# brain-researcher-agent-kit

Open-source agent layer for Brain Researcher: skills, AGENTS templates, MCP adapters, sanitized demos, and eval rubrics. Sits on top of the [`brain-researcher-public`](https://github.com/brain-researcher/brain-researcher-public) core MCP server.

**Status: v0.1.0 released.**

## Quickstart

1. Clone the kit and install the lightweight eval dependency:

   ```bash
   git clone https://github.com/brain-researcher/brain-researcher-agent-kit.git
   cd brain-researcher-agent-kit
   python -m pip install -e ".[runner]"
   ```

2. Set up Brain Researcher MCP for your agent client.

   Use [`MCP_SETUP.md`](MCP_SETUP.md) for Cursor, Claude Code, Codex CLI, and
   generic MCP JSON setup. The hosted endpoint is
   `https://brain-researcher.com/mcp`, and the canonical setup page is
   <https://brain-researcher.com/mcp/setup>.

3. Add the agent template you need to your project:

   - Brain Researcher MCP work: [`agents/AGENTS.brain-researcher.md`](agents/AGENTS.brain-researcher.md)
   - General research work: [`agents/AGENTS.research.md`](agents/AGENTS.research.md)
   - PR/code-review work: [`agents/AGENTS.code-review.md`](agents/AGENTS.code-review.md)

4. Smoke-test the captured demos:

   ```bash
   python -m evals.runner --all
   ```

5. Run the public-surface checks before opening a PR:

   ```bash
   python scripts/redaction_guard.py
   git diff --check
   ```

6. Try one example:

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

- `skills/` — portable SKILL.md bundles an agent can invoke. v0.1.0 ships: `brain-researcher-session-handoff` (BR-aware session start + snapshot discipline), `neuro-big-picture` (idea framing against grand challenges and recent discourse), `journal-writing-guidelines` (neuroimaging manuscript playbook), `sherlock-oak-workflow` (Stanford Sherlock + OAK + SLURM patterns; PI-group placeholders), and `gcp-gpu-request` (GPU sizing + guarded gcloud request).
- `agents/` — `AGENTS.brain-researcher.md`, `AGENTS.research.md`, `AGENTS.code-review.md` — reusable agent-policy templates.
- `adapters/` — flat adapters: `br-adapter-map.json` + `br-fallback-policy.md` for Brain Researcher MCP routing, and `neurodesk.md` + `neurodesk-modules.json` for the Neurodesk module environment.
- `examples/` — sanitized end-to-end demos with `input/`, `expected_output/`, `rubric.yaml`, `run.sh`.
- `evals/` — AutoResearch-dimension rubrics + a small runner that scores demo outputs.

## Prerequisites

Before any of this kit is useful, the Brain Researcher MCP server has to be reachable from your agent client. See [`MCP_SETUP.md`](MCP_SETUP.md) for the 2-minute terminal flow (token in `~/.zshrc`, live check from Codex and Claude Code) — or the canonical page at <https://brain-researcher.com/mcp/setup>.

## Companion repo

- `brain-researcher-public` ships the MCP server, the contract layer (`contracts/tools/*.json` + `contracts/VERSION`), shared utilities (`br.retry`, `br.provenance`, `br.artifact`, `br.http`, `br.redaction`), and architecture docs. This kit's `pyproject.toml` declares the version dependency.

## Contributing

Found a bug, a stale tool reference, a confusing example, or a missing skill? See [`CONTRIBUTING.md`](CONTRIBUTING.md) for where to file it. Security/data-leak issues go through [`SECURITY.md`](SECURITY.md), not public issues.

## License

MIT — see [LICENSE](LICENSE).
