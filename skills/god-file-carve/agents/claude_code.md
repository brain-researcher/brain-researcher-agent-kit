# Claude Code Prompt: God-File Carve

Use this block when Claude Code splits an oversized Brain Researcher Python
module or cuts an import cycle, without changing behavior.

```text
Carve one cohesive cluster at a time. Do not change behavior in a carve PR;
keep behavior changes in a separate PR.

For each slice:

1. Pick ONE cohesive cluster (a router, a concern) and extract it to a sibling
   module, then re-export from the original file (from .new_module import *
   # noqa: F401) so the public surface is unchanged.
2. If the new module needs the parent, import it LAZILY inside the function,
   and test BOTH import orders (parent first, child first).
3. Run the head-to-head backup diff before claiming neutrality — a static
   dependency scan is NOT sufficient. Do the over-deletion grep and the
   monkeypatch-contract check.
4. Scope ruff --fix to the authored files only.
5. Ship one reviewable PR per slice via worktree-pr-cycle (isolated worktree
   off origin/master, Codex review, user merges).

Do not claim "behavior-neutral" from a green import alone; the backup diff is
the load-bearing gate. Remember the analyzer caveat: a lazy import != a graph
cut.
```

Good final handoff shape:

```text
carved: <cluster moved and re-export path>
neutral: <backup diff result — the load-bearing gate, not just a green import>
checks: <both import orders, over-deletion grep, monkeypatch-contract>
open: <cycle still present / next slice, or "none" only if true>
next_command: <one concrete command for the next slice>
```
