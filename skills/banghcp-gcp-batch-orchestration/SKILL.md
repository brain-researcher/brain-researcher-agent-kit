---
name: banghcp-gcp-batch-orchestration
description: Constrained GCP experiment scheduling for BangHCP / FC benchmarking in the brain_researcher repository. Use when Codex needs to choose CPU vs GPU batches, check budget and worker status, launch approved workers, sync results, stop workers, or apply the BangHCP compute envelopes without using raw gcloud instance commands. This skill is specific to the BangHCP project document and project-local GCP wrappers. Do not use it for production service deployment; use $brain-researcher-prod-rollout for web-ui, agent, br-kg, mcp, or orchestrator releases.
---

# BangHCP GCP Batch Orchestration

## Overview

Use the approved BangHCP wrapper scripts to run bounded experiment batches on
GCP. Keep CPU first, use GPU only for promoted work, sync results after each
batch, and stop workers when the next batch is not already justified.

## Read These First

Set `BANGHCP_WORKSPACE` to the BangHCP project workspace before launching
anything. This skill is project-specific and is not a generic public deployment
path.

Read these files before launching anything:

- `${BANGHCP_WORKSPACE}/banghcp_program.md`
  - read `## 18. GCP Autonomous Execution Protocol`
  - read `## Appendix A. Example Compute Envelopes`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/_common.sh`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/budget_status.sh`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/start_cpu_batch.sh`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/start_gpu_batch.sh`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/sync_results.sh`
- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/stop_all.sh`

If policy text and wrappers disagree:

- trust `banghcp_program.md` for the scientific and budget policy
- trust `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/*.sh` for the actual command surface

## Core Workflow

### 1. Classify the next batch

Use CPU by default for:

- Phase 0 audit and harness validation
- Phase 1 classical baselines and FC pruning
- reflection and analysis between GPU batches

Use GPU only for:

- promoted Phase 2 candidates
- matched-budget Phase 3 KG search-policy batches

Do not open a GPU worker just because one is available.

### 2. Check status before launch

Run:

```bash
${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/budget_status.sh
```

If the output shows stale managed workers, over-budget state, or a blocked
launch condition:

- stop or sync first
- do not launch another worker until the status is clean

### 3. Launch only approved workers

Launch a CPU batch with:

```bash
${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/start_cpu_batch.sh \
  --phase phase0-audit \
  --batch-label audit-bootstrap
```

Launch a GPU batch with:

```bash
${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/start_gpu_batch.sh \
  --phase phase2-promoted \
  --batch-label candidate-refresh
```

Do not call raw:

- `gcloud compute instances create`
- `gcloud compute instances start`
- `gcloud compute instances stop`
- `gcloud compute instances delete`

outside the wrappers.

### 4. Use the compute envelopes

Use these planning anchors from `banghcp_program.md` Appendix A:

- CPU audit / harness batch:
  - target `4-8h`
- CPU classical sweep:
  - target `24-36h`
- CPU hard upper bound for one batch:
  - target `48h`
- default promoted GPU envelope:
  - `2x L4`
  - target runtime `~37h`
  - TTL `~49h`

Treat these as decision thresholds:

- if a CPU batch exceeds `48h`, split it and reflect
- if a GPU batch materially exceeds `~49h` TTL, split it, prune it, or defer it
- treat A100-class plans as policy exceptions, not routine search infrastructure

### 5. Sync and stop

After a batch or phase boundary, run:

```bash
${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/sync_results.sh --instance <instance-name>
```

When workers should not stay alive, run:

```bash
${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/stop_all.sh
```

Prefer stopping workers between phases over letting them idle.

### 6. Reflect before escalating

Escalate from CPU to GPU only after evidence exists that:

- the baseline or pruning phase succeeded
- the next batch is promoted, not speculative
- the expected batch still fits inside the current budget box

If the next action is unclear, stop workers and reflect before spending more.

## Environment Contract

Expect these environment variables to matter:

- `BANGHCP_PROJECT_ID`
- `BANGHCP_WORKSPACE`
- `BANGHCP_GCS_BUCKET`
- `BANGHCP_CPU_TEMPLATE`
- `BANGHCP_GPU_TEMPLATE`
- `BANGHCP_PREFERRED_ZONES`
- `BANGHCP_COST_LOG`

Policy defaults live in:

- `${BANGHCP_WORKSPACE}/scripts/banghcp_gcp/_common.sh`

Read them before assuming hourly cost, runtime caps, or concurrency caps.

## Anti-Patterns

Avoid these mistakes:

- treating this as unconstrained cloud autonomy
- escalating to on-demand because Spot failed once
- keeping a GPU worker alive while only reading logs or writing reflections
- opening a larger worker than the approved template
- using `$brain-researcher-prod-rollout` for experiment VM lifecycle

## Example User Requests

This skill should trigger for requests like:

- `Use $banghcp-gcp-batch-orchestration to decide whether the next BangHCP batch should be CPU or GPU.`
- `Use $banghcp-gcp-batch-orchestration to check budget status and launch the next approved BangHCP worker.`
- `Use $banghcp-gcp-batch-orchestration to stop idle workers and sync BangHCP results after reflection.`
