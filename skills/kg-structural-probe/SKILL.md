---
name: kg-structural-probe
description: Probe the Brain Researcher knowledge graph for structural leverage, contradiction motifs/frontiers, assumption cracks, analogy transfers, and refuted directions — to find where the field is contested or thin, not to confirm a hypothesis. Use when a user wants to explore what's contradictory, under-supported, or high-leverage in a research area, or to map refuted vs supported directions.
---

# KG Structural Probe

## Overview

This skill is for *exploring the shape of the evidence*, not screening a specific
claim: where the knowledge graph shows contradiction, thin assumptions, high
structural leverage, or transferable analogies — and which directions are already
refuted. Its discipline is that a probe surfaces **structure to investigate**, not a
verdict: a contradiction motif is a question to chase, and a "high-leverage" node is
a lead, not a finding.

Use it when the user wants to find contested / under-supported / high-leverage areas,
map refuted-vs-supported directions, or look for analogy transfers. Do **not** use it
to screen candidate hypotheses for support (that is
`kg-hypothesis-discovery-and-verification`) or to ground a claim's anchors
(`evidence-grounding`).

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Seed the region of the graph.** `kg_search_nodes` / `kg_get_node` /
   `kg_neighbors` to pin the entities the probe starts from. Report degraded KG reads.
2. **Probe the structure** with `kg_probe(probe_type=...)` — pick the probe for the
   question (see `references/probe-types.md`): `structural_leverage`,
   `contradiction_motifs`, `contradiction_frontiers`, `assumption_cracks`,
   `analogy_transfers`. Pass `seed_kg_ids` / `start_kg_ids` as required.
3. **Trace multi-hop questions** with `kg_multihop_qa` when the question spans hops
   ("what connects X to Y across the graph?"); report degraded/timeout explicitly.
4. **Map refuted directions** with `refuted_landscape_summary` over structured
   findings to see supported / refuted / inconclusive at a glance.
5. **Report structure as leads.** Present contradictions, cracks, and leverage as
   *investigable questions* with their evidence, not as conclusions. A promising lead
   still has to go through discovery+verify before it is a claim.

If BR is unreachable or a probe tool is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not fabricate contradictions or leverage.

## Anti-patterns

- **Do not** report a contradiction motif / high-leverage node as a finding — it is a
  question to investigate, not a verdict.
- **Do not** turn a probe lead into a stated claim without running discovery+verify
  (`kg-hypothesis-discovery-and-verification`) on it.
- **Do not** hide a degraded/timeout `kg_multihop_qa` result; surface it — a thin
  traversal is not "no contradictions exist."
- **Do not** invent a seed node id; seed-ground first.
- **Do not** present `refuted_landscape_summary` "inconclusive" as "refuted" or
  "supported."

## Resources

- `references/probe-types.md` — what each `kg_probe` probe_type finds and when to
  reach for it vs `kg_multihop_qa` vs `refuted_landscape_summary`.

## Example user requests

- "Where is the literature on default-mode connectivity contradictory?"
- "Find high-leverage nodes / assumption cracks around reward prediction error."
- "What directions in this area are already refuted vs supported?"
- "Is there an analogy transfer from motor learning to this task?"
