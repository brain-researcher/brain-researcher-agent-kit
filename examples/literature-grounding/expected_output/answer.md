# Grounded Answer: Cerebellar Contribution to Non-Motor Cognition

**Question.** What is the current evidence that the cerebellum contributes to non-motor cognitive tasks beyond timing?

## Grounding status

A live call to `grounding_resolve` against the BR MCP server was issued for each candidate anchor supplied in `input/question.json`. **None of the three anchors resolved** against the locally indexed document store or knowledge graph:

| Candidate | Ref | Reference kind | Resolved | Error |
|---|---|---|---|---|
| doc-1 (Schmahmann 2019, CCAS) | `document:doc-1` | retrieved_document | false | `document_anchor_unresolved` |
| doc-2 (Buckner 2013, Cerebellum & Cognitive Function) | `document:doc-2` | retrieved_document | false | `document_anchor_unresolved` |
| kg-cerebellum-prefrontal | `kg:cerebellum_prefrontal_connectivity` | kg_fact | false | `kg_anchor_unresolved` |

A subsequent call to `grounding_gate_evidence_basis` over the candidate evidence basis returned `basis_type="uncertain"` for every row, `resolved=[]`, and `coverage.ungrounded_after_gate=4`. Full machine-readable records are in `resolved_evidence.json` and `scorecard.json`.

## Answer (with mandatory hedging)

Per the demo rubric, no claim may be asserted on the strength of an anchor that the gate did not resolve. Because every candidate anchor landed in `unresolved[]`, every substantive claim below is prefixed with **"evidence not resolved"**.

1. **evidence not resolved** — The cerebellum is widely *reported* in the secondary literature to contribute to executive function, language, and visuospatial cognition via crossed cerebro-cerebellar loops, but the supporting anchor (Schmahmann 2019, CCAS) was not resolved by `grounding_resolve` against the local BR document store, so this claim is downgraded to `uncertain` and is not citation-backed in this run.
2. **evidence not resolved** — Resting-state fMRI is *reported* to show cerebellar functional connectivity with prefrontal and parietal association cortices, but the supporting anchor (Buckner 2013) was not resolved by `grounding_resolve`, so this claim is downgraded to `uncertain`.
3. **evidence not resolved** — Cerebellar lesions are *reported* to produce Cerebellar Cognitive Affective Syndrome (CCAS) with deficits in executive function, visuospatial cognition, language, and affect regulation, but the supporting anchor (Schmahmann 2019) was not resolved, so this claim is downgraded to `uncertain`.
4. **evidence not resolved** — The cerebellum is *reported* to participate in distributed cognitive networks through reciprocal connectivity with prefrontal cortex, but the supporting KG anchor (`cerebellum_prefrontal_connectivity`) was not resolved by `grounding_resolve`, so this claim is downgraded to `uncertain`.

## Citations

No citations are asserted. All four candidate claims were downgraded by `grounding_gate_evidence_basis` and appear in `scorecard.json::downgraded[]` and `scorecard.json::unresolved[]`. To upgrade any claim from `uncertain` to grounded, the corresponding paper or KG fact must first be ingested into the BR document store / Neo4j KG so that `grounding_resolve` returns `resolved=true`.

## Provenance

- Tool 1: `grounding_resolve` (3 invocations, one per candidate anchor) — see `resolved_evidence.json`.
- Tool 2: `grounding_gate_evidence_basis` (1 invocation over the 4-row candidate basis) — see `scorecard.json`.
- Captured: 2026-05-28 (live Brain Researcher MCP server).
