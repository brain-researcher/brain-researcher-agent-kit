---
name: neuroprogram-real-fmri
description: Run NeuroProgram against real task-fMRI. Compile a hypothesis into a constrained NeuroProgram report, stage public OpenNeuro fMRIPrep derivatives, run a genuinely different fitlins multiverse, reduce z-maps to a robustness profile, and bind that profile into a bounded ClaimCardV1.
---

# NeuroProgram Real fMRI

Use this skill when validating the hypothesis-to-claim loop on real OpenNeuro
task-fMRI, especially the empirical half of a `neuroprogram_compile` plan.

The intended path is:

1. Compile the declarative program with `neuroprogram_compile` or the local
   `compile_program` helper and keep the `commitment_hash`.
2. Stage real BIDS + fMRIPrep inputs with
   `scripts/fetch_openneuro_derivatives.sh`.
3. Generate genuinely different fitlins model variants with
   `scripts/make_multiverse_variants.py`.
4. Run each variant with `scripts/run_fitlins_variants.sh`.
5. Reduce contrast maps and bind robustness to a claim card with
   `scripts/bind_robustness_to_claim.py`.

## Environment Contract

Run from the Brain Researcher repo root unless `BR_NEUROPROGRAM_STAGE` is set.

Required:

- `conda activate brain_researcher`
- `PYTHONPATH=<repo>/src` or an editable package install
- `fitlins`, `nilearn`, `nibabel`, `pandas`, `numpy`
- `git-annex` plus a local OpenNeuro derivatives checkout
- explicit `DERIV_REPO` and `RAW_DIR` environment variables for Stage 1
- a cached atlas path supplied via `--atlas` for Stage 4

Default generated outputs stay under `.br_runs/neuroprogram_fitlins/` in the
current repo checkout. Override with `BR_NEUROPROGRAM_STAGE` or `STAGE` when
using another scratch location.

## Stage 0: Compile

Use the MCP tool `neuroprogram_compile` or the package function directly. This
stage produces a `NeuroProgramReportV1` with a pre-observation commitment hash
and a program ceiling. Do not treat `plan_preflight`, `plan_create`, or
`neuroprogram_compile` alone as having executed the analysis.

## Stage 1: Fetch Public Derivatives

```bash
DERIV_REPO=/path/to/ds000114-fmriprep \
RAW_DIR=/path/to/ds000114 \
TASK=fingerfootlips \
SUBJECTS="01 02 03" \
bash skills/neuroprogram-real-fmri/scripts/fetch_openneuro_derivatives.sh
```

This stages a pruned BIDS tree and matching fMRIPrep derivatives for only the
requested task and subjects, so fitlins does not traverse unrelated annex
symlinks.

## Stage 2: Generate Variants

```bash
python skills/neuroprogram-real-fmri/scripts/make_multiverse_variants.py \
  base_model.json .br_runs/neuroprogram_fitlins/models \
  --subjects 01 02 03 --task fingerfootlips --session test
```

The variants intentionally differ in HRF and motion-confound choices. Do not
reuse identical model JSON as a multiverse.

## Stage 3: Run fitlins

```bash
STAGE=.br_runs/neuroprogram_fitlins \
bash skills/neuroprogram-real-fmri/scripts/run_fitlins_variants.sh
```

Use `--estimator nilearn` first because it is the smallest local dependency
surface. Other estimators may require site-specific neuroimaging modules.

## Stage 4: Bind Robustness

```bash
PYTHONPATH=src python skills/neuroprogram-real-fmri/scripts/bind_robustness_to_claim.py \
  --stage .br_runs/neuroprogram_fitlins \
  --contrast fingervfoot \
  --atlas /path/to/cached_atlas_in_mni.nii.gz \
  --run-id mv:ds000114:fingerfootlips:realrun \
  --program-report .br_runs/neuroprogram_fitlins/neuroprogram_report.json
```

The claim must carry the same contrast in `claim.extra["contrast"]`. A contrast
mismatch is a fail-closed `unbound` result, not borrowed robustness evidence.

## Invariants

- Record the Stage 0 `commitment_hash` before observing fitlins outputs.
- A multiverse of identical specs is invalid evidence.
- `n_valid < 5` variants caps the claim as underpowered.
- Low or missing effect-size stability caps the claim as unstable.
- Objective-safety stays at compile time: optimize validity, robustness, or
  coverage, never significance or effect magnitude.
- Report the final output as `implemented`, `partial`, or `spec-only` based on
  the actual run artifacts present.
