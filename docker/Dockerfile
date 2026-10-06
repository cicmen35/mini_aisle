# syntax=docker/dockerfile:1.7
# One multi-stage Dockerfile for every service. Build a service with:
#   docker build -f docker/Dockerfile --target api --build-arg SERVICE=api -t patchloop-api .
# Targets: api | fixer | scanner | verifier. All run as uid 10001 with no build tooling.

ARG PYTHON_IMAGE=python:3.12-slim
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.12.23

FROM ${UV_IMAGE} AS uv

# ---------------------------------------------------------------- builder: service venv
FROM ${PYTHON_IMAGE} AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /src
ARG SERVICE
RUN test -n "${SERVICE}" || (echo "--build-arg SERVICE is required" && false)
COPY pyproject.toml uv.lock ./
COPY packages packages
COPY services services
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable --package "patchloop-${SERVICE}"

# ---------------------------------------------------------------- tools: scanners in their own venvs
FROM ${PYTHON_IMAGE} AS tools
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_TOOL_DIR=/opt/tools/venvs UV_TOOL_BIN_DIR=/opt/tools/bin UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
RUN --mount=type=cache,target=/root/.cache/uv \
    uv tool install semgrep==1.157.0 \
 && uv tool install "bandit[toml]==1.9.2" \
 && uv tool install pip-audit==2.9.0

# ---------------------------------------------------------------- runtime base
FROM ${PYTHON_IMAGE} AS runtime
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /tmp --shell /usr/sbin/nologin app
ENV PATH=/opt/venv/bin:$PATH PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app

# Scanner/verifier base: git + scanner tools + offline Semgrep rules.
FROM runtime AS sandbox
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*
COPY --from=tools /opt/tools /opt/tools
COPY services/scanner/rules /opt/patchloop/rules
ENV PATH=/opt/venv/bin:/opt/tools/bin:$PATH \
    PATCHLOOP_SCANNER_SEMGREP_CONFIG=/opt/patchloop/rules/semgrep

# ---------------------------------------------------------------- service targets
FROM runtime AS api
COPY --from=builder /opt/venv /opt/venv
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"]
CMD ["patchloop-api"]

FROM runtime AS fixer
COPY --from=builder /opt/venv /opt/venv
USER 10001:10001
CMD ["patchloop-fixer"]

FROM sandbox AS scanner
COPY --from=builder /opt/venv /opt/venv
USER 10001:10001
CMD ["patchloop-scanner"]

FROM sandbox AS verifier
COPY --from=builder /opt/venv /opt/venv
USER 10001:10001
CMD ["patchloop-verifier"]
