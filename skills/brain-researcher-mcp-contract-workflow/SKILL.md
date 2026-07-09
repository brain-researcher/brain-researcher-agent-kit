---
name: brain-researcher-mcp-contract-workflow
description: Brain Researcher MCP contract repair workflow. Use when changing or reviewing MCP tool behavior, response shape, schema/docs parity, planner/MCP wrapper contracts, `docs/mcp_tools.schema.json`, or focused `tests/unit/mcp` coverage in this repository.
---

# Brain Researcher MCP Contract Workflow

## Overview

Use this skill to keep MCP runtime code, public schema documentation, and focused
tests aligned. The goal is a narrow contract fix with explicit validation, not a
repo-wide cleanup.

## Workflow

1. Read `AGENTS.md` first and carry forward any protected paths or scope limits
   from the user.
2. Inspect the actual implementation before editing:
   - `src/brain_researcher/services/mcp/server.py`
   - related service code such as `src/brain_researcher/services/br_kg/`
   - existing focused tests under `tests/unit/mcp/`
   - `docs/mcp_tools.schema.json` when signatures, descriptions, enums, or
     response shapes change
3. Reproduce or trace the contract mismatch with the smallest local check
   available. Distinguish implemented, partial, spec-only, and handoff-only
   surfaces.
4. Make the narrowest code change that fixes the observed contract. Avoid
   refactors, broad routing rewrites, or opportunistic fixes unless the user
   asked for them.
5. Update `docs/mcp_tools.schema.json` in the same change when tool parameters,
   descriptions, enums, validation semantics, or result fields changed.
6. Add or update focused tests for the changed behavior. Prefer one test per
   contract papercut over broad snapshot churn.
7. Run focused validation first, then the requested wider MCP suite when
   feasible.

## Validation

Use the narrowest meaningful command set for the touched surface, for example:

```bash
python -m json.tool docs/mcp_tools.schema.json >/dev/null
python -m py_compile src/brain_researcher/services/mcp/server.py
pytest tests/unit/mcp/test_mcp_contract_papercuts.py -q
pytest tests/unit/mcp/test_local_mcp_server.py -q -k "plan_preflight or plan_create"
pytest tests/unit/mcp -q
git diff --check -- src/brain_researcher/services/mcp/server.py docs/mcp_tools.schema.json tests/unit/mcp
```

Only run commands that match the actual edit. If the wider MCP suite fails,
separate new regressions from known unrelated failures and report the exact
failing tests.

## Common Fix Shapes

- Aggregated validation errors for missing required fields.
- Explicit supported-value lists for unsupported enum/action/card inputs.
- Schema-visible `Literal[...]` or enum typing for constrained parameters.
- Wrapper-level conditional-parameter validation before a deeper tool call.
- Preservation of worker-side policy reasons or degraded-state diagnostics.
- Session-binding hints for directive/verdict or handoff-style round trips.

## Handoff

Report changed files, exact validation commands and results, protected paths
left untouched, unrelated dirty-worktree noise, and the next command needed to
resume. Do not claim the whole MCP surface is fixed when only a focused contract
was validated.
