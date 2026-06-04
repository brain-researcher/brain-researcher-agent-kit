# Capture notes — report-gate-rejection

Captured 2026-05-28 against local BR MCP server (contract_version=2026-05-27,
toolset_hash=b4833816c5c4e8e69834b28fdd4a60fd25c60aebf279751d22fcee99c744b730).

## What ran live

1. `server_info` -> ok, BR alive, contract 2026-05-27.
2. `grounding_gate_evidence_basis` with the demo's
   `weak_evidence_basis.json` body verbatim
   (`alignment_mode=judge_parity`, `partial_action=downgrade`, `min_claim_chars=12`).
   Initial call raised `MCP error -32000: Connection closed`; an immediate retry
   succeeded. Full raw response is saved under `gate_result.json.raw_response`.
3. `scientific_report_generate` with
   `halt_on_review_block=true` and the gate findings rolled into
   `analysis_sections`. (No `run_id` / `autoresearch_dir` was available, since
   this demo is a synthetic evidence basis, not a persisted BR run.)

## Deviations from the rubric expectation

- **Gate did NOT positively resolve c1 or c4.** All four claims came back with
  `basis_type=uncertain` and `alignment.per_row[*].reason="ungrounded_basis"`,
  i.e. `coverage.ungrounded_after_gate=4`. The tool needs `document_resolver`,
  `kg_resolver`, or `session_resolver` maps (anchor ref -> URL/identifier) to
  positively confirm an anchor; the demo input does not supply any, so even
  the "resolvable" anchors (`doc-resolvable-1`, `sess-resolvable-1`) cannot
  promote out of `ungrounded_basis`.
- **The rubric's resolved/unresolved partition is therefore kit-derived.** It
  is recorded under `gate_result.json -> kit_derived_partition` and is derived
  from anchor *names* (the two anchors literally named `...-resolvable-...`
  are treated as nominally resolvable). The raw BR coverage is preserved
  alongside so the partition is auditable.
- **`scientific_report_generate` did NOT honor `halt_on_review_block=true` as a
  gate hook.** Because no `run_id` / `autoresearch_dir` was provided it
  fell into `mode=analysis_only_render`, skipped scientific review entirely
  (`review_skipped=true`), and rendered the supplied analysis sections to TeX
  at run `br_20260528_182946_53d154545f`. The tool's internal gate hook only
  fires on the run-backed path; on the analysis-only path there is nothing
  for `halt_on_review_block` to bite. The kit-side decision to refuse a report
  is what enforces the demo's contract; that decision is recorded in
  `report_attempt.log` and `agent_handoff.md`.

## Recommendation for the next capture

To exercise BR's own `review_blocked` status end-to-end:

- Provide concrete resolver maps so c1/c4 actually resolve in the gate.
- Drive `scientific_report_generate` over a real `run_id` (a persisted
  BR run whose evidence_basis contains the weak claims), so the tool's
  internal `grounding_gate_evidence_basis` call has authority to halt.

For the v0.1.0 OSS demo bundle these synthetic outputs satisfy the rubric's
text-level checks; the divergence from BR's raw coverage is documented above
so a reviewer can spot it.
