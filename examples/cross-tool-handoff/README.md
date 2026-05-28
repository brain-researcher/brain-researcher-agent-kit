# Demo · cross-tool-handoff

**Closed-loop slice**: an artifact produced by one stable-tier tool flows into another with explicit provenance.

## What this exercises

| Step | Intent | Tool |
|---|---|---|
| 1 | preflight-plan | `plan_preflight` |
| 2 | validate-plan | `pipeline_plan_validate` |
| 3 | (caller executes the validated plan) | local runner |
| 4 | score-run | `run_scorecard` |
| 5 | generate-report | `scientific_report_generate(run_id=...)` |

The handoff chain: `plan_preflight.candidate_tools[*].name` → input to validate → run_id from execution → `run_scorecard` → `scientific_report_generate`.

## Inputs

- `input/cross_tool_request.json` — high-level analysis request that names two BR tools that should chain.

## Expected output

- `expected_output/handoff_chain.json` — `{step, tool, output_artifact_sha256, consumed_by_step}` rows.
- `expected_output/report.md` — final report that cites each step's provenance.

**TODO**: capture from live BR MCP run.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares provenance (every claim traces to an `output_artifact_sha256` in the chain).
