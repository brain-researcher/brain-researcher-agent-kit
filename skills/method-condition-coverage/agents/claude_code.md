# Claude Code Prompt: BR-KG Method-Condition Coverage

Use this block when Claude Code continues the Brain Researcher method-condition
coverage line — populating BR-KG method fields and proving a reviewer's query
returns them.

```text
Use the Brain Researcher MCP tools if they are exposed in this Claude Code
session. Inspect the actual tool list first; do not invent tool names.

For a real method-condition coverage cycle:

1. Check whether the GABRIEL extraction fleet is still running. If it is,
   reschedule a wakeup instead of busy-polling with foreground sleep.
2. Build the accepted manifest by deduping extracted method conditions
   (scripts/br-kg/build_deduped_gabriel_accepted_manifest.py).
3. Ingest into the prod KG only after explicit per-cycle authorization: bundle,
   gcloud compute scp to the k3s VM, and run
   scripts/br-kg/batch_ingest_gabriel_manifest_to_neo4j.py via kubectl exec
   against the br-kg pod (creates MethodCondition nodes + HAS_METHOD_CONDITION
   edges).
4. Reachability is load-bearing: re-run the reviewer's exact query via
   kg_method_condition_coverage_guard for the affected pmid:/doi: and assert the
   Methods fields are non-null. Report each field with the grounding tier the
   tool returns (br_kg_stored, br_kg_gabriel_cache_candidate,
   br_kg_neurostore_pipeline, br_kg_on_demand_extracted,
   not_applicable_to_design). Never read these off the Publication node's own
   properties.
5. Adversarially spot-check a sample against the source Methods section before
   declaring coverage.
6. Never inline or print .env creds. Measure coverage % only on the
   KG ∩ pubget intersection actually processed.

If the BR MCP server is inactive or unavailable, say so and continue with a
concise local handoff; do not imply that ingest or a reachability query ran.
```

Good final handoff shape:

```text
changed: <manifest / KG nodes+edges ingested>
verified: <kg_method_condition_coverage_guard query + grounding tiers>
open: <coverage gaps, dropped papers, blockers>
next_command: <one concrete command for resumption>
```
