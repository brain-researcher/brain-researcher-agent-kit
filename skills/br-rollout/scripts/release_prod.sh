#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <service>"
  echo "Services: web-ui | agent | neurokg | mcp | orchestrator | marimo-runtime"
  exit 2
fi

SERVICE="$1"
DOCKERHUB_NAMESPACE="${DOCKERHUB_NAMESPACE:-zjc062}"
K8S_NAMESPACE="${K8S_NAMESPACE:-brain-researcher-core}"
RELEASE_PREFIX="${RELEASE_PREFIX:-brain-researcher}"
IMAGE_TAG="${IMAGE_TAG:-$(date -u +%Y%m%d%H%M%S)}"
ROLLOUT="${ROLLOUT:-true}"
VERIFY_HTTP_URL="${VERIFY_HTTP_URL:-}"
KUBE_CONTEXT="${KUBE_CONTEXT:-}"

DOMAIN="${DOMAIN:-brain-researcher.com}"
ORCHESTRATOR_HOST="${ORCHESTRATOR_HOST:-${RELEASE_PREFIX}-orchestrator}"
ORCHESTRATOR_PORT="${ORCHESTRATOR_PORT:-3001}"
AGENT_HOST="${AGENT_HOST:-${RELEASE_PREFIX}-agent}"
AGENT_PORT="${AGENT_PORT:-8000}"
NEUROKG_HOST="${NEUROKG_HOST:-${RELEASE_PREFIX}-neurokg}"
NEUROKG_PORT="${NEUROKG_PORT:-5000}"
WEB_UI_DOCKERFILE="${WEB_UI_DOCKERFILE:-}"
WEB_UI_BUILD_CONTEXT="${WEB_UI_BUILD_CONTEXT:-}"
ORCHESTRATOR_DOCKERFILE="${ORCHESTRATOR_DOCKERFILE:-}"
MARIMO_RUNTIME_DOCKERFILE="${MARIMO_RUNTIME_DOCKERFILE:-}"
MARIMO_RUNTIME_BUILD_CONTEXT="${MARIMO_RUNTIME_BUILD_CONTEXT:-}"
MARIMO_RUNTIME_IMAGE_REPO="${MARIMO_RUNTIME_IMAGE_REPO:-marimo-singleuser}"
GCP_PROJECT="${GCP_PROJECT:-}"
GCP_ZONE="${GCP_ZONE:-us-west1-b}"
PROD_VM="${PROD_VM:-brain-researcher-vm}"
GCLOUD_BIN="${GCLOUD_BIN:-gcloud}"
ORCHESTRATOR_DEPLOYMENT="${ORCHESTRATOR_DEPLOYMENT:-${RELEASE_PREFIX}-orchestrator}"

DOCKER_BUILD_CMD=()
IMAGE_REPO=""
DEPLOYMENT_NAME=""
CONTAINER_NAME=""
ROLLOUT_MODE="local_kubectl_image"

resolve_first_existing_path() {
  for candidate in "$@"; do
    if [[ -n "${candidate}" && -f "${candidate}" ]]; then
      echo "${candidate}"
      return 0
    fi
  done
  return 1
}

resolve_web_ui_build() {
  local dockerfile=""
  dockerfile="$(
    resolve_first_existing_path \
      "${WEB_UI_DOCKERFILE}" \
      "apps/web-ui/Dockerfile" \
      "brain_researcher/services/web_ui/Dockerfile" \
      "src/brain_researcher/services/web_ui/Dockerfile"
  )" || true

  if [[ -z "${dockerfile}" ]]; then
    echo "ERROR: Could not find web-ui Dockerfile." >&2
    echo "Checked: apps/web-ui/Dockerfile, brain_researcher/services/web_ui/Dockerfile, src/brain_researcher/services/web_ui/Dockerfile" >&2
    echo "Set WEB_UI_DOCKERFILE to override." >&2
    exit 1
  fi

  local context="${WEB_UI_BUILD_CONTEXT}"
  if [[ -z "${context}" ]]; then
    case "${dockerfile}" in
      apps/web-ui/Dockerfile)
        context="."
        ;;
      *)
        context="$(dirname "${dockerfile}")"
        ;;
    esac
  fi

  echo "${dockerfile}|${context}"
}

