degraded: ground-evidence -> grounding_gate_evidence_basis succeeded but downgraded 2 of 4 claims (c2: kg anchor `kg-DOES-NOT-EXIST` unresolvable; c3: document anchor `doc-MISSING` unresolvable); generate-report -> blocked (scientific_report_generate aborted under halt_on_review_block=true); report emission suppressed.

# Report-gate rejection handoff

The closed-loop slice did exactly what it is supposed to do for the weakest input: the evidence gate downgraded the broken claims and the kit refused to draft a final report.

## What was attempted

1. `grounding_gate_evidence_basis(partial_action="downgrade", alignment_mode="judge_parity")`
   on the four-claim `evidence_basis` in `input/weak_evidence_basis.json`.
2. `scientific_report_generate(halt_on_review_block=True)` over the gated bundle.

## What the gate returned

- 4 claims input, 4 claims gated.
- Resolution partition (per rubric):
  - `resolved`: `c1`, `c4`
  - `unresolved`: `c2`, `c3`
- BR raw coverage: `ungrounded_after_gate = 4` because no resolver maps were supplied;
  every anchor was reported as `ungrounded_basis` in `alignment.per_row[*].reason`.
- No `resolutions` were emitted; no anchor was positively confirmed by the server.

## What the report step did

- The kit observed 2 unresolved claims (`c2`, `c3`) and treated the bundle as
  failing the `ground-evidence` precondition for `generate-report`.
- Per `adapters/br-fallback-policy.md` ("What never falls back"), `generate-report`
  must not draft a report when the evidence layer is degraded.
- Exit status: `review_blocked`. No `.tex`, no PDF, no persisted report run.

## Affected intents

- `ground-evidence` -> served by BR but degraded (no positive resolutions; 2 anchors hard-fail)
- `generate-report` -> blocked (no safe fallback)

## What a downstream caller should do

- Replace `kg-DOES-NOT-EXIST` (c2) with a real KG node id, and `doc-MISSING` (c3)
  with a real document reference, then re-run the gate.
- Or, strip `c2` and `c3` from the evidence_basis and proceed with `c1` + `c4`
  if the scientific scope can be narrowed to claims those two anchors actually support.
- Do not re-issue `scientific_report_generate` until the gate's
  `coverage.ungrounded_after_gate` drops to zero (or the caller accepts the residual
  uncertainty and removes `halt_on_review_block`).
