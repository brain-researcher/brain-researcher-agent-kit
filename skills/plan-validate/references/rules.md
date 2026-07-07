# Plan-validation rule catalog (offline, `use_kg=False`)

This is the human-readable audit view of the rules the validator enforces. The
machine-readable source of truth the script actually loads is
`plan_review_rules.json` (rule metadata + tool sets) and
`method_compatibility_seed.json` (design/method compatibility). Both were ported
**verbatim** from Brain Researcher:

| Skill file | Source in `brain_researcher/` |
| --- | --- |
| `plan_review_rules.json` | `configs/review_rules.yaml` (the `review_mode: plan` subset) |
| structural check logic in `validate_plan.py` | `services/review/checks/tool_order.py`, `checks/space_compat.py` |
| `method_compatibility_seed.json` | `configs/br-kg/method_compatibility_seed.yaml` |
| roll-up + checklist | `services/review/verdict_builder.py` |
| bundle extraction | `services/review/bundle_builder.py::build_plan_review_bundle` |

The offline validator reproduces the `code_review` verdict that
`pipeline_plan_validate(plan)` returns (rule engine run with `use_kg=False`) —
verified finding-for-finding against the live engine.

## How a verdict is rolled up

Each fired rule is a *finding* with a `severity` (`warn` / `error` / `critical`)
and an `action` (`warn` / `block`). The verdict is the single worst outcome
(from `verdict_builder._roll_up_decision`):

| Condition (checked top → bottom) | decision | risk_level |
| --- | --- | --- |
| any finding `action == block` **or** any `severity == critical` | `block` | `critical` |
| any `severity == error` | `revise` | `high` |
| any `severity == warn` | `approve_with_warnings` | `medium` |
| no findings | `approve` | `low` |

`ok` is `true` when there are **no** error/critical findings and **no** block
actions (warnings still pass). A hard schema failure returns `ok:false` with a
`schema_error` and no findings (mirrors `pipeline_plan_validate` returning
`{"ok": false, "error": ...}` from `_coerce_plan`).

Note: every `error`-severity plan rule below also carries `action: block`, so in
practice a plan error resolves to `block/critical`, not `revise/high`. The
`revise` tier exists in the roll-up for parity with artifact-mode review.

## Metric rules (per-step parameter ranges)

Evaluated against each step's `params`. Rules with a **tool filter** only apply
to steps whose `tool` (lowercased) is in the filter set; unfiltered rules apply
to every step. A missing parameter is skipped (never fires).

| rule_id | trigger | severity / action | tool filter |
| --- | --- | --- | --- |
| `REVIEW_TR_LOW` | `params.tr < 0.3` | warn / warn | (any step) |
| `REVIEW_TR_HIGH` | `params.tr > 5.0` | warn / warn | (any step) |
| `REVIEW_FWHM_OOB` | `params.fwhm > 12.0` | warn / warn | smooth, fslmaths, nilearn_smooth_img, susan |
| `REVIEW_FWHM_LOW` | `params.fwhm < 2.0` | **error / block** | smooth, fslmaths, nilearn_smooth_img, susan |
| `REVIEW_GLM_N_EVENTS_TOO_FEW` | `params.n_events_per_condition < 8` | warn / warn | glm_first_level, nilearn_first_level_model, fsl_feat, fsl_film_gls, spm_glm, fitlins |
| `REVIEW_HIGH_PASS_TOO_AGGRESSIVE` | `params.high_pass > 0.02` | warn / warn | glm_first_level, nilearn_first_level_model, fsl_feat, fsl_film_gls, nilearn_clean_img |
| `REVIEW_GROUP_N_TOO_SMALL` | `params.n_subjects < 10` | warn / warn | glm_second_level, nilearn_second_level_model, fsl_randomise, spm_factorial_design, flame |
| `REVIEW_DWI_BVALUE_LOW` | `params.b_value < 700` | warn / warn | mrtrix_tckgen, dsi_studio_tracking, fsl_dtifit, ants_dti, dipy_tracking, dmri_tractography |
| `REVIEW_DWI_BVALUE_HIGH` | `params.b_value > 5000` | warn / warn | mrtrix_tckgen, dsi_studio_tracking, fsl_dtifit, dipy_tracking, dmri_tractography |
| `REVIEW_DWI_N_DIRECTIONS_LOW` | `params.n_directions < 12` | **error / block** | mrtrix_tckgen, fsl_dtifit, dipy_tracking, ants_dti, dmri_tractography, dmri_parcellate_connectome |
| `REVIEW_PARAMETRIC_SMALL_N` | `params.n_subjects < 8` | warn / warn | scipy_ttest_ind, scipy_ttest_rel, pingouin_ttest, glm_second_level, nilearn_second_level_model |
| `REVIEW_NO_STEPS` | `plan.step_count < 1` | **error / block** | (plan-level) |

