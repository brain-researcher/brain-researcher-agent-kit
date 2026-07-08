# Null-result triage: check → action

Consulted at Workflow step 4 (BLOCKING diagnosis) and step 7 (decide). A weak or
non-significant main effect is **not** a final null until every check below is
cleared. Each check has a symptom, how to test it, and what to do if it fires.

## The five checks

| Check | Symptom of the artifact | How to test | If it fires |
|---|---|---|---|
| **Granularity** | effect averaged away at too coarse a level (whole-brain, all-trials, all-subjects) | re-slice finer: ROI/network, per-condition, per-group; `run_compare` split deltas | re-run at the corrected granularity before calling it null |
| **Confounders** | motion, TR, site, age, task timing not controlled | check the model/covariates in `run_bundle_get`; `companion_diagnostic_suggester` for the metric | add the confounder and re-fit; do not report the null yet |
| **Labels** | placeholder / weak / mislabeled conditions or groups | inspect the design/label fields in the bundle | fix labels and re-run; a null over bad labels is meaningless |
| **Filters / QC** | no QC subset; failed scans/subjects included | check filtering in the bundle/scorecard | re-run on the QC-passed subset |
| **Outcome definition** | outcome too broad to show the effect | check the contrast/outcome spec | narrow the outcome and re-run |

## Decision at step 7

After the checks + at least one exploratory follow-up (step 6):

| Situation | Report as |
|---|---|
| all five checks clear AND the effect is still absent | **genuine final null** (state the checks that were done) |
| a check fired and a corrected re-run is warranted | **re-run at corrected granularity/definition** — not a null yet |
| overall weak but an exploratory slice shows signal | **downgrade to exploratory** — report the slice, labeled exploratory, not as confirmatory |

Use `refuted_landscape_summary` to roll structured findings into
supported / refuted / **inconclusive** (keep inconclusive distinct from refuted).

## Hard rules

- Do not report a weak/null result as a **final** null until all five checks are
  cleared and at least one exploratory follow-up was run.
- Every post-hoc / subgroup finding is **exploratory** — label it, never present it
  as confirmatory.
- Do not accept a "review complete" line on a stale/empty run — assert the review
  ran over the real evidence.
