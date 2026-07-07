# Failure-class triage table

Map the observed failure to the signal that confirms it and the right next move. The
cause you report must trace to one of these signals in the run's own evidence.

| Failure class | Confirming signal (where) | Typical remedy | Lean on |
|---|---|---|---|
| **policy / sandbox** | `violations[]` with `output_dir_not_allowed` / `path_outside_allowed_roots` in the bundle; `policy_issues` on the step | fix the allowed roots / output_dir; not a code bug | `run_bundle_get` → `generate_repo_repair_context` |
| **execution error** | step `error` + traceback in `run_logs` | fix the code/params the traceback names | `run_logs` → `generate_bug_digest` |
| **data / input** | missing-input / file-not-found in logs; dataset readiness gap | resolve the dataset resource (see `dataset-discovery-and-readiness`) | `run_logs`, `run_get` |
| **timeout / stall** | `run_metrics` shows silence past `stall_timeout` / `soft_timeout`; status stuck `running`/`queued` | raise budget or shrink the work; check the executor | `run_metrics`, `run_get` |
| **AI-response / wrapper** | a top-level `PROCESSING_ERROR` whose *step* error in the bundle is something else | trust the step error; the wrapper masked it | `run_bundle_get` (compare wrapper vs step error) |

## Rules

- The **step error in the bundle** beats the **top-level wrapper message** whenever
  they disagree. Report the step-level cause.
- `stalled` (still running, silent) ≠ `failed` (finished with error) ≠ `degraded`
  (completed with warnings). Confirm which from `run_get` status before triaging.
- A `generate_repo_repair_context` suggestion is a repair *hypothesis*. Verify with a
  re-run; do not mark the run fixed from the digest alone.
