# Neurodesk environment — agent quick reference

Drop the relevant lines into your agent's `AGENTS.md` when the agent will run neuroimaging tools through a [Neurodesk](https://neurodesk.org)-style module environment (local preinstalls layered on top of a CVMFS mount).

This is **not** an install guide. It is the minimum an agent needs to know to pick the right command and report failures honestly.

## 8 things the agent should know

1. **Tools are loaded via `module`, not bare PATH.** Always `module load <tool>` (or check `module list`) before invoking `fsl`, `fmriprep`, `afni`, etc. Never assume a binary is on PATH because it "should be installed."
2. **Two tiers, one namespace.** A `module load fsl/6.0.3` may resolve to either a **local** preinstall (fast, common tools) or **CVMFS** (`/cvmfs/neurodesk.ardc.edu.au`, on-demand, first load can be slow). Local always wins on name collisions.
3. **Discover before loading.** Use `module avail <name>` to list versions; use `module whatis <name>/<version>` for a one-line description. Do not guess version strings — they are pinned (e.g. `fsl/6.0.3`, not `fsl/latest`).
4. **First CVMFS load may be slow, subsequent loads are cached.** If a CVMFS tool's first invocation appears to hang for tens of seconds, that is expected — do not retry-loop or report it as a failure.
5. **`module purge` between unrelated steps.** Mixing FSL + AFNI + SPM in one shell can produce surprising `LD_LIBRARY_PATH` interactions. When in doubt, `module purge && module load <only what's needed>`.
6. **Bind paths and licenses are pre-wired.** The setup script exports `APPTAINER_BINDPATH`, `FS_LICENSE`, `TEMPLATEFLOW_HOME`, etc. Do not redefine these inside the agent unless a tool error explicitly names one as wrong.
7. **Working directory is bound at the same path inside containers.** Anything under the project root is visible at the same absolute path inside Apptainer/Singularity containers. So `fmriprep /data/bids /data/out` works from the host CWD; no need to rewrite paths.
8. **Failure modes to report explicitly, not paper over:**
   - `module: command not found` → environment not sourced; do not fall back to `apt install`.
   - `module load` succeeds but binary not on PATH → likely a CVMFS mount issue; report `ls /cvmfs/neurodesk.ardc.edu.au` state.
   - "different values for bind path" warning → bind paths were redefined; revert to the setup-script defaults.
   - Quota errors during first CVMFS load → `$SCRATCH` cache not set; surface to the user instead of silently retrying.

## Tool-name routing

See [`neurodesk-modules.json`](./neurodesk-modules.json) for the canonical tool-name → `module load` string + tier (local / cvmfs / container-only) mapping. Use that table to construct load commands; do not hardcode version strings in agent prompts.

## When this snippet does **not** apply

- Containerless pip/conda installs (vanilla Python env).
- Cloud-batch jobs where each container is built per-step (the orchestrator handles tooling).
- Pure dataset/metadata tasks that do not invoke a neuroimaging binary.
