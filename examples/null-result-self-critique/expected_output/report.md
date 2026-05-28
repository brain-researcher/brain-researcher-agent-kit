# Trait anxiety and amygdala-mPFC resting-state connectivity — final report

**Demo**: null-result-self-critique
**Closed-loop chain**: initial null -> `run_scientific_review` -> exploratory subgroup plan -> `pipeline_plan_validate` -> labeled report.
**Provenance discipline**: confirmatory and exploratory claims are kept in separate sections; the exploratory section is NOT promoted to a primary result.

---

## confirmatory: whole-cohort null on the preregistered test

**Hypothesis (preregistered).** Trait anxiety (STAI-T) predicts right amygdala -> mPFC resting-state functional connectivity in N=80 healthy adults.

**Result (from `input/initial_findings.json`, unchanged).**
- Pearson r = 0.05
- p = 0.66
- 95% CI = [-0.17, 0.27]
- N = 80

**Confirmatory verdict.** The whole-cohort test is null. The data are consistent with no association between STAI-T and right-amygdala / mPFC resting-state FC at the cohort level. This is the only finding that survives as a confirmatory claim.

**What the draft interpretation overstated.** `interpretation_draft` in the input read "Hypothesis not supported." We retain that as a confirmatory null but explicitly do NOT conclude that the hypothesis is false in general — the self-critique below identifies specific reasons a real effect could be masked at the whole-cohort level.

**Self-critique tool invocation.** `mcp__brain-researcher-local__run_scientific_review` was called with `run_id="demo_null_result_self_critique_initial_findings"` and returned `{"ok": false, "error": "run not found: ..."}` — it requires a persisted BR run, which this inline-JSON demo does not have. The critique that follows applies the tool's documented deterministic checklist (correctness + completeness: seed pinned, atlas versioned, ordering declared) manually to the input. See `review.json` and `_capture_notes.md` for the verbatim response.

**Diagnoses recorded (see `critique.md`).** Granularity / aggregation masking; missing preprocessing provenance; uncontrolled confounders (age, sex, motion, medication); weak labels / restricted STAI-T range in a healthy cohort.

---

## exploratory: high-anxiety subgroup follow-up (NOT confirmatory)

**Status.** Hypothesis-generating only. Selected post-hoc after observing the cohort null. Not preregistered.

**Exploratory hypothesis.** Within participants with STAI-T >= 45, trait anxiety predicts right-amygdala -> mPFC resting-state FC.

**Plan.** One step, `seed_based_fc` on the high-STAI-T subset (seed = right_amygdala, target = mPFC, atlas = Harvard-Oxford v0.4.0). Full plan in `exploratory_plan.json`.

**Plan validation (`mcp__brain-researcher-local__pipeline_plan_validate`).**
- v1 of the plan was rejected: `ok=false`, four issues — `Unknown tool: behavior_filter`, `Missing required params for seed_based_fc: ['img']`, `Unknown tool: pearson_correlation`, `Unknown tool: report_tagger`.
- v2 (final) validated: `ok=true`, `issues=[]`, `code_review.decision=approve`, `risk_level=low`, `run_id_hint=br_20260528_182842_87d13f69dd`.
- Full validator response in `validate.json`.

**Execution.** Not executed in this demo capture. The kit ships no fMRI fixtures for this demo, and per task constraints we do not fabricate subgroup r/p. See `followup_findings.json`.

**Why this stays in the exploratory section.**
- post-hoc subgroup selection,
- no preregistration,
- subgroup N strictly less than the cohort N=80, so statistical power is reduced,
- a non-null subgroup result would still require an independent confirmatory cohort before being promoted out of this section.

**If executed and significant.** Report as: "exploratory: in the STAI-T >= 45 subgroup (n=..., r=..., p=...), a positive association between trait anxiety and right amygdala -> mPFC resting-state FC was observed; this is hypothesis-generating and requires independent replication before confirmatory status."

---

## summary table

| Section        | Claim                                                                                  | Status         |
|----------------|----------------------------------------------------------------------------------------|----------------|
| confirmatory:  | Whole-cohort r=0.05, p=0.66, CI [-0.17, 0.27], N=80 — null at the cohort level.       | retained       |
| confirmatory:  | "Hypothesis not supported in general."                                                 | NOT made       |
| exploratory:   | High-STAI-T subgroup may show amygdala-mPFC coupling.                                  | hypothesis only |

## artifacts

- `review.json` — `run_scientific_review` invocation and verbatim response.
- `critique.md` — null-result diagnoses + the single exploratory follow-up proposal.
- `exploratory_plan.json` — the subgroup plan submitted to the validator.
- `validate.json` — `pipeline_plan_validate` response (v1 rejected, v2 approved).
- `followup_findings.json` — execution status (not executed; would have been exploratory).
- `_capture_notes.md` — per-tool capture log including the `run_scientific_review` error.
