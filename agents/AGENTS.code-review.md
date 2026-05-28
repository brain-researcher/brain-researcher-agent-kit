# AGENTS · code-review

Code-review and PR-discipline template. Drop into your agent's `AGENTS.md` (or equivalent) when the agent is reviewing or shepherding code changes. Derived from `brain-researcher-public`'s `CONTRIBUTING.md` and `docs/development/code_quality_guide.md`.

## Priority rules (when reviewing or making changes)

- Surgical edits. Touch only what the request requires. Don't refactor unrelated areas.
- Tie every change to a verifiable check: focused test, reproduction, lint/typecheck, or another concrete validation step.
- Don't overclaim status. Distinguish `implemented` / `partial` / `spec-only` precisely.
- Keep behavior changes, refactors, and migrations separable when practical.

## Workflow

- **Discovery before execution**: inspect existing implementations before adding parallel ones. Look in `src/`, `tests/`, `scripts/`, `docs/`.
- Prefer extending existing entrypoints (CLI commands, current service modules, existing scripts) over adding new ones.
- For new operational scripts, keep them under a topical `scripts/` subdirectory, make them rerunnable, and document inputs, outputs, env vars, and log locations. Avoid run-specific or one-off scripts directly under `scripts/`.
- If multiple options are viable, state trade-offs explicitly: correctness, speed, maintenance burden, operational cost, and infra/data requirements.

## PR workflow (when shepherding a change)

1. **Plan the change.** For non-trivial work, open a Discussion or draft issue describing what changes and why, which datasets/tools are affected, and whether a new dependency is needed.
2. **Branch.** Use `git checkout -b <type>/<short-slug>` with one of `feat|fix|refactor|docs|chore|test|perf|ci`.
3. **Make the change.**
   - **Style**: ruff + black + isort enforced via `.pre-commit-config.yaml`. `pre-commit install` if not already done.
   - **Types**: `mypy src/brain_researcher` should be clean for new code.
   - **Tests**: add unit tests for new behavior; integration tests for new service surfaces. Mark slow/external-data tests with the appropriate `pytest.mark.*`.
   - **Docs**: update `docs/` for user-facing changes; update repo-level agent instructions when conventions change.
4. **Verify before pushing.**
   ```bash
   ruff check src/ tests/
   black --check src/ tests/
   mypy src/brain_researcher --ignore-missing-imports
   pytest tests/unit -x
   pytest tests/integration            # required for service changes
   ```
   Pre-commit hooks (gitleaks, ruff, bandit, …) run automatically. Do not bypass with `--no-verify` unless fixing a hook bug.
5. **Open the PR.** Include: **What** changed and **why**; linked issue/discussion (if any); **Test plan** — what you ran, what passed; **Impact** — for refactors, paste the codegraph diff or impact-report excerpt; **Out-of-scope** — anything intentionally left for a follow-up. PRs go through CI (lint + tests + helm-render + secret scan). Reviewers focus on correctness, test coverage, and scientific defensibility for analysis-touching changes.

## Repository conventions

### Hardcoded paths

**Never** commit absolute paths (`/home/<user>/...`) into source, configs, or active docs. Use:

- env-var defaults: `os.environ.get("BR_DATA_ROOT", "/app/data")`
- repo-relative: `Path(__file__).resolve().parents[N] / "data"`
- helpers from `brain_researcher.config.paths`: `get_data_root()`, `get_config_root()`, etc.

The CI gitleaks step blocks new committed secrets; a manual grep keeps personal paths out:

```bash
grep -rln "/home/$USER" src/ apps/ configs/ scripts/ tests/ docs/ \
  --include="*.py" --include="*.ts" --include="*.tsx" \
  --include="*.yaml" --include="*.yml" --include="*.json" \
  --exclude-dir=audits --exclude-dir=operations --exclude-dir=archive
# Should print nothing.
```

### Captured experiment archives

`benchmarks/reproducibility_audit_examples/`, `benchmarks/UNIFIED_BENCHMARK_BUNDLE*/`, `docs/audits/`, `docs/operations/*/data/`, `docs/archive/` are **frozen audit trails**. Don't rewrite paths inside their JSON dumps — they're records, not code. If you need to regenerate, do it via a new run, not by editing the historical output.

### MCP tool naming

New MCP tools go under canonical SLURM-style generic names (`slurm_*` not `sherlock_*`). The existing `sherlock_*` tools are kept as deprecated aliases for one release cycle and will be removed post-v1.1.

### Architecture boundaries

PRs must not introduce new cross-boundary violations beyond the baseline at `docs/architecture/codegraph_baseline.md`. For substantial refactors, run:

```bash
python scripts/analyze_code_import_graph.py \
  --src-root src/brain_researcher \
  --markdown-out /tmp/codegraph_local.md \
  --boundary core:services --boundary llmcore:services
```

and compare against the canonical baseline. CI enforces this in `Run architecture boundary tests`.

## Adding a new analysis tool

To register a new analysis tool in the catalog so it's discoverable from the agent / MCP loop:

1. Implement the tool under `src/brain_researcher/services/tools/`.
2. Add a contract entry in `configs/tools_catalog.json` (validated by `configs/schemas/tools_catalog.schema.json` in CI).
3. Add the tool name to `configs/catalog/exposed_tools.yaml`.
4. Add an example invocation in `configs/catalog/chat_tool_schemas.yaml`.
5. Add a unit test under `tests/unit/tools/`.
6. Document inputs/outputs in `docs/api/mcp-tools.md`.
7. If the tool is meant to be OSS-stable, also add a `contracts/tools/<name>.json` entry via `scripts/oss/extract_tool_contracts.py` and tag it `stability: stable` in `_MCP_SURFACE_METADATA_BY_NAME`.

## Code quality tools

- **Ruff** (linting + formatting; replaces flake8/black/isort): line length 88, Python 3.10+. Auto-fix import sorting and simple issues with `ruff check --fix .`.
- **Mypy** (type checking): clean for new code. Tests excluded.
- **Bandit** (security scanning): low severity threshold, tests excluded.
- **Pre-commit hooks**: install once with `pre-commit install`. Run manually with `pre-commit run --all-files`. Bypassing with `--no-verify` should be reserved for hook bugs and noted in the PR.

## Releasing

Releases are cut by the maintainers. The general flow:

1. Bump version in `pyproject.toml` and `CITATION.cff`.
2. Update `CHANGELOG.md` (Keep-a-Changelog format) and `contracts/VERSION` if the stable-tier contract surface changed.
3. Tag the commit: `git tag -a vX.Y.Z -m "vX.Y.Z" && git push --tags`.
4. CI builds Docker images, publishes to GHCR, and uploads to PyPI.
5. Zenodo automatically mints a DOI for the tagged release.

## Security

- Provide secrets via env vars; never commit them.
- Prefer existing data download paths and scripts over ad hoc large-file placement.
- See `SECURITY.md` for vulnerability reporting; see `THREAT_MODEL.md` for the attack surface of the MCP server itself.
