# Skill licenses

Per-skill license stance. The kit ships under MIT (see `LICENSE`); some skills bundle third-party content with different terms.

## First-party skills (MIT, same as the kit)

| Skill | License | Provenance |
|---|---|---|
| `brain-researcher-session-handoff/` | MIT | Authored for this kit. |
| `banghcp-gcp-batch-orchestration/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `br-vs-host-benchmark/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `brain-researcher-docs-public-prune/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `brain-researcher-git-worktree-hygiene/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `brain-researcher-mcp-contract-workflow/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `brain-researcher-mechanism-proof-review/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `brain-researcher-scientific-review-gate/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `codex-review-operator/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `god-file-carve/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `method-condition-coverage/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `neuroprogram-real-fmri/` | MIT | Authored for this kit; path-parameterized OpenNeuro/fMRIPrep workflow wrapper. |
| `prod-mcp-health-sweep/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `repo-github-workflow/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `worktree-pr-cycle/` | MIT | First-party BR operational skill, ported from the private BR repo with public-safe paths. |
| `scientific-self-critique/` *(planned)* | MIT | Authored for this kit; thin wrapper over BR review tools. |
| `plan-validation/` *(planned)* | MIT | Authored; wraps `pipeline_plan_validate` / `pipeline_plan_review`. |
| `evidence-grounding/` *(planned)* | MIT | Authored; wraps `grounding_resolve` / `grounding_gate_evidence_basis`. |
| `confirmatory-vs-exploratory-labeling/` *(planned)* | MIT | Authored; wraps `run_scorecard` / `verdict_builder` output. |
| `final-report-gate/` *(planned)* | MIT | Authored; wraps `scientific_report_generate` with precondition checks. |

## Third-party content

None bundled in v0.1.0.

The internal repo's `skills/third_party/AI-Research-SKILLs/` bundle (90+ ML skills) is **explicitly excluded** from this kit per the OSS launch plan decision (2026-05-26). If you want those skills, install them upstream and add them to your own kit. We may add a `docs/related-skills.md` pointer post-launch.

## Adding a new skill

When proposing a new skill to this kit:

1. Default to MIT, matching the kit's `LICENSE`.
2. If the skill bundles third-party prompts, datasets, or templates with non-MIT terms, declare them in this file and include the upstream LICENSE file under `skills/<your-skill>/LICENSES/`.
3. If the skill ships scientist-attribution data (expert registries, named recommenders), get explicit consent or replace names with generic IDs (`expert_a`, etc.). See `REDACTION_POLICY.md`.
