# brain-researcher-agent-kit

Open-source agent layer for Brain Researcher: skills, AGENTS templates, MCP adapters, sanitized demos, and eval rubrics. Sits on top of the [`brain-researcher-public`](https://github.com/brain-researcher/brain-researcher-public) core MCP server.

**Status: v0.1.0 released.**

## Use It Directly

Most users do not need to install this repo. The fastest path is to use the
agent instruction file directly.

1. Set up Brain Researcher MCP if your agent client is not connected yet.

   Use [`MCP_SETUP.md`](MCP_SETUP.md) for Cursor, Claude Code, Codex CLI, and
   generic MCP JSON setup. The hosted endpoint is
   `https://brain-researcher.com/mcp`.

2. Give your agent the Brain Researcher instructions.

   Use [`agents/AGENTS.brain-researcher.md`](agents/AGENTS.brain-researcher.md)
   as your project `AGENTS.md`, `CLAUDE.md`, Cursor project rule, or equivalent
   system-instruction file.

3. Ask the agent plainly:

   ```text
   Read agents/AGENTS.brain-researcher.md, check Brain Researcher MCP with
   server_info and system_self_test, then help me plan this analysis.
   ```

   Or, if you only need setup help:

   ```text
   Read MCP_SETUP.md and tell me the exact Brain Researcher MCP setup for
   Cursor / Claude Code / Codex CLI.
   ```

Other useful instruction files:

- General research work: [`agents/AGENTS.research.md`](agents/AGENTS.research.md)
- PR/code-review work: [`agents/AGENTS.code-review.md`](agents/AGENTS.code-review.md)

## Clone For Examples Or PRs

Clone the repo only if you want the captured demos, eval runner, or contribution
checks:

```bash
git clone https://github.com/brain-researcher/brain-researcher-agent-kit.git
cd brain-researcher-agent-kit
python -m pip install -e ".[runner]"
```

Smoke-test the captured demos:

```bash
python -m evals.runner --all
```

Run the public-surface checks before opening a PR:

```bash
python scripts/redaction_guard.py
git diff --check
```

Try one example:

```bash
bash examples/plan-validate-and-execute/run.sh
```

## Report Or Contribute

- Unreasonable KG node, edge, retrieval result, evidence link, or generated
  claim: open **KG / result correction**.
- Existing skill or workflow bundle that should be consolidated here: open
  **Skill consolidation**.
- Agent picked the wrong tool, hallucinated args, skipped self-critique, or
  over-claimed execution: open **BR agent behavior bug**.
- Demo, rubric, adapter, or docs bug: open **Kit bug**.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full routing table.

## Scope

- `skills/` — portable SKILL.md bundles an agent can invoke. v0.1.0 ships: `brain-researcher-session-handoff` (BR-aware session start + snapshot discipline), `neuro-big-picture` (idea framing against grand challenges and recent discourse), `journal-writing-guidelines` (neuroimaging manuscript playbook), `sherlock-oak-workflow` (Stanford Sherlock + OAK + SLURM patterns; PI-group placeholders), and `gcp-gpu-request` (GPU sizing + guarded gcloud request). Ported deterministic kernels of the BR review/compile layer (offline, stdlib-only, reviewer-auditable): `neuroprogram-design-compile` (objective-safety gate — magnitude objectives rejected — + magnitude-free design-family enumeration), `implementation-review` (QSM / rapidtide pipeline rule checks), `plan-validate` (offline analysis-plan feasibility rules), and `session-heuristics` (risk classification + lesson extraction over a session digest). Closed-loop routing wrappers (markdown discipline over a BR MCP sequence, the daily-usage flows named in `agents/AGENTS.brain-researcher.md`): `evidence-grounding` (resolve → gate → reject/downgrade), `plan-validation` (preflight → validate → review → recipe, never "executed"), `scientific-self-critique` (weak/null-result checkpoint + exploratory follow-up), `final-report-gate` (block a polished report over a weak evidence basis), `cross-tool-provenance-handoff` (carry run_id + checksum + profile across tools), `mcp-contract-drift-debugging` (confirm the live surface before calling from memory), and `demo-fixture-capture-redaction` (capture → redact → guard before committing a fixture). Daily research-workflow wrappers (motivated by the paper's cases): `kg-hypothesis-discovery-and-verification` (sample → verify; a candidate is a question, not a finding), `method-condition-lookup` (coverage guard + report each field with its grounding tier), `sealed-commitment-preregistration` (commit-before-observe seal-and-stop; never backfill), `posthoc-claim-audit-packet` (honest audit for an already-run analysis; `commitment_card_ref: null`), `neuroclaim-calibration` (report the weakest binding axis + forbidden-language boundary), `survival-gated-claim-adjudication` (falsifier gate before a magnitude winner or gated dispatch), `dataset-discovery-and-readiness` (mention is not readiness), `session-lessons-to-memory-promotion` (no promotion without a verdict), and `method-implementation-review` (QSM/rapidtide critics as blockers). Diagnostics + exploration wrappers: `run-failure-triage` (diagnose a failed run from its artifacts → bug digest + repair context, cause traced to evidence), `kg-structural-probe` (probe the KG for leverage / contradiction / refuted directions — leads, not verdicts), `external-scientific-review-handoff` (BR issues criteria, an external agent inspects, only an inspection-backed verdict is submitted), `neurodesk-module-environment` (module-load discipline + honest env-failure reporting), and `research-trajectory-synthesis` (cross-run trajectory grounded in run bundles, not a narrative gloss).
- `skills/neuroprogram-real-fmri/` — path-parameterized real fMRI wrapper for the NeuroProgram empirical half: compile a bounded program, stage public OpenNeuro derivatives with explicit `DERIV_REPO` / `RAW_DIR`, generate fitlins multiverse variants, and bind robustness into a bounded claim card.
- BR repo operational skills ported from the private repo and Claude project skills after public-safety review: `banghcp-gcp-batch-orchestration`, `br-rollout`, `br-vs-host-benchmark`, `brain-researcher-docs-public-prune`, `brain-researcher-git-worktree-hygiene`, `brain-researcher-mcp-contract-workflow`, `brain-researcher-mechanism-proof-review`, `brain-researcher-scientific-review-gate`, `codex-review-operator`, `god-file-carve`, `method-condition-coverage`, `prod-mcp-health-sweep`, `repo-github-workflow`, `tb-science-task-authoring`, and `worktree-pr-cycle`.
- `agents/` — `AGENTS.brain-researcher.md`, `AGENTS.research.md`, `AGENTS.code-review.md` — reusable agent-policy templates.
- `adapters/` — flat adapters: `br-adapter-map.json` + `br-fallback-policy.md` for Brain Researcher MCP routing, and `neurodesk.md` + `neurodesk-modules.json` for the Neurodesk module environment.
- `examples/` — sanitized end-to-end demos with `input/`, `expected_output/`, `rubric.yaml`, `run.sh`.
- `evals/` — AutoResearch-dimension rubrics + a small runner that scores demo outputs.

## MCP Setup Details

If your agent cannot call `server_info` or `system_self_test`, connect the MCP
client with [`MCP_SETUP.md`](MCP_SETUP.md) or the canonical setup page:
<https://brain-researcher.com/mcp/setup>.

## Companion repo

- `brain-researcher-public` ships the MCP server, the contract layer (`contracts/tools/*.json` + `contracts/VERSION`), shared utilities (`br.retry`, `br.provenance`, `br.artifact`, `br.http`, `br.redaction`), and architecture docs. This kit's `pyproject.toml` declares the version dependency.

## Contributing

Found a bug, a stale tool reference, a confusing example, or a missing skill? See [`CONTRIBUTING.md`](CONTRIBUTING.md) for where to file it. Security/data-leak issues go through [`SECURITY.md`](SECURITY.md), not public issues.

## License

MIT — see [LICENSE](LICENSE).
