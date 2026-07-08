# Verdict → action + the non-execution ledger

Consulted at Workflow steps 4–6. Two parts: how to act on each validate/review
verdict, and the ledger of what each tool actually did (so the boundary report is
honest).

## Verdict → next action

| Verdict (from `pipeline_plan_validate` / `pipeline_plan_review`) | Action |
|---|---|
| `approve` / ok | proceed to the next step (review, then recipe) |
| `approve_with_warnings` | proceed, but surface every warning in the report; do not silence them |
| `revise` | fix the plan, then re-run `pipeline_plan_validate` before continuing — do not hand off a recipe for an unrevised plan |
| `block` | **hard stop.** Fix the plan and re-validate. Never downgrade a block to a warning to reach `get_execution_recipe` |

Rule: a `block` at validate OR review stops the loop. The recipe handoff
(`get_execution_recipe`) happens only after both validate and review are clear (or
clear-with-disclosed-warnings).

## The non-execution ledger

For the boundary report — what each tool actually did vs. what remains caller-run:

| Tool | What it did | What it did NOT do |
|---|---|---|
| `server_info` / `tool_search` | confirmed the live surface | — |
| `plan_preflight` | checked dataset facts, missing inputs, blockers, candidate tools | did not run anything |
| `plan_create` | produced a read-only plan contract | executed nothing; no run store write |
| `pipeline_plan_validate` | schema/path/policy checks, validation issues | did not run the analysis |
| `pipeline_plan_review` | domain critique (ordering, params, modality/space, completeness) | did not run the analysis |
| `get_execution_recipe` | produced a runnable local/container/cluster recipe (a **handoff artifact**) | did **not** execute it — the caller must run it |

## The boundary line

Always close with: "**Checked:** <tools that ran + verdicts>. **Not executed** — the
recipe is caller-run." Never blur "the plan validated" into "the analysis ran," and
never imply results exist from a recipe.
