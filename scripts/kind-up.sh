#!/usr/bin/env bash
# Local Kubernetes: kind cluster + metrics-server (+ KEDA) + patchloop.
#   make kind-up                 # with KEDA scale-to-zero for workers
#   KEDA=0 make kind-up          # plain HPA/fixed replicas
#   make kind-down
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CLUSTER="${CLUSTER:-patchloop}"
KEDA="${KEDA:-1}"
KEDA_VERSION="${KEDA_VERSION:-2.16.1}"
METRICS_SERVER_VERSION="${METRICS_SERVER_VERSION:-v0.7.2}"

for bin in kind kubectl docker; do
  command -v "$bin" >/dev/null || { echo "error: $bin is required" >&2; exit 1; }
done

if ! kind get clusters | grep -qx "$CLUSTER"; then
  echo "==> Creating kind cluster '$CLUSTER'"
  kind create cluster --name "$CLUSTER" --wait 120s --config - <<'EOF'
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
EOF
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

echo "==> Building images"
make -C "$ROOT" images TAG=local
echo "==> Loading images into kind"
for img in api scanner fixer verifier infra; do
  kind load docker-image --name "$CLUSTER" "patchloop-$img:local"
done
docker pull -q localstack/localstack:4.14 >/dev/null && kind load docker-image --name "$CLUSTER" localstack/localstack:4.14
docker pull -q postgres:16-alpine >/dev/null && kind load docker-image --name "$CLUSTER" postgres:16-alpine

echo "==> metrics-server (for the API HPA)"
kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/${METRICS_SERVER_VERSION}/components.yaml" >/dev/null
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' >/dev/null 2>&1 || true

overlay="$ROOT/deploy/k8s/overlays/kind"
if [[ "$KEDA" == "1" ]]; then
  echo "==> KEDA $KEDA_VERSION"
  kubectl apply --server-side -f "https://github.com/kedacore/keda/releases/download/v${KEDA_VERSION}/keda-${KEDA_VERSION}.yaml" >/dev/null
  kubectl -n keda rollout status deploy/keda-operator --timeout=180s
  kubectl -n keda rollout status deploy/keda-operator-metrics-apiserver --timeout=180s
  overlay="$ROOT/deploy/k8s/overlays/kind-keda"
fi

echo "==> Deploying $(basename "$overlay")"
kubectl apply -k "$overlay"

echo "==> Waiting for backing services, terraform and migrations"
kubectl -n patchloop-deps rollout status statefulset/postgres --timeout=180s
kubectl -n patchloop-deps rollout status deploy/localstack --timeout=180s
kubectl -n patchloop-deps wait --for=condition=complete job/infra --timeout=300s
kubectl -n patchloop wait --for=condition=complete job/migrate --timeout=300s

# Workers may have crash-looped while queues didn't exist yet; restart them now that they do.
kubectl -n patchloop rollout restart deploy >/dev/null
kubectl -n patchloop rollout status deploy/api --timeout=180s
kubectl -n patchloop get deploy,pods,hpa
[[ "$KEDA" == "1" ]] && kubectl -n patchloop get scaledobjects

cat <<EOF

patchloop is running in kind.
  kubectl -n patchloop port-forward svc/api 8421:80   ->  http://localhost:8421/docs
  kubectl -n patchloop get deploy -w                   (watch workers scale with KEDA)
  make kind-down
EOF
