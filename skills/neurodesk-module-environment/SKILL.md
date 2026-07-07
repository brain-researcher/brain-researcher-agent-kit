---
name: neurodesk-module-environment
description: Run neuroimaging tools through a Neurodesk-style module environment correctly — load via `module`, pin versions, purge between unrelated steps, and report environment failures honestly instead of falling back to ad-hoc installs. Use when an agent will invoke fsl/fmriprep/afni/freesurfer/etc. through a module + CVMFS/Apptainer environment.
---

# Neurodesk Module Environment

## Overview

Neuroimaging tools in a Neurodesk-style environment are loaded through `module`
(local preinstalls layered on a CVMFS mount), not from a bare PATH. This skill is the
discipline for picking the right load command and — crucially — **reporting an
environment failure honestly** rather than silently falling back to `apt install` or
a guessed binary. It wraps the kit's Neurodesk adapter, mirroring the
`sherlock-oak-workflow` pattern (an environment discipline, not an MCP call).

Use it when the agent will run fsl / fmriprep / afni / freesurfer / ants / mrtrix3 /
spm / matlab through a module + CVMFS/Apptainer environment. Do **not** use it for
SLURM/Sherlock cluster patterns (`sherlock-oak-workflow`) or GPU requests
(`gcp-gpu-request`).

## Workflow

1. **Discover before loading.** `module avail <name>` to list pinned versions;
   `module whatis <name>/<version>` for a one-liner. Do not guess a version string
   (`fsl/6.0.3`, never `fsl/latest`).
2. **Resolve the load string** from
   [`adapters/neurodesk-modules.json`](../../adapters/neurodesk-modules.json) —
   the canonical tool-name → `module load` string + tier (local / cvmfs /
   container-only) map. Do not hardcode versions in prompts.
3. **Load and isolate.** `module load <tool>/<version>`; `module purge` between
   unrelated steps (mixing FSL + AFNI + SPM produces `LD_LIBRARY_PATH` surprises).
4. **Trust the pre-wired binds/licenses.** `APPTAINER_BINDPATH`, `FS_LICENSE`,
   `TEMPLATEFLOW_HOME` are exported by the setup script; do not redefine them unless a
   tool error explicitly names one. The project root is bound at the same absolute
   path inside containers — no path rewriting.
5. **Expect a slow first CVMFS load.** A first invocation that pauses tens of seconds
   is caching, not a hang — do not retry-loop.

See [`adapters/neurodesk.md`](../../adapters/neurodesk.md) for the full 8-point quick
reference this skill operationalizes.

## Anti-patterns

- **Do not** assume a binary is on PATH — `module load` first, or check `module list`.
- **Do not** fall back to `apt install` / pip / a guessed binary when `module` fails;
  report the environment failure (see the failure modes below).
- **Do not** hardcode `fsl/latest` or an unpinned version — versions are pinned.
- **Do not** redefine `APPTAINER_BINDPATH` / `FS_LICENSE` / `TEMPLATEFLOW_HOME`
  unless a tool error names one; a "different values for bind path" warning means
  revert to the setup-script defaults.
- **Do not** retry-loop a slow first CVMFS load or report it as a failure.

Report these explicitly, do not paper over: `module: command not found` (env not
sourced), `module load` succeeds but binary absent (likely CVMFS mount — report
`ls /cvmfs/neurodesk.ardc.edu.au`), quota errors on first CVMFS load (`$SCRATCH`
cache unset).

## Resources

- `adapters/neurodesk.md` + `adapters/neurodesk-modules.json` (repo root) — the
  quick reference and the tool-name → load-string/tier table this skill uses.

## Example user requests

- "Run fmriprep on this BIDS dataset in the module environment."
- "What's the right `module load` for FSL 6.0.3 here?"
- "afni isn't on PATH after I loaded it — what's wrong?"
- "Set up the environment to run freesurfer + ants without conflicts."