resolve_orchestrator_dockerfile() {
  local dockerfile=""
  dockerfile="$(
    resolve_first_existing_path \
      "${ORCHESTRATOR_DOCKERFILE}" \
      "infrastructure/docker/Dockerfile.orchestrator" \
      "src/brain_researcher/services/orchestrator/Dockerfile" \
      "brain_researcher/services/orchestrator/Dockerfile"
  )" || true

  if [[ -z "${dockerfile}" ]]; then
    echo "ERROR: Could not find orchestrator Dockerfile." >&2
    echo "Checked: src/brain_researcher/services/orchestrator/Dockerfile, brain_researcher/services/orchestrator/Dockerfile" >&2
    echo "Set ORCHESTRATOR_DOCKERFILE to override." >&2
    exit 1
  fi

  echo "${dockerfile}"
}

resolve_marimo_runtime_build() {
  local dockerfile=""
  dockerfile="$(
    resolve_first_existing_path \
      "${MARIMO_RUNTIME_DOCKERFILE}" \
      "infrastructure/docker/Dockerfile.marimo-singleuser" \
      "apps/web-ui/infrastructure/docker/Dockerfile.marimo-singleuser" \
      "src/brain_researcher/services/orchestrator/Dockerfile.marimo-singleuser"
  )" || true

  if [[ -z "${dockerfile}" ]]; then
    echo "ERROR: Could not find marimo runtime Dockerfile." >&2
    echo "Checked: infrastructure/docker/Dockerfile.marimo-singleuser, apps/web-ui/infrastructure/docker/Dockerfile.marimo-singleuser, src/brain_researcher/services/orchestrator/Dockerfile.marimo-singleuser" >&2
    echo "Set MARIMO_RUNTIME_DOCKERFILE and MARIMO_RUNTIME_BUILD_CONTEXT when building from a sibling web-ui worktree." >&2
    exit 1
  fi

  local context="${MARIMO_RUNTIME_BUILD_CONTEXT}"
  if [[ -z "${context}" ]]; then
    context="$(dirname "$(dirname "${dockerfile}")")"
  fi

  echo "${dockerfile}|${context}"
}

