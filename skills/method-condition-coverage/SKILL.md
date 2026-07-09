---
name: method-condition-coverage
description: Continue the BR-KG method-condition coverage line — check the GABRIEL extraction fleet, ingest the accepted manifest into the prod KG, adversarially quality-audit, and re-run the reviewer's exact query via kg_method_condition_coverage_guard to prove reachability. Use when the user says "继续 method-condition 线", asks the extraction fleet's status, or wants BR-KG method fields (preprocessing / distance_metric / statistical_model) populated.
---

# method-condition-coverage

Make the manuscript claim "BR-KG records method conditions per recommendation" true: extract
granular method conditions from full text, ingest them into the KG, and prove a reviewer's query now
returns non-null Methods fields with their grounding tier. This wraps a long orchestration the user
has re-pasted verbatim many times.

## When to use

- "继续 method-condition 线" / "现在 fleet 的 status 呢" / "make the method fields non-null".
- A reviewer (e.g. Jeanette) reports BR-KG returns null `preprocessing` / `distance_metric` /
  `statistical_model`.
- NOT for: building a new extraction template from scratch (that is a GABRIEL authoring task);
  reading a single paper's methods (just call `kg_method_condition_coverage_guard` directly).

## Prerequisites

- Prod KG target is the k3s VM (see the `br-rollout` skill / `reference_prod_rollout` memory); operate
  via `gcloud compute ssh ... "sudo k3s kubectl ..."`.
- Neo4j / API creds come from `.env` (`set -a && source .env && set +a`); never inline or print them.
- GABRIEL extraction runs against the KG ∩ pubget full-text intersection (paid Gemini SDK, full text
  required). Long fleets run hours — launch in background, poll with `Monitor`, reschedule if unfinished.

## Client adapters

This skill ships two client-launch adapters alongside `SKILL.md`:

- `agents/openai.yaml` — Codex/OpenAI skill launch metadata (display name, trigger prompt).
- `agents/claude_code.md` — a compact Claude Code instruction block.

Keep both in this skill directory; do not duplicate the policy into `CLAUDE.md` (repo convention:
instructions live in AGENTS.md; CLAUDE.md only points there).

## Workflow

1. **Fleet-progress check** — is the extraction fleet still running? If yes, reschedule (e.g. a
   wakeup) instead of blocking; do not busy-poll with foreground `sleep`.
2. **Build the accepted manifest** — dedupe extracted method conditions into an ingest manifest:
   `scripts/br-kg/build_deduped_gabriel_accepted_manifest.py` (and, for the deep-research path,
   `scripts/deep_research_to_gabriel_manifest.py`).
3. **Bundle → transfer → ingest into prod KG** — `tar` the manifest, `gcloud compute scp` it to the
   VM, then run `scripts/br-kg/batch_ingest_gabriel_manifest_to_neo4j.py` inside a `kubectl exec`
   against the br-kg pod (materializes `MethodCondition` nodes + `HAS_METHOD_CONDITION` edges).
4. **Reachability verify (the load-bearing step)** — re-run the reviewer's *exact* query via
   `kg_method_condition_coverage_guard` for the affected `pmid:`/`doi:`; assert the Methods fields are
   now non-null and report each with the grounding tier the tool returns (`br_kg_stored`,
   `br_kg_gabriel_cache_candidate`, `br_kg_neurostore_pipeline`, `br_kg_on_demand_extracted`,
   `not_applicable_to_design`). Do NOT read these off the Publication node's own properties.
5. **Adversarial quality audit** — spot-check a sample against the source Methods section for
   fabricated / mis-attributed conditions before declaring coverage.
6. **Tear down** the ingest pod; emit a structured status: `done / open / next`.

## Honesty / invariants

- Coverage % must be measured on the KG ∩ pubget intersection actually processed — `log()` what was
  dropped; don't imply full-corpus coverage.
- "ingested" ≠ "reachable": the run isn't done until step 4's real query returns the fields.
- Standing prod-safety constraints: branch off `origin/master`, work in a `/tmp` worktree, omit the
  Claude `Co-Authored-By` trailer, and get explicit per-cycle authorization before the prod write.

## Related memory

`project_method_condition_coverage`, `reference_prod_rollout`, `feedback_verify_mechanism_engaged`.
MCP: the brain-researcher server instructions cover `kg_method_condition_coverage_guard` and its
`enable_live_extraction=true` fallback.
