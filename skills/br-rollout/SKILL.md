---
name: br-rollout
description: BR Rollout — build, push, and roll out Brain Researcher container images to production k3s (web-ui, agent, neurokg, mcp, orchestrator, marimo-runtime) with verification and rollback. Use when a code change is ready for release and you need the repeatable prod deployment flow for brain-researcher.com.
---

# BR Rollout

Release Brain Researcher services safely to production.

Primary prod target is **k3s on the GCE VM `brain-researcher-vm`**, NOT GKE and NOT
the local `k3d-*` cluster. Operate the prod control plane only via
`gcloud compute ssh ... "sudo k3s kubectl ..."`. Do not trust the local `kubectl`
context for prod decisions (it usually points at a k3d test cluster).

## When to use
- A code change is merged and you need to ship one or more services to prod k3s.
- You need the exact build→push→roll-out→verify→pin→rollback flow for `brain-researcher.com`.
- NOT for: local/k3d testing; GKE; editing Helm values without a release (edit `values.prod.yaml` directly).

## Defaults

| Setting | Value |
|---|---|
| Docker Hub namespace | `zjc062` |
| Kubernetes namespace | `brain-researcher-core` |
| Helm release | `brain-researcher` |
| GCP project | set via `GCP_PROJECT` |
| Prod VM | `brain-researcher-vm` |
| Zone | `us-west1-b` |
| Prod domain | `brain-researcher.com` |
| Prod values file | `infrastructure/deployment/gce_k3s/values.prod.yaml` |

Never hardcode secrets in files. Runtime secrets come from Kubernetes secrets
(`brain-researcher-external-services`, `-llm-api-keys`, `-database-credentials`,
`-mcp-auth`), not from this skill.

## Preflight

Confirm before building:

```bash
gcloud auth list --filter=status:ACTIVE --format='value(account)'   # active GCP account
gcloud config get-value project                                     # matches GCP_PROJECT
docker login                                                        # namespace zjc062 reachable
git -C <brain_researcher_checkout> status -sb                       # intended change committed
```

## Workflow

Run from the Brain Researcher repo root: `cd <brain_researcher_checkout>`

### 1. Build + push (rollout skipped)

Always build+push first, then roll out explicitly. Use a descriptive tag tied to
the commit so the running image is traceable.

```bash
export IMAGE_TAG="$(date -u +%Y%m%d%H%M%S)-<short-purpose>-<git-short-sha>"
ROLLOUT=false IMAGE_TAG="$IMAGE_TAG" \
  ./skills/br-rollout/scripts/release_prod.sh web-ui
```

The script sets the correct Next.js build args for `web-ui` (internal
`ORCHESTRATOR_HOST/PORT`, `AGENT_HOST/PORT`, `NEUROKG_HOST/PORT` so rewrites do
not fall back to `localhost`) and prints the pushed image + digest.

Services: `web-ui | agent | neurokg | mcp | orchestrator | marimo-runtime`.

### 2. Roll out on the prod VM

Use the SAME `<TAG>` that was pushed. (RollingUpdate `maxUnavailable:0` → zero downtime for web-ui.)

```bash
TAG="<the pushed tag>"
gcloud compute ssh brain-researcher-vm --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core set image deployment/brain-researcher-web-ui web-ui=docker.io/zjc062/web-ui:${TAG} && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-web-ui --timeout=300s"
```

Deployment vs statefulset and the container/image name per service are in the
**Service Mapping** table below. For `marimo-runtime` the rollout is an env update
on `deployment/brain-researcher-orchestrator` (`BR_MARIMO_RUNTIME_IMAGE`), not a
`set image` — `ROLLOUT=true` on the script handles this automatically.

### 3. Verify

```bash
# running image matches the pushed tag
gcloud compute ssh brain-researcher-vm --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core get deploy brain-researcher-web-ui -o jsonpath='{.spec.template.spec.containers[0].image}' && echo"

# public health (expect HTTP 200)
curl -sS -o /dev/null -w 'health %{http_code}\n' https://brain-researcher.com/api/health
curl -sS -o /dev/null -w 'agent  %{http_code}\n' https://brain-researcher.com/api/agent/health
curl -sS -o /dev/null -w 'kg     %{http_code}\n' https://brain-researcher.com/api/kg/health
```