case "$SERVICE" in
  web-ui)
    IMAGE_REPO="web-ui"
    DEPLOYMENT_NAME="${RELEASE_PREFIX}-web-ui"
    CONTAINER_NAME="web-ui"
    IFS='|' read -r RESOLVED_WEB_UI_DOCKERFILE RESOLVED_WEB_UI_CONTEXT <<< "$(resolve_web_ui_build)"
    echo "Resolved web-ui Dockerfile: ${RESOLVED_WEB_UI_DOCKERFILE} (context: ${RESOLVED_WEB_UI_CONTEXT})"
    DOCKER_BUILD_CMD=(
      docker build
      -t "docker.io/${DOCKERHUB_NAMESPACE}/${IMAGE_REPO}:${IMAGE_TAG}"
      -f "${RESOLVED_WEB_UI_DOCKERFILE}"
      --build-arg "NEXT_PUBLIC_API_URL=https://${DOMAIN}"
      --build-arg "NEXT_PUBLIC_ORCHESTRATOR_URL=https://${DOMAIN}"
      --build-arg "NEXT_PUBLIC_AGENT_URL=https://${DOMAIN}"
      --build-arg "NEXT_PUBLIC_NEUROKG_URL=https://${DOMAIN}/kg"
      --build-arg "NEXT_PUBLIC_NEUROKG_API=https://${DOMAIN}/kg"
      --build-arg "NEXT_PUBLIC_WS_URL=wss://${DOMAIN}/ws"
      --build-arg "NEXT_PUBLIC_USE_API_PROXY=true"
      --build-arg "NEXT_PUBLIC_AUTH_MODE=both"
      --build-arg "ORCHESTRATOR_HOST=${ORCHESTRATOR_HOST}"
      --build-arg "ORCHESTRATOR_PORT=${ORCHESTRATOR_PORT}"
      --build-arg "AGENT_HOST=${AGENT_HOST}"
      --build-arg "AGENT_PORT=${AGENT_PORT}"
      --build-arg "NEUROKG_HOST=${NEUROKG_HOST}"
      --build-arg "NEUROKG_PORT=${NEUROKG_PORT}"
      "${RESOLVED_WEB_UI_CONTEXT}"
    )
    ;;
  agent|neurokg|mcp)
    IMAGE_REPO="${SERVICE}"
    DEPLOYMENT_NAME="${RELEASE_PREFIX}-${SERVICE}"
    CONTAINER_NAME="${SERVICE}"
    DOCKER_BUILD_CMD=(
      docker build
      --target "${SERVICE}"
      -t "docker.io/${DOCKERHUB_NAMESPACE}/${IMAGE_REPO}:${IMAGE_TAG}"
      .
    )
    ;;
  orchestrator)
    IMAGE_REPO="orchestrator"
    DEPLOYMENT_NAME="${RELEASE_PREFIX}-orchestrator"
    CONTAINER_NAME="orchestrator"
    RESOLVED_ORCHESTRATOR_DOCKERFILE="$(resolve_orchestrator_dockerfile)"
    echo "Resolved orchestrator Dockerfile: ${RESOLVED_ORCHESTRATOR_DOCKERFILE}"
    DOCKER_BUILD_CMD=(
      docker build
      -t "docker.io/${DOCKERHUB_NAMESPACE}/${IMAGE_REPO}:${IMAGE_TAG}"
      -f "${RESOLVED_ORCHESTRATOR_DOCKERFILE}"
      .
    )
    ;;
  marimo-runtime)
    IMAGE_REPO="${MARIMO_RUNTIME_IMAGE_REPO}"
    DEPLOYMENT_NAME="${ORCHESTRATOR_DEPLOYMENT}"
    CONTAINER_NAME="orchestrator"
    ROLLOUT_MODE="remote_orchestrator_env"
    IFS='|' read -r RESOLVED_MARIMO_RUNTIME_DOCKERFILE RESOLVED_MARIMO_RUNTIME_CONTEXT <<< "$(resolve_marimo_runtime_build)"
    echo "Resolved marimo runtime Dockerfile: ${RESOLVED_MARIMO_RUNTIME_DOCKERFILE} (context: ${RESOLVED_MARIMO_RUNTIME_CONTEXT})"
    DOCKER_BUILD_CMD=(
      docker build
      -t "docker.io/${DOCKERHUB_NAMESPACE}/${IMAGE_REPO}:${IMAGE_TAG}"
      -f "${RESOLVED_MARIMO_RUNTIME_DOCKERFILE}"
      "${RESOLVED_MARIMO_RUNTIME_CONTEXT}"
    )
    ;;
  *)
    echo "Unsupported service: ${SERVICE}"
    exit 2
    ;;
esac

IMAGE_URI="docker.io/${DOCKERHUB_NAMESPACE}/${IMAGE_REPO}:${IMAGE_TAG}"

echo "[1/4] Building image: ${IMAGE_URI}"
"${DOCKER_BUILD_CMD[@]}"

echo "[2/4] Pushing image: ${IMAGE_URI}"
PUSH_OUTPUT="$(docker push "${IMAGE_URI}" 2>&1 | tee /dev/stderr)"
DIGEST="$(printf '%s' "${PUSH_OUTPUT}" | rg -o 'digest: sha256:[0-9a-f]+' | tail -n1 | awk '{print $2}')"

if [[ -z "${DIGEST}" ]]; then
  DIGEST="unknown"
fi

