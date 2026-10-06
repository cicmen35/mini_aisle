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
networking:
  # nftables, not iptables: kube-proxy's iptables mode needs the xt_statistic module,
  # which some kernels (this one included) don't ship. nftables is in Kubernetes 1.31.
  kubeProxyMode: nftables
nodes:
  - role: control-plane
EOF
fi
kubectl config use-context "kind-$CLUSTER" >/dev/null

echo "==> Building images"
make -C "$ROOT" images TAG=local
echo "==> Loading images into kind"
# `kind load` imports with --all-platforms, which fails on images whose index references
# blobs that aren't in the saved archive (LocalStack 4.14). Fall back to a plain ctr import.
load_image() {
  local image="$1"
  if kind load docker-image --name "$CLUSTER" "$image"; then
    return 0
  fi
  echo "kind load failed for $image; importing the archive directly"
  if docker save "$image" | docker exec -i "${CLUSTER}-control-plane" \
    ctr --namespace=k8s.io images import --snapshotter=overlayfs -; then
    return 0
  fi
  # Public images only: pull inside the node (kind's ctr import chokes on some indexes).
  echo "archive import failed for $image; pulling it inside the node"
  docker exec "${CLUSTER}-control-plane" crictl pull "$image"
}
for img in api scanner fixer verifier infra; do
  load_image "patchloop-$img:local"
done
docker pull -q localstack/localstack:4.14 >/dev/null && load_image localstack/localstack:4.14
docker pull -q postgres:16-alpine >/dev/null && load_image postgres:16-alpine

echo "==> metrics-server (for the API HPA)"
kubectl apply -f "https://github.com/kubernetes-sigs/metrics-server/releases/download/${METRICS_SERVER_VERSION}/components.yaml" >/dev/null
kubectl -n kube-system patch deployment metrics-server --type=json \
  -p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]' >/dev/null 2>&1 || true

overlay="$ROOT/deploy/k8s/overlays/kind"
if [[ "$KEDA" == "1" ]]; then
  echo "==> KEDA $KEDA_VERSION"
  kubectl apply --server-side -f "https://github.com/kedacore/keda/releases/download/v${KEDA_VERSION}/keda-${KEDA_VERSION}.yaml" >/dev/null
  kubectl -n keda rollout status deploy/keda-operator --timeout=180s
  kubectl -n keda rollout status deploy/keda-metrics-apiserver --timeout=180s
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
