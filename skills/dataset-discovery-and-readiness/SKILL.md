---
name: dataset-discovery-and-readiness
description: Find a dataset for a construct or hypothesis and confirm it is actually runnable before committing a plan — mention is not readiness. Use before planning an analysis, to go from "which dataset for X?" to a resource record with a real path/BIDS root/derivative + access readiness that a plan can safely consume.
---

# Dataset Discovery & Readiness

## Overview

This skill is the front-half that must precede planning: discover a dataset for the
construct/hypothesis, then **confirm it is runnable**. Its discipline is
resource-before-commit — a dataset being *mentioned* in the knowledge graph is not
enough to hand to a plan; commitment requires a resource record with a real local
path or URL, a BIDS root, derivative readiness, phenotype availability, access
constraints, and backend reachability.

Use it before planning an analysis, when the user asks "find me a dataset for X" or
"can we actually run this on <dataset>?". Hand off to the `plan-validation` skill
(which begins at `plan_preflight`) once readiness is confirmed.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Discover candidates** for the construct/hypothesis:
   - `kg_search_datasets` / `kg_related_datasets` — dataset subgraph search.
   - `kg_behavior_to_fmri_retrieval` — behavior → task-fMRI dataset evidence.
   - `kg_list_dataset_onvoc_links` — ontology links for a dataset.
2. **Confirm readiness** with `dataset_get_resources` for each serious candidate:
   local path / URL present? BIDS root? derivatives available? phenotype/covariates?
   access constraints? backend reachable?
3. **Gate on readiness.** A candidate that is only *mentioned* (no resource record)
   is a lead, not a runnable dataset. Do not pass it to a plan.
4. **Preflight the winner.** `plan_preflight` on the ready dataset to surface any
   remaining missing inputs / blockers before committing a plan.
5. **Report the readiness state** honestly: which datasets are runnable now, which
   need access/derivatives, and which are mentions only.

If BR is unreachable or a discovery tool is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not assert a dataset is runnable without a resource record.

## Anti-patterns

- **Do not** hand a merely-*mentioned* dataset to a plan — commitment needs a
  `dataset_get_resources` readiness record.
- **Do not** assume derivatives / phenotype exist because the raw dataset does;
  confirm each.
- **Do not** ignore access constraints or backend reachability — an unreachable
  dataset is not ready.
- **Do not** skip `plan_preflight` on the chosen dataset before planning.
- **Do not** describe discovery/readiness as having run an analysis.

## Resources

None — this is a clean tool-sequence discipline. Readiness fields to check are
listed in the Workflow.

## Example user requests

- "Find an fMRI dataset for working memory and check we can actually run it."
- "Is ds000114 ready to run — BIDS, derivatives, access?"
- "Which datasets match this hypothesis and are runnable now?"
- "Get me a dataset for response inhibition with phenotype data available."