if [[ "${ROLLOUT}" == "true" ]]; then
  if [[ "${ROLLOUT_MODE}" == "remote_orchestrator_env" ]]; then
    if [[ -z "${GCP_PROJECT}" ]]; then
      echo "ERROR: Set GCP_PROJECT before remote production rollout."
      exit 1
    fi

    echo "[3/4] Rolling out marimo runtime via orchestrator env on ${PROD_VM}"
    "${GCLOUD_BIN}" compute ssh "${PROD_VM}" \
      --zone "${GCP_ZONE}" \
      --project "${GCP_PROJECT}" \
      --command "sudo k3s kubectl -n ${K8S_NAMESPACE} set env deployment/${DEPLOYMENT_NAME} BR_MARIMO_RUNTIME_IMAGE=${IMAGE_URI} && sudo k3s kubectl -n ${K8S_NAMESPACE} rollout status deployment/${DEPLOYMENT_NAME} --timeout=300s"

    echo "[4/4] Verifying deployed marimo runtime image env"
    RUNNING_IMAGE="$(
      "${GCLOUD_BIN}" compute ssh "${PROD_VM}" \
        --zone "${GCP_ZONE}" \
        --project "${GCP_PROJECT}" \
        --command "sudo k3s kubectl -n ${K8S_NAMESPACE} get deployment ${DEPLOYMENT_NAME} -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{\"\\n\"}{end}' | grep '^BR_MARIMO_RUNTIME_IMAGE='"
    )"
  else
    if [[ -n "${KUBE_CONTEXT}" ]]; then
      KCTX_ARGS=(--context "${KUBE_CONTEXT}")
    else
      KCTX_ARGS=()
    fi

    CURRENT_CONTEXT="$(kubectl "${KCTX_ARGS[@]}" config current-context 2>/dev/null || true)"
    if [[ -z "${CURRENT_CONTEXT}" ]]; then
      echo "ERROR: kubectl context is not available. Set KUBE_CONTEXT or configure kubeconfig."
      exit 1
    fi

    if [[ -z "${KUBE_CONTEXT}" && "${CURRENT_CONTEXT}" == k3d-* ]]; then
      echo "ERROR: current context is ${CURRENT_CONTEXT} (likely local test cluster)."
      echo "Set KUBE_CONTEXT to your production context before rollout."
      exit 1
    fi

    if ! kubectl "${KCTX_ARGS[@]}" -n "${K8S_NAMESPACE}" get deployment "${DEPLOYMENT_NAME}" >/dev/null 2>&1; then
      echo "ERROR: deployment ${K8S_NAMESPACE}/${DEPLOYMENT_NAME} not found in context ${CURRENT_CONTEXT}."
      exit 1
    fi

    echo "[3/4] Rolling out deployment ${K8S_NAMESPACE}/${DEPLOYMENT_NAME}"
    kubectl "${KCTX_ARGS[@]}" -n "${K8S_NAMESPACE}" set image "deployment/${DEPLOYMENT_NAME}" "${CONTAINER_NAME}=${IMAGE_URI}"
    kubectl "${KCTX_ARGS[@]}" -n "${K8S_NAMESPACE}" rollout status "deployment/${DEPLOYMENT_NAME}" --timeout=300s

    echo "[4/4] Verifying deployed image"
    RUNNING_IMAGE="$(
      kubectl "${KCTX_ARGS[@]}" -n "${K8S_NAMESPACE}" get deployment "${DEPLOYMENT_NAME}" \
        -o "jsonpath={.spec.template.spec.containers[?(@.name=='${CONTAINER_NAME}')].image}"
    )"
  fi
else
  RUNNING_IMAGE="(rollout skipped)"
fi

if [[ -n "${VERIFY_HTTP_URL}" ]]; then
  echo "HTTP check: ${VERIFY_HTTP_URL}"
  curl -sS -I --max-time 10 "${VERIFY_HTTP_URL}" | head -n 5
fi

echo
echo "Release summary:"
echo "  - service: ${SERVICE}"
echo "  - image: ${IMAGE_URI}"
echo "  - push digest: ${DIGEST}"
if [[ "${ROLLOUT}" == "true" ]]; then
  echo "  - rollout target: ${K8S_NAMESPACE}/${DEPLOYMENT_NAME} succeeded"
fi
echo "  - deployed image: ${RUNNING_IMAGE}"