If `/api/agent/health` returns 500 with `Failed to proxy http://localhost:8000/health`
in web-ui logs, the image was built without the internal host build args — rebuild
via the script (which sets them) and roll out again.

### 4. Pin the tag in `values.prod.yaml`

So a later `helm upgrade` does not revert to the old image, update the per-service
tag (e.g. `webUi.imageTag`) and commit it.

```yaml
webUi:
  imageTag: "<the pushed tag>"
```

### 5. Rollback (if unhealthy)

```bash
gcloud compute ssh brain-researcher-vm --zone us-west1-b --project "$GCP_PROJECT" \
  --command "sudo k3s kubectl -n brain-researcher-core rollout undo deployment/brain-researcher-web-ui && \
             sudo k3s kubectl -n brain-researcher-core rollout status deployment/brain-researcher-web-ui --timeout=300s"
```

For statefulsets, roll back by `set image` to the previous known-good tag. Keep
1–2 prior tags per service for this reason; don't delete images right after rollout.

## Service Mapping

| Service | Workload | Container | Image |
|---|---|---|---|
| `web-ui` | deployment `brain-researcher-web-ui` | `web-ui` | `docker.io/zjc062/web-ui:<TAG>` |
| `agent` | statefulset `brain-researcher-agent` | `agent` | `docker.io/zjc062/agent:<TAG>` |
| `neurokg` | statefulset `brain-researcher-neurokg` | `neurokg` | `docker.io/zjc062/neurokg:<TAG>` |
| `mcp` | deployment `brain-researcher-mcp` | `mcp` | `docker.io/zjc062/mcp:<TAG>` |
| `orchestrator` | deployment `brain-researcher-orchestrator` | `orchestrator` | `docker.io/zjc062/orchestrator:<TAG>` |
| `marimo-runtime` | env on `deployment/brain-researcher-orchestrator` | — | `BR_MARIMO_RUNTIME_IMAGE=docker.io/zjc062/marimo-singleuser:<TAG>` |

## Helm guardrails

- Always pass `-f infrastructure/deployment/gce_k3s/values.prod.yaml`.
- Never revert pinned values to `global.imageTag: latest` or
  `global.domain: brain-researcher.local`. `global.domain` must stay `brain-researcher.com`.
- Prefer per-service `imageTag` updates over only changing `global.imageTag`.
- After `helm upgrade`, re-check live images with `get deploy/sts ... -o jsonpath=...`.

## Worked example — homepage revert (2026-05-28)

Reverted `landing-page-static.tsx` to the "Take any neuroimaging workflow with you" version:

1. Commit on master: `a6ee48274`.
2. `ROLLOUT=false IMAGE_TAG=20260529044256-homepage-revert-a6ee48274 ./skills/br-rollout/scripts/release_prod.sh web-ui`
   → pushed `docker.io/zjc062/web-ui:20260529044256-homepage-revert-a6ee48274` (digest `sha256:f5f5129a…`).
3. `gcloud compute ssh brain-researcher-vm ... set image deployment/brain-researcher-web-ui web-ui=...:<tag> && rollout status` → succeeded, zero downtime.
4. Verified: running image = new tag, `https://brain-researcher.com/api/health` = 200, live headline = "Take any neuroimaging workflow".
5. Pinned `webUi.imageTag` in `values.prod.yaml` (commit `0af37f1f3`).

## References

- `references/prod-rollout-playbook.md` — per-service rollout/rollback commands,
  marimo-runtime flow, CVMFS/Neurodesk and OpenNeuro S3 prerequisites.
- `scripts/release_prod.sh` — build/push (+optional rollout) helper. Mirrors the
  canonical Codex `brain-researcher-prod-rollout` script; keep them in sync.

## Related memory
`reference_prod_rollout.md` (prod = k3s on GCE VM, operate via `gcloud compute ssh … sudo k3s kubectl`).