`REVIEW_HIGH_PASS_TOO_AGGRESSIVE` carries a `kg_lookup` (GLMDesignPrior). It is
**ignored offline** — only the KG-backed `pipeline_plan_review` consults it.
`REVIEW_NO_STEPS` is effectively unreachable through this validator because the
schema coercion rejects an empty `steps` list first (same as production).

## Structural rules (cross-step ordering / modality-space compatibility)

Evaluated by ported check functions over the whole step list.

| rule_id | fires when | severity / action |
| --- | --- | --- |
| `REVIEW_REGISTRATION_ORDER` | first atlas/parcellation step precedes first registration step | **error / block** |
| `REVIEW_SKULL_STRIP_ORDER` | first registration step precedes first skull-strip step | warn / warn |
| `REVIEW_MISSING_CONFOUND_REGRESSION` | a GLM step exists with no confound-regression step before it | warn / warn |
| `REVIEW_MODALITY_MISMATCH` | an EEG/MEG modality is declared with a volumetric MNI space/atlas | **error / block** |
| `REVIEW_DWI_TOOL_ON_BOLD` | a DWI-only tool is declared with a BOLD/fMRI modality | **error / block** |
| `REVIEW_MIXED_MNI_VERSIONS` | both `MNI152NLin2009cAsym` and `MNI152NLin6Asym` appear | **error / block** |
| `REVIEW_METHOD_APPROPRIATENESS` | inferred (design, method) pair is incompatible per the seed | **error / block** |

Tool membership sets for these checks are in `plan_review_rules.json → tool_sets`.
Modality is read from step `params.modality` / `params.modalities`; space from
`params.space` / `spaces` / `target_space` / `atlas_space` (plus `output_space`
for the mixed-MNI scan) — see `bundle_extraction` in the same file.

### Method appropriateness (offline seed path)

`REVIEW_METHOD_APPROPRIATENESS` infers the study **design** and the statistical
**method**, then looks the pair up in `method_compatibility_seed.json`:

- **Design** is inferred from (in order): a truthy boolean param
  (`within_subject`, `between_subjects`, `factorial`, …), an explicit
  `design_type` / `design` string, or free-text alias matching.
- **Method** is inferred from an explicit `statistical_method` / `test_type` /
  `method` string, the tool name, or free-text alias matching.
- The seed's `rules` list is scanned for a matching `(design, method)` with
  `compatible: false`. A match fires a finding whose `rule_id` is the **seed
  rule id** (e.g. `REPEATED_MEASURES_BLOCKS_INDEPENDENT_T_TEST`) and whose
  `message` is the seed rationale.

Fidelity detail: the live engine's rule-metadata merge forces this finding to
`severity=error` / `action=block` regardless of the seed row's own `severity`
(so a `warn`-severity factorial seed row still rolls up as block). The port
reproduces this; the seed's own severity is preserved in `seed_severity` on the
finding for transparency.

Only the curated seed is consulted offline. The live tool additionally queries
BR-KG graph edges first (`use_kg` path) — that requires the server (see SKILL.md).

## Case-sensitivity quirk (faithfully reproduced)

In `tool_order.py` the tool-name is lowercased before membership testing, but a
few set members are stored mixed-case (`antsRegistration` in
`registration_tools`, `antsBrainExtraction` in `skull_strip_tools`). Those exact
members therefore never match a lowercased tool and are effectively dead entries
in the source — the `ants_registration` / snake_case aliases are what actually
match. The port keeps the sets in source casing so its output matches production
byte-for-byte. `space_compat.dwi_tool_on_bold` and the EEG-modality set *do*
lowercase their sets, so those match case-insensitively; the port mirrors each
transformation exactly.

## What is NOT in scope offline

The full `pipeline_plan_validate` MCP tool also performs, server-side:
workspace-path resolution + sandbox enforcement, per-step **registry preflight**
(does the tool exist / is it allowed), and the `use_kg=True` **KG parameter
grounding** that can attach GLMDesignPrior evidence to parameter findings. Those
need the registry, the filesystem sandbox, and the live graph and are **not**
reimplemented here. This validator is advisory / feasibility-and-consistency
only; it does not certify that a plan is runnable.
