---
name: gcp-gpu-request
description: Estimate GPU VRAM requirements (GB), runtime duration, and on-demand GCP instance plan for ML workloads, then generate safe request text and gcloud commands. Use when a project needs GPU capacity that is not currently available and you need to size memory, estimate time-to-complete, and provision only what is necessary.
---

# GCP GPU Request

## Overview

Use this skill to answer three questions before provisioning GPU resources:
1. How much VRAM (GB) is required?
2. How long will the workload run?
3. What is the minimal on-demand GCP request and command set?

Do not assume a public default project. Require the caller to provide a project
and zone, or read them from `GCP_PROJECT_ID` and `GCP_ZONE`.

## Workflow

1. Collect workload inputs:
   - workload mode: `infer`, `finetune`, or `train`
   - model size (billions of parameters)
   - precision (`fp32`, `fp16`, `bf16`, `int8`, `int4`)
   - sequence length and batch size
   - one runtime signal:
     - tokens + tokens/sec/GPU
     - or steps + sec/step/GPU
2. Run planner script to estimate VRAM, GPUs, duration, and TTL.
3. Review output warnings (availability, unsupported GPU counts, unknown throughput).
4. Produce a request message and generate on-demand `gcloud` commands.
5. Prefer smallest viable allocation; scale up only if utilization evidence shows need.

## Run Planner

```bash
python skills/gcp-gpu-request/scripts/plan_gcp_gpu_request.py \
  --mode finetune \
  --model-params-b 7 \
  --precision bf16 \
  --seq-len 4096 \
  --batch-size 4 \
  --gpu-type l4 \
  --total-tokens 200000000 \
  --throughput-tokens-per-sec-per-gpu 250 \
  --project "${GCP_PROJECT_ID}" \
  --zone "${GCP_ZONE:-us-west1-b}" \
  --instance-name br-gpu-job
```

## Output Contract

The planner returns JSON with:
- `estimate.required_vram_gb`
- `estimate.recommended_gpus_total`
- `estimate.estimated_hours`
- `estimate.recommended_ttl_hours`
- `estimate.recommended_disk_gb`
- `cost_estimate.hourly_cost_usd`
- `cost_estimate.estimated_run_cost_usd`
- `cost_estimate.estimated_ttl_cost_usd`
- `cost_estimate.pricing_assumptions`
- `commands.create/start/stop/delete`
- `request_markdown`
- `warnings`

## Provisioning Guardrails

1. Do not allocate persistent GPU instances by default.
2. Include stop/delete commands in every response.
3. Use conservative TTL (`estimated_hours * 1.3`, rounded up).
4. If runtime estimate is unknown, use a short checkpoint window (for example 8h) and re-estimate after profiling.
5. Avoid hardcoding credentials or service account keys in scripts.

## References

### references/

- `gpu-sizing-heuristics.md`: Memory and duration heuristics.
- `gcp-machine-family-map.md`: GPU families and machine-type mapping.
- `request-template.md`: Request message template for PI/team approval.

### scripts/

- `plan_gcp_gpu_request.py`: Deterministic estimator + command generator.
