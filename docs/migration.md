# Migration notes

Per-release migration guidance for consumers of this kit.

## v0.1.0 (2026-05-27, first OSS release)

Initial release. No prior contract to migrate from.

If you were copying skills out of the pre-OSS internal `brain_researcher/skills/` directory:

- `brain-researcher-session-handoff/` ships verbatim (sanitization audit found no private content).
- `banghcp-gcp-batch-orchestration/` is **not** included in v0.1.0; the skill is tightly bound to a lab-private GCP setup. We will revisit as a generic "constrained-cloud-batch" template post-launch.
- `gcp-gpu-request/`, `journal-writing-guidelines/`, `neuro-big-picture/`, `sherlock-oak-workflow/` are slated for sanitized inclusion in a follow-up release.
- `skills/third_party/AI-Research-SKILLs/` (90+ vendored ML skills) is excluded entirely.

If you were consuming `adapters/` from internal `scripts/neurometabench_v1/`:

- The `adapter-map.json` format is new — there was no published precedent. The internal `br_screening_adapter.py` was a per-benchmark adapter; this kit's adapter map is generic and intent-keyed.

Future entries land here whenever this kit's contract or layout changes.
