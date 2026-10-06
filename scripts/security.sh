#!/usr/bin/env bash
# Security scans of THIS repo (not of scan targets). demo-targets/ is deliberately vulnerable and
# excluded everywhere. Set SKIP_IMAGES=1 to skip image scans (e.g. when images aren't built).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
UV="${UV:-uv}"
TAG="${TAG:-local}"
SEMGREP_VERSION="${SEMGREP_VERSION:-1.157.0}"
TRIVY_IMAGE="${TRIVY_IMAGE:-aquasec/trivy:0.75.0}"

trivy() {
  if command -v trivy >/dev/null 2>&1; then
    command trivy "$@"
  else
    docker run --rm -v "$ROOT:/repo" -w /repo -v /var/run/docker.sock:/var/run/docker.sock \
      -v "${HOME}/.cache/trivy:/root/.cache/trivy" "$TRIVY_IMAGE" "$@"
  fi
}

echo "==> bandit (medium+)"
"$UV" run bandit -q -r packages services -c pyproject.toml -ll

echo "==> semgrep (registry rules: python, dockerfile, secrets)"
"$UV" tool run --from "semgrep==${SEMGREP_VERSION}" semgrep scan --error --quiet --metrics=off \
  --disable-version-check --config p/python --config p/dockerfile --config p/secrets \
  --exclude demo-targets --exclude tests --exclude .venv .

echo "==> pip-audit (locked runtime dependencies)"
"$UV" export --frozen --no-dev --no-hashes --no-emit-workspace --no-header -o build/requirements.lock.txt -q 2>/dev/null \
  || { mkdir -p build && "$UV" export --frozen --no-dev --no-hashes --no-emit-workspace --no-header -o build/requirements.lock.txt -q; }
"$UV" tool run pip-audit==2.9.0 -r build/requirements.lock.txt --no-deps --disable-pip --progress-spinner off

echo "==> trivy fs (vulns, secrets, misconfig: Dockerfiles, compose, k8s, terraform)"
trivy fs --quiet --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
  --scanners vuln,secret,misconfig --skip-dirs demo-targets --skip-dirs .venv \
  --skip-dirs build --ignorefile .trivyignore .

if [[ "${SKIP_IMAGES:-}" != "1" ]]; then
  for svc in api scanner fixer verifier; do
    echo "==> trivy image patchloop-$svc:$TAG"
    trivy image --quiet --exit-code 1 --severity HIGH,CRITICAL --ignore-unfixed \
      --scanners vuln,secret --ignorefile .trivyignore "patchloop-$svc:$TAG"
  done
fi
echo "security: OK"
