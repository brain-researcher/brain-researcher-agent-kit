# Method-condition grounding tiers

`kg_method_condition_coverage_guard` returns each method-condition field with a
grounding tier. The tier is the field's provenance — report it verbatim; it is the
difference between a stored fact and a candidate guess.

| Tier | Meaning | Confidence | Say it as |
|---|---|---|---|
| `br_kg_stored` | curated/stored in BR-KG | highest | "recorded in BR-KG: …" |
| `br_kg_neurostore_pipeline` | resolved via the NeuroStore pipeline | high | "from NeuroStore: …" |
| `br_kg_gabriel_cache_candidate` | a GABRIEL extraction *candidate* in cache | medium — candidate | "candidate (GABRIEL cache), not confirmed stored: …" |
| `br_kg_on_demand_extracted` | extracted live this call (Methods section) | medium — freshly extracted | "extracted on demand from the Methods section: …" |
| `not_applicable_to_design` | the field does not apply to this study design | n/a | "not applicable to this design" |

## Escalation rule

- Cohort / sample_size / task_paradigm resolve **without** any flag.
- preprocessing / distance_metric / statistical_model may come back missing. Only if
  the response's `next_action` says to, re-call with `enable_live_extraction=true`
  (this triggers `br_kg_on_demand_extracted`).
- Do not escalate fields that already resolved, and do not escalate just because a
  field is missing if `next_action` does not ask.

## Never

- Never promote a `gabriel_cache_candidate` or `on_demand_extracted` value to
  `br_kg_stored` in your wording.
- Never fill a missing field from the abstract, a sibling paper, or prior belief.
