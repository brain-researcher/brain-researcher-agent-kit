# Demo · report-gate-rejection

**Closed-loop slice**: an evidence basis with weak/unresolved anchors is correctly downgraded and the report is blocked.

## What this exercises

This demo proves the kit fails closed for the weakest input. It is the rejection-quality counterpart to `literature-grounding`.

| Step | Intent | Tool |
|---|---|---|
| 1 | ground-evidence | `grounding_gate_evidence_basis(partial_action="downgrade")` |
| 2 | (caller decides not to render) | — |
| 3 | generate-report (negative path) | `scientific_report_generate(halt_on_review_block=True)` exits with `review_blocked` |

## Inputs

- `input/weak_evidence_basis.json` — a constructed evidence_basis where 2 of 4 anchors fail to resolve (one bad KG ref, one missing document anchor).

## Expected output

- `expected_output/gate_result.json` — `grounding_gate_evidence_basis` output showing 2 anchors in `unresolved[]` and 2 in `downgraded[]`.
- `expected_output/report_attempt.log` — `scientific_report_generate` exits with `review_blocked` status; no `.tex` produced.
- `expected_output/agent_handoff.md` — the kit's degraded-mode summary explaining what was blocked and why.

The committed `expected_output/` fixture is captured, sanitized, and scoreable
offline with the demo runner.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares rejection-quality (gate did downgrade) and validity (no final report emitted from blocked evidence).
