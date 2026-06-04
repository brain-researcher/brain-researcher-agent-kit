# Self-critique — is the whole-cohort null a real null?

Source finding: `input/initial_findings.json`
- Hypothesis: trait anxiety (STAI-T) predicts right amygdala -> mPFC resting-state FC.
- Whole-cohort result: r = 0.05, p = 0.66, 95% CI [-0.17, 0.27], N = 80.
- Draft interpretation: "Hypothesis not supported."

`run_scientific_review` was attempted
and returned `{"ok": false, "error": "run not found: demo_null_result_self_critique_initial_findings"}`
because the tool is bound to persisted BR runs in `RUN_ROOT` and the demo's input is inline
JSON (see `review.json`, `_capture_notes.md`). The diagnoses below are therefore derived
from the tool's documented checklist (correctness + completeness) applied manually to the
fields actually present in `initial_findings.json`. Nothing was fabricated about effect
sizes; only the methodological gaps explicit in the input are flagged.

## Null-result diagnoses (none promoted to a confirmed finding)

1. **Granularity / aggregation masking** — A whole-cohort correlation collapses across the
   full STAI-T distribution. Healthy adult cohorts often cluster in the low-to-mid trait-
   anxiety range; if the hypothesised amygdala-mPFC coupling is gated by clinically
   elevated anxiety, the relationship can be invisible at the cohort level even when
   present in a subgroup. The 95% CI [-0.17, 0.27] is wide enough that a moderate
   subgroup effect would be statistically compatible with the cohort null.
2. **Missing provenance / weak preregistration signal** — `initial_findings.json` does not
   declare seed-ROI version, atlas version, motion-scrubbing threshold, global-signal
   regression choice, or run/session ordering. The deterministic completeness checklist
   that `run_scientific_review` would apply (seed pinned, atlas versioned, ordering
   declared) cannot be satisfied from the provided fields. A null with unspecified
   preprocessing is ambiguous between "real null" and "method-induced null."
3. **Confounders not controlled in the reported model** — Age, sex, head-motion summary
   (mean FD), and medication/caffeine status are common moderators of amygdala-mPFC
   coupling and of self-reported anxiety. The reported Pearson r is unadjusted; an
   unadjusted whole-cohort null is consistent with a true effect that is masked by
   opposing covariate-linked variance.
4. **Weak labels / instrument range** — STAI-T in a healthy N=80 sample is likely
   right-skewed and bounded away from the clinical range. Restricted variance attenuates
   Pearson correlations mechanically; the null can be a range-restriction artifact rather
   than evidence of absent association.

## Single exploratory follow-up (one, per the user prompt)

**Exploratory subgroup analysis:** restrict to participants with STAI-T >= 45 (a commonly
used "high trait anxiety" cut) and re-estimate the right-amygdala -> mPFC seed-based
connectivity / STAI-T Pearson correlation within that subgroup only.

This proposal is **exploratory, not confirmatory**:
- it is selected post-hoc after observing the whole-cohort null,
- it is not preregistered,
- the subgroup sample size will be smaller than N=80 and statistically under-powered,
- any subgroup effect will be reported as hypothesis-generating only.

The plan was validated via `pipeline_plan_validate` (see `exploratory_plan.json` and
`validate.json`). The first plan revision was rejected for using unregistered tool names
(`behavior_filter`, `pearson_correlation`, `report_tagger`) and for a missing required
`img` param on `seed_based_fc`; the second revision validated with `ok: true`, zero
issues, and code-review decision `approve`. No execution was run.
