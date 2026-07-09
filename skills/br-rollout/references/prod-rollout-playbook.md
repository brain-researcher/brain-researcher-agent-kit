# Brain Researcher Prod Rollout Playbook

## Purpose

Use this playbook to release one service safely to production k3s after code changes.

## Preconditions

- Repo is up to date and local tests are green.
- `docker login` has access to `docker.io/zjc062`.
- `gcloud` auth can access the project named by `GCP_PROJECT`.
- Production VM `${PROD_VM}` is reachable.
- Target workload exists in namespace `brain-researcher-core`.

## Critical Path

- Production control-plane path is VM-local k3s:
  - `gcloud compute ssh ... "sudo k3s kubectl ..."`
- Do not use local `kubectl` context as the source of truth for production rollout.
- Hosted marimo runtime is orchestrator-managed. Updating it means changing `BR_MARIMO_RUNTIME_IMAGE` on `deployment/brain-researcher-orchestrator`.

## VM Access Check

```bash
gcloud compute ssh ${PROD_VM} \
  --zone us-west1-b \
  --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core get deploy,sts -o wide"
```

## Build + Push (Recommended)

From repo root:

```bash
IMAGE_TAG=$(date -u +%Y%m%d%H%M%S) \
ROLLOUT=false \
./skills/br-rollout/scripts/release_prod.sh web-ui
```

The current script is authoritative for build/push. For `marimo-runtime`, it also knows how to update orchestrator via the prod VM when `ROLLOUT=true`.

## Rollout Commands (VM k3s)

Use the same `<TAG>` that was pushed.

### `web-ui` (deployment)

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image deployment/brain-researcher-web-ui web-ui=docker.io/zjc062/web-ui:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-web-ui --timeout=300s"
```

### `mcp` (deployment)

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image deployment/brain-researcher-mcp mcp=docker.io/zjc062/mcp:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-mcp --timeout=300s"
```

### `orchestrator` (deployment)

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image deployment/brain-researcher-orchestrator orchestrator=docker.io/zjc062/orchestrator:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-orchestrator --timeout=300s"
```

### `agent` (statefulset)

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image statefulset/brain-researcher-agent agent=docker.io/zjc062/agent:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status statefulset/brain-researcher-agent --timeout=600s"
```

### `neurokg` (statefulset)

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image statefulset/brain-researcher-neurokg neurokg=docker.io/zjc062/neurokg:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status statefulset/brain-researcher-neurokg --timeout=600s"
```

### `marimo-runtime` (orchestrator env)

Build/push from a sibling UI worktree when needed:

```bash
IMAGE_TAG=$(date -u +%Y%m%d%H%M%S)-marimo-hotfix \
MARIMO_RUNTIME_DOCKERFILE=/path/to/brain_researcher-ui/infrastructure/docker/Dockerfile.marimo-singleuser \
MARIMO_RUNTIME_BUILD_CONTEXT=/path/to/brain_researcher-ui \
ROLLOUT=false \
./skills/br-rollout/scripts/release_prod.sh marimo-runtime
```

Manual VM rollout with an already-pushed tag:

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set env deployment/brain-researcher-orchestrator BR_MARIMO_RUNTIME_IMAGE=docker.io/zjc062/marimo-singleuser:<TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-orchestrator --timeout=300s"
```

Verification:

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core get deploy brain-researcher-orchestrator -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{\"\\n\"}{end}' | grep '^BR_MARIMO_RUNTIME_IMAGE='"
```

## Build/Push Overrides

- Custom tag:
  - `IMAGE_TAG=hotfix-20260211 .../release_prod.sh web-ui`
- Build and push only:
  - `ROLLOUT=false .../release_prod.sh web-ui`
- Marimo runtime from sibling clone/worktree:
  - `MARIMO_RUNTIME_DOCKERFILE=/path/to/Dockerfile.marimo-singleuser`
  - `MARIMO_RUNTIME_BUILD_CONTEXT=/path/to/ui-worktree`

## Verification checklist

- Runtime image matches pushed tag (from VM):
  - `gcloud compute ssh ... --command "sudo k3s kubectl -n brain-researcher-core get deploy brain-researcher-web-ui -o jsonpath='{.spec.template.spec.containers[0].image}' && echo"`
  - `gcloud compute ssh ... --command "sudo k3s kubectl -n brain-researcher-core get sts brain-researcher-neurokg -o jsonpath='{.spec.template.spec.containers[0].image}' && echo"`
  - `gcloud compute ssh ... --command "sudo k3s kubectl -n brain-researcher-core get deploy brain-researcher-orchestrator -o jsonpath='{range .spec.template.spec.containers[0].env[*]}{.name}={.value}{\"\\n\"}{end}' | grep '^BR_MARIMO_RUNTIME_IMAGE='"`
- Health checks:
  - `curl -sS -i https://brain-researcher.com/api/health`
  - `curl -sS -i https://brain-researcher.com/api/agent/health`
  - `curl -sS -i https://brain-researcher.com/api/kg/health`
- Runtime-sensitive smoke:
  - fresh `/hub` session if the rollout changes hosted marimo runtime behavior

## Rollback

If any issue is observed:

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core rollout undo deployment/brain-researcher-web-ui && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-web-ui --timeout=300s"
```

For statefulsets, rollback by setting the previous known-good image tag:

```bash
gcloud compute ssh ${PROD_VM} --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image statefulset/brain-researcher-neurokg neurokg=docker.io/zjc062/neurokg:<PREV_TAG> && \
             sudo k3s kubectl -n brain-researcher-core rollout status statefulset/brain-researcher-neurokg --timeout=600s"
```

For `marimo-runtime`, rollback by restoring the previous `BR_MARIMO_RUNTIME_IMAGE` value on orchestrator and rolling out orchestrator again.
