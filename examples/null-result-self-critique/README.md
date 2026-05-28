# Demo · null-result-self-critique

**Closed-loop slice**: initial null result → critique → exploratory follow-up → labeled report.

## What this exercises

This is the demo that proves the kit's central discipline: **a null result is not a finished report**.

| Step | Intent | Tool |
|---|---|---|
| 1 | (initial analysis) | `pipeline_plan_validate` + caller-side execution |
| 2 | self-critique | `run_scientific_review` (discovered via `tool_search`) |
| 3 | exploratory follow-up | second `pipeline_plan_validate` against a subgroup or condition |
| 4 | ground-evidence | `grounding_gate_evidence_basis` on the final claims |
| 5 | generate-report | `scientific_report_generate` |

## Inputs

- `input/initial_findings.json` — a synthetic weak/null effect at the whole-cohort level.
- `input/critique_prompt.md` — the user-facing question that triggers the self-critique path.

## Expected output

- `expected_output/critique.md` — null-result diagnosis (granularity, confounders, weak labels) + one exploratory follow-up proposal.
- `expected_output/followup_findings.json` — the second-pass result on the proposed subgroup.
- `expected_output/report.md` — final report explicitly labeling `confirmatory:` vs `exploratory:` claims.

**TODO**: capture from live BR MCP run.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares rejection-quality (null not reported as final without a diagnosis) and provenance (exploratory claims labeled).
