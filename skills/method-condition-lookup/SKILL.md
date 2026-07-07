---
name: method-condition-lookup
description: The correct way to look up what method conditions a publication actually used — cohort / sample size, task paradigm, preprocessing, distance metric, statistical model — via the Brain Researcher coverage guard, reporting each field with the grounding tier the tool returns. Use whenever the user asks what a specific paper (pmid:NNNN) did methodologically.
---

# Method-Condition Lookup

## Overview

This skill enforces the one right way to answer "what did paper X actually do?".
These method-condition fields are **not** stored on the Publication node — reading
them off the node returns null. They must be routed through
`kg_method_condition_coverage_guard`, which resolves them across BR-KG stored
fields, GABRIEL cache candidates, and the NeuroStore pipeline, and returns each
field **with its grounding tier**. The discipline is to report the tier faithfully
and never relabel it.

Use it when the user asks what cohort / sample size / task paradigm / preprocessing
/ distance metric / statistical model a specific paper (or the claim it supports)
used. Do **not** use it for generic KG node lookup (`kg_get_node`) or dataset
discovery.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Call the guard** with the paper id: `kg_method_condition_coverage_guard(paper_id="pmid:NNNN")`.
   Cohort / sample size / task paradigm resolve without any flag.
2. **Read each field's tier** from the response (see `references/grounding-tiers.md`):
   `br_kg_stored`, `br_kg_gabriel_cache_candidate`, `br_kg_neurostore_pipeline`,
   `br_kg_on_demand_extracted`, or `not_applicable_to_design`.
3. **Escalate only when the tool asks.** If Methods-section fields (preprocessing,
   distance_metric, statistical_model) come back missing **and the response's
   `next_action` says so**, re-call with `enable_live_extraction=true`. Do not
   escalate reflexively.
4. **Report field-by-field with the tier.** Present each value alongside the exact
   tier the tool returned. A `br_kg_gabriel_cache_candidate` is a candidate, not a
   confirmed stored fact — say so.
5. **Absence is a result.** A field that stays missing after the allowed escalation
   is reported as "not available at any tier," never guessed or inferred.

If BR is unreachable or the guard is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not read the fields off the node or fabricate them.

## Anti-patterns

- **Do not** read method-condition fields off the Publication node (`kg_get_node`) —
  they are null there by design.
- **Do not** relabel a tier — never report a `gabriel_cache_candidate` as a
  confirmed `br_kg_stored` value, or an on-demand extraction as pre-stored.
- **Do not** enable live extraction unless the response's `next_action` calls for it.
- **Do not** infer a missing method from the abstract or a related paper; report it
  absent.
- **Do not** present a `not_applicable_to_design` field as "missing data" — it is a
  design-level N/A.

## Resources

- `references/grounding-tiers.md` — what each tier means, how confident it is, and
  the exact user-facing wording per tier.

## Example user requests

- "What sample size and task did pmid:33981209 use?"
- "What preprocessing and statistical model does this paper's claim rest on?"
- "What distance metric did they use for the connectivity analysis?"
- "Give me the method conditions behind this finding."
