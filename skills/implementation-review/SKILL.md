---
name: implementation-review
description: Run Brain Researcher's deterministic implementation-review rubrics on caller-supplied neuroimaging pipeline code or config — QSM (quantitative susceptibility mapping) reconstruction code, and rapidtide (systemic low-frequency-oscillation lag-mapping) method contracts. Use when someone hands over a QSM code snippet or a rapidtide method configuration and needs a static, rule-based audit that flags known-invalid dataflow or method choices (direct total-field dipole inversion, missing background-field removal, static zero-lag regression, clipped lag-search windows, filter bands outside the sLFO band) and returns a structured findings verdict. It is a non-displacive checker: it certifies that no known-bad pattern fired; it does not write or replace a reconstruction recipe.
---

# Implementation Review

## Overview

Two neuroimaging methods have a small set of choices that quietly invalidate the
result even when the code runs and the output looks plausible. This skill wraps
the two deterministic Brain Researcher rubrics that catch them:

- **QSM** (`review_qsm`) — static analysis of a **code string**. QSM is a dipole
  deconvolution whose forward model relates susceptibility to the *local* field.
  Inverting the *total* field (which still holds the background field from
  air/bone/sinuses) solves the wrong equation. The rubric flags direct
  total/raw/phase-field inversion, a missing background-removal stage, ambiguous
  dataflow into the inversion, and TKD without contrast QC.

- **rapidtide** (`review_rapidtide`) — a rule check of a declared
  **`method_contract`** (plus optional numeric `subject_summaries`). rapidtide
  maps sLFO blood-arrival delays by cross-correlating each voxel against an
  iteratively refined probe regressor over a lag-search window. The rubric flags
  a static zero-lag regression, a missing or too-narrow lag window, skipped probe
  refinement, a naive global-mean regressor, a filter band outside the sLFO band,
  insufficient oversampling at long TR, disabled despeckling, and — from observed
  outputs — peak lags railing at the search boundary.

Both are **deterministic and dependency-free** (Python stdlib only), and both are
**non-displacive**: they return hard constraints, findings, and QC checks, never
a replacement pipeline. A clean `approve` means only that none of the specific
known-bad patterns fired — not that the whole pipeline is endorsed.

This skill is fully self-contained. It reproduces the MCP tools
`qsm_implementation_review` and `rapidtide_implementation_review` bit-for-bit
(see `scripts/implementation_review.py --selftest`); no server, KG, or network
is required. Those MCP tools remain the hosted equivalents if a caller prefers
the certified server path, but nothing here depends on them.

## Workflow

### 1. Route by input type

- Caller supplies **QSM reconstruction code** (mentions dipole inversion,
  susceptibility, RESHARP/V-SHARP/LBV, chi map, multi-echo GRE) → **QSM path**.
- Caller supplies a **rapidtide / sLFO lag configuration** (cross-correlation
  lag search, lag range, probe regressor refinement, sLFO band) → **rapidtide
  path**.

If unsure which method it is, ask; do not run the wrong rubric.

### 2. Build the input JSON

Write a single JSON file the script reads. The `method` field selects the rubric.

QSM:

```json
{ "method": "qsm", "code": "<the pipeline code, verbatim>", "filename": "recon.py" }
```

rapidtide:

```json
{
  "method": "rapidtide",
  "task_profile": "sLFO_delay_mapping",
  "method_contract": {
    "cross_correlation_lag_search": true,
    "lag_search_range_s": [-10, 10],
    "refinement_passes": 3,
    "regressor_source": "refined_sLFO",
    "temporal_filter_band_hz": [0.009, 0.15],
    "oversample_factor": 4,
    "tr_s": 2.0,
    "lag_map_despeckle": true
  },
  "subject_summaries": [ { "subject": "sub-01", "lag_boundary_fraction": 0.02 } ]
}
```

For rapidtide, only fill keys you can actually attest from the pipeline. Every
`method_contract` key is optional and a missing key skips its check — **except
`lag_search_range_s`, whose absence blocks** (an undeclared lag window cannot be
verified). Do not invent values to silence a check; an honest omission is a
finding, a fabricated value is worse. `subject_summaries` is for *observed*
outputs (e.g. the measured fraction of voxels whose peak lag sits at the search
boundary) and confirms clipping beyond what the contract declares.

### 3. Run the rubric

```bash
python skills/implementation-review/scripts/implementation_review.py <input.json>
```

The script prints one JSON verdict. To regression-guard the ported rules against
accidental edits to this script (a self-consistency check — it does not import
`brain_researcher` and cannot detect upstream drift):

```bash
python skills/implementation-review/scripts/implementation_review.py --selftest
```

### 4. Interpret and report the verdict

Read the verdict per `references/output_contract.md`:

- `block` — a hard, invalidating error (any `critical` severity or `block`
  action). Report the `rule_id`, `message`, and `suggested_fix`; the pipeline
  must be fixed before its output is trusted.
- `revise` — an `error`-severity finding; correct before trusting the result.
- `approve_with_warnings` — only `warn`-severity findings; surface them.
- `approve` — no findings fired.

Report each finding by its `rule_id` and the concrete `suggested_fix`. For QSM,
also relay the `domain_invariant_review` block (hard constraints + QC protocol).

### 5. Stay within the rubric (non-displacement)

Do not turn these findings into a full method prescription. The QSM rubric
explicitly forbids substituting generic fMRI preprocessing (fMRIPrep, FEAT,
fieldmap-distortion) for QSM, mandating full-resolution iterative TV/ADMM, or
recommending TKD-only without contrast QC. Recommend only the minimal canonical
fix for each finding, and make clear that `approve` audits the listed patterns,
not the entire scientific design.

## Files

### references/
- `qsm_review_rules.yaml` — the QSM rule catalog: detection primitives, the four
  rules with rationale + fix, roll-up policy, hard constraints, QC protocol, and
  the domain-invariant notice. Human-readable mirror of the script.
- `rapidtide_review_rules.yaml` — the rapidtide rule catalog: thresholds, the
  nine rules with rationale + fix, roll-up policy, and validation.
- `output_contract.md` — the `CodeReviewVerdict` / `ReviewFinding` output schema
  and what each decision means.

### scripts/
- `implementation_review.py` — the deterministic rule engine. Routes QSM vs
  rapidtide by the `method` field, ports both BR kernels verbatim (constants and
  regexes copied from the source), and prints the JSON verdict. `--selftest`
  re-runs the BR unit fixtures to guard against drift. Stdlib only; no
  `import brain_researcher`.

## When the server is genuinely needed

Never, for this skill. These two rubrics are pure static/rule checks over
caller-supplied inputs (that is exactly why they were carved out as
`skill_candidate`). If a task additionally needs a KG evidence read, a
tamper-evident commitment, or a run-bundle/digest fetch, those stay on the MCP —
call the relevant `mcp__brain-researcher__*` tool for that step; do not
reimplement it here.
