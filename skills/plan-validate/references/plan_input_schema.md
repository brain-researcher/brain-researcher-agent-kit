# Plan input schema

The validator accepts the **same dict** the `pipeline_plan_validate(plan=...)`
MCP tool accepts. A top-level `{"plan": {...}}` wrapper is also unwrapped
automatically.

```jsonc
{
  "steps": [                      // REQUIRED, non-empty list
    {
      "tool": "glm_first_level",  // REQUIRED non-empty string.
                                  //   aliases accepted: "tool_id", "name"
      "params": {                 // optional object (default {}).
                                  //   alias accepted: "parameters"
        "tr": 2.0,
        "high_pass": 0.01,
        "n_events_per_condition": 20,
        "modality": "bold",       // drives modality/space compatibility rules
        "target_space": "MNI152NLin2009cAsym"
      },
      "step_id": "glm"            // optional; must be unique across steps.
                                  //   aliases accepted: "id", "name"
    }
  ],
  "project_root": "/data/study",  // optional string (informational offline)
  "run_tag": "clean-fmri-glm"     // optional string (informational offline)
}
```

## Hard schema failures (return `ok:false`, `schema_error`)

Ported from `server._coerce_plan`:

- `steps` missing, not a list, or empty.
- a step that is not an object.
- a step with no non-empty `tool` (or `tool_id` / `name`).
- a step whose `params` (or `parameters`) is present but not an object.
- a duplicate `step_id` across steps.
- `project_root` / `run_tag` present but not a non-empty string.

## Parameter keys the rules read

The rules only inspect a small set of well-known param keys. Put the values
where the rules look, or they will not fire:

| key(s) | used by |
| --- | --- |
| `tr` | `REVIEW_TR_LOW`, `REVIEW_TR_HIGH`, checklist |
| `fwhm` | `REVIEW_FWHM_OOB`, `REVIEW_FWHM_LOW`, checklist |
| `n_events_per_condition` | `REVIEW_GLM_N_EVENTS_TOO_FEW` |
| `high_pass` | `REVIEW_HIGH_PASS_TOO_AGGRESSIVE` |
| `n_subjects` | `REVIEW_GROUP_N_TOO_SMALL`, `REVIEW_PARAMETRIC_SMALL_N` |
| `b_value`, `n_directions` | DWI rules |
| `modality`, `modalities` (str or list) | modality-mismatch, DWI-on-BOLD |
| `space`, `spaces`, `target_space`, `atlas_space`, `output_space` | MNI/space rules |
| boolean design flags (`within_subject`, `between_subjects`, `factorial`, `mixed_design`, `longitudinal`, `correlation`, `one_sample`, …) | design inference for `REVIEW_METHOD_APPROPRIATENESS` |
| `design_type` / `design` (string) | design inference |
| `statistical_method` / `test_type` / `method` (string) | method inference |
| `task` / `paradigm`, `contrast*`, `study_id` / `dataset*` | reported in `detected_context` (also feed method-inference free-text) |

The design/method can also be expressed via the **tool name** (e.g. a step whose
tool is `scipy_ttest_ind` infers method `independent_t_test`).
