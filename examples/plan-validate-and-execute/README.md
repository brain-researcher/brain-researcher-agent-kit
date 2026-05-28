# Demo · plan-validate-and-execute

**Closed-loop slice**: preflight → validate → review → execute recipe.

## What this exercises

| Step | Intent | Tool |
|---|---|---|
| 1 | inspect-tools | `server_info`, `tool_search` |
| 2 | preflight-plan | `plan_preflight` |
| 3 | validate-plan | `pipeline_plan_validate` |
| 4 | review-plan | `pipeline_plan_review` |
| 5 | get-execution-recipe | `get_execution_recipe` |

## Inputs

- `input/plan.json` — a 3-step fMRI preprocessing plan (skull-strip → motion-correction → registration).
- `input/dataset_facts.json` — minimal dataset descriptor for preflight.

## Expected output

- `expected_output/preflight.json` — candidate-tool list + blockers.
- `expected_output/validate.json` — normalized plan + issues.
- `expected_output/review.json` — CodeReviewVerdict (decision, risk_level, findings).
- `expected_output/recipe.json` — runnable recipe for the first step.

**TODO**: capture from live BR MCP run.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares validity (every produced artifact references a real step) and reliability (rerun yields the same `normalized_plan.steps`).
