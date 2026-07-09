# Claude Code Prompt: Worktree PR Cycle

Use this block when Claude Code ships a PR-shaped change to the Brain Researcher
repository and must not touch the shared checkout directly.

```text
Ship this change with the standard one-change → one-PR loop. Do not commit on
the shared checkout ~/projects/brain_researcher — its HEAD floats across
concurrent sessions.

1. Open a clean worktree off origin/master:
   git -C ~/projects/brain_researcher fetch origin
   git -C ~/projects/brain_researcher worktree add /tmp/br-<task> origin/master -b <branch>
2. Preflight-grep any enabling symbol that must already exist on master; refuse
   to run if it is absent (version skew is silent).
3. Run the narrowest meaningful gate. Activate conda per Bash call:
   source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate brain_researcher
4. Get an adversarial Codex review via the Task/Agent tool (codex:rescue), NOT
   Skill(codex:rescue). Apply fixes, re-run the gate, and verify Codex's edits
   actually landed with git status / git diff before claiming them.
5. Open the PR, then STOP. The user merges every PR. Do not gh pr merge --admin.
   Omit the Claude Co-Authored-By trailer.
6. After the user merges, prune:
   git -C ~/projects/brain_researcher worktree remove /tmp/br-<task>
   git -C ~/projects/brain_researcher branch -d <branch>

succeeded means the gate passed on this branch, NOT that the PR is merged or
deployed. Keep merge + rollout as explicit open items.
```

Good final handoff shape:

```text
changed: <paths and behavior>
verified: <gate command actually run and its result>
open: merge (user) + rollout, plus any concrete blocker
next_command: <one concrete command for resumption>
PR: <url>
```
