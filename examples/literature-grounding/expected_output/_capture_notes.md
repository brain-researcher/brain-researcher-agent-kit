# Capture notes — literature-grounding

Captured 2026-05-28 against `mcp__brain-researcher-local` (live).

## Tool calls

1. `grounding_resolve(ref="document:doc-1", document_resolver={"doc-1": "Schmahmann 2019 Cerebellar Cognitive Affective Syndrome"})`
   → `{resolved: false, error: "document_anchor_unresolved"}`
2. `grounding_resolve(ref="document:doc-2", document_resolver={"doc-2": "Buckner 2013 The Cerebellum and Cognitive Function"})`
   → `{resolved: false, error: "document_anchor_unresolved"}`
3. `grounding_resolve(ref="kg:cerebellum_prefrontal_connectivity", kg_resolver={"kg-cerebellum-prefrontal": "cerebellum_prefrontal_connectivity"})`
   → `{resolved: false, error: "kg_anchor_unresolved"}`
4. `grounding_gate_evidence_basis(evidence_basis=[4 rows], document_resolver=..., kg_resolver=...)`
   → `{resolved: [], degraded_count: 0, coverage: {grounded_in: 0, grounded_out: 0, ungrounded_after_gate: 4}, alignment.skipped: 4 (reason: ungrounded_basis)}`
   → all 4 rows came back `basis_type="uncertain"` with `reference=null`.

## Interpretation

The local BR server has **no document store or KG record** for the three candidate anchors supplied in `input/question.json`. This is the expected behavior for a fresh kit environment without ingested papers — the gate correctly refuses to ground claims it cannot back, and the rubric's hedging clause (`"evidence not resolved" prefix`) is the path forward.

The captured `answer.md` therefore asserts no citation-backed claims; every claim is hedged. This is a faithful capture of what the BR MCP grounding chain actually does when the candidate anchors are unknown — not a fabricated success.

## Blockers / follow-ups (for a future re-capture)

- To exercise the `resolved[]` arm of the rubric, ingest Schmahmann 2019 and Buckner 2013 into the BR document store and add a `cerebellum_prefrontal_connectivity` fact to the KG, then re-run.
- No tool errored; nothing was "degraded" in the strict sense — all calls returned `ok: true`. The unresolved status is data-driven, not error-driven.
