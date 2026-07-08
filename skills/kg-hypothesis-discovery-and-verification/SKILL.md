---
name: kg-hypothesis-discovery-and-verification
description: The discover-then-screen loop for Brain Researcher hypotheses — sample candidate hypotheses from the knowledge graph and then verify each against KG (and optionally literature) evidence before any is reported as supported. Use when the user asks for hypotheses about a construct/region/task, or asks whether a set of candidate hypotheses actually holds up.
---

# KG Hypothesis Discovery & Verification

## Overview

This skill runs the daily **discover → screen** loop: seed-ground the entities,
sample candidate hypotheses from the knowledge graph, then verify each candidate
against evidence. Its discipline is the separation the paper insists on — a
*sampled* or *frontier* candidate is a **question**, not a finding, and retrieval
strength ranks candidates but never accepts them.

Use it when the user wants hypotheses about a construct / region / task, or hands
you candidate hypotheses and asks "are these actually supported?". Do **not** use
it to ground the anchors of an *already-formed* claim you are about to state — that
is the `evidence-grounding` skill.

Authored against Brain Researcher MCP `contract_version >= 2026-07-08`.

## Workflow

1. **Seed-ground the entities.** `kg_search_nodes` / `kg_get_node` / `kg_neighbors`
   to pin the real KG entities (construct, region, task) the hypotheses will be
   about. Report degraded/timeout KG reads explicitly; do not proceed on a guessed id.
2. **Sample candidates.** `kg_hypothesis_workflow(operation="sample")` (or
   `kg_hypothesis_candidate_cards` for synchronous cards; for long runs
   `kg_hypothesis_candidate_cards_start` + `_get`). Treat every returned candidate
   as a question to be screened, not a result.
3. **Verify each candidate.** `kg_verify_hypothesis` per candidate (or
   `kg_hypothesis_workflow(operation="sample_and_verify")`). Optionally set
   `use_external_literature=True` to fold in literature evidence. Read the
   supporting **and** conflicting evidence and the confidence tier.
4. **Report with the tier.** A candidate is "supported" only if verification
   returns supporting evidence at the required tier. State the tier, the
   conflicting evidence, and rank by retrieval strength *without* letting the rank
   substitute for acceptance.
5. **Quarantine the rest.** Unverified / conflicted / insufficient-evidence
   candidates stay labeled as open questions — never promoted to findings.

If BR is unreachable or a KG/hypothesis tool is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not fabricate candidates or verdicts.

## Anti-patterns

- **Do not** report a sampled/frontier candidate as a supported finding without a
  `kg_verify_hypothesis` verdict at the required tier.
- **Do not** let a high retrieval-strength / ranking score stand in for acceptance
  — ranking is not verification.
- **Do not** hide the conflicting evidence or the confidence tier; a one-sided
  "supported" is a misreport.
- **Do not** invent a KG node id; seed-ground first, and surface a degraded KG read
  instead of guessing.
- **Do not** promote any verified candidate into accepted memory/KG here — that is a
  separate, verdict-gated step (see `session-lessons-to-memory-promotion`).

## Resources

- `references/discovery-verify-decision-table.md` — the `operation` (sample /
  verify / sample_and_verify) and `strictness` / `candidate_lane_mode` → status
  wording map, the sync-vs-async (start/get) branch, and the literature-augmented
  option.

## Example user requests

- "Generate some hypotheses about the dlPFC and working memory."
- "I have five candidate hypotheses — which ones does the evidence actually support?"
- "Screen these term×region associations against the knowledge graph."
- "Find frontier hypotheses at the edge of what's known about response inhibition."
