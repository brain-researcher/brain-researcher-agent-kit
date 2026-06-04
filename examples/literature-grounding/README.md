# Demo · literature-grounding

**Closed-loop slice**: paper-qa-style grounded answer with citations.

## What this exercises

| Step | Intent | Tool |
|---|---|---|
| 1 | inspect-tools | `server_info`, `tool_search` |
| 2 | (literature retrieval) | `deepxiv` or `google_deep_research` (not stable-tier; discovered via `tool_search`) |
| 3 | ground-evidence | `grounding_resolve`, `grounding_gate_evidence_basis` |

## Inputs

- `input/question.json` — a single research question + a few candidate paper anchors.

## Expected output

- `expected_output/answer.md` — a grounded answer that cites only resolved anchors and explicitly downgrades any unresolved claim.
- `expected_output/scorecard.json` — captured `grounding_gate_evidence_basis` result showing `downgraded[]` and `unresolved[]` arrays.

The committed `expected_output/` fixture is captured, sanitized, and scoreable
offline with the demo runner.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares which `evals/rubrics/*.yaml` apply. For this demo: validity (every cited claim resolved) and provenance (anchor refs present per claim).
