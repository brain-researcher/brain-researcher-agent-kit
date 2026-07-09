---
name: god-file-carve
description: Split a huge Python module into cohesive router/submodules (or break an import cycle) without changing behavior — re-export + lazy import-back, proven behavior-neutral by a head-to-head backup diff, one reviewable PR per slice. Use when a module is too big (mcp/server.py, br_kg/query_service.py, any file >~2k lines), the user says "keep carving", or you need to cut an import cycle.
---

# god-file-carve

A behavior-neutral decomposition recipe for oversized Python modules. Promoted from the
`feedback_god_file_carve_methodology` memory, which was applied 3+ times (server.py 20-tools → 7
routers; query_service.py 14,909 → 13,070 lines; services/* cycle cleanup) — this makes the
checklist invokable instead of re-remembered.

## When To Use

- A module is too large to reason about, or the user says "keep carving".
- Breaking an import cycle (top-level or `core/*` / `services/*`).
- NOT for: behavior changes or refactors that intentionally alter output — keep those in a separate PR.

## Workflow (per slice)

1. **Pick ONE cohesive cluster** — a group of functions/classes that move together (a router, a
   concern). Don't carve across concerns in one slice.
2. **Extract to a sibling module + re-export** — move the cluster out, then in the original file
   `from .new_module import *  # noqa: F401` (or explicit names) so the public surface is unchanged.
3. **LAZY import-back for cycle safety** — if the new module needs something from the parent, import
   it *inside the function*, not at module top. **Test BOTH import orders** (`import parent` first,
   and `import child` first) — a cycle often only bites one order.
4. **Head-to-head backup diff = the load-bearing gate.** Before the cut, snapshot a baseline; after,
   diff the public surface / a byte-identical behavior probe against it. **A static dependency scan
   is NOT sufficient** — it always misses something (non-underscore helper fns, module constants,
   stdlib re-exports, type annotations). The backup diff is what actually catches over/under-deletion.
5. **Over-deletion check** — after scripted cuts, confirm nothing still-referenced was removed
   (grep the deleted names across the tree).
6. **Monkeypatch-contract check** — if tests monkeypatch `module.symbol`, the re-export must keep that
   attribute resolvable at the old path, or the patch silently no-ops.
7. **One reviewable PR per slice** — hand to `worktree-pr-cycle` (isolated worktree off origin/master,
   Codex review, user merges). Small slices review faster and revert cleanly.

## Parallelism

For a multi-file campaign over **disjoint** file-sets, fan out to parallel subagents, each in its own
`/tmp` worktree (per AGENTS.md). Keep each agent's file-set disjoint so their edits don't collide.

## Honesty / invariants

- "carved" ≠ "behavior-neutral" until the backup diff passes — don't claim neutrality from a green
  import alone.
- Note the analyzer caveat: import-cycle tools often count lazy imports, so a lazy import ≠ a graph cut.
- Scope `ruff --fix` to the authored files only — a repo-wide glob reformats unrelated legacy files.

## Client Prompt Artifacts

- `agents/openai.yaml` for Codex/OpenAI skill launch metadata.
- `agents/claude_code.md` for a compact Claude Code instruction block.

Keep both adapters in this skill directory. Repo pointer invariant:
do not duplicate the policy into `CLAUDE.md` (repo convention: instructions live in AGENTS.md; CLAUDE.md only points there).

## Related memory

`feedback_god_file_carve_methodology`, `project_mcp_server_carve_and_trackb`,
`project_codegraph_cycle_cleanup`.
