---
name: plan-validation
description: Use when someone asks Brain Researcher to plan, preflight, validate, review, or hand off an execution recipe for a neuroimaging analysis — the closed-loop pre-execution flow that checks a plan and produces a runnable recipe, but never runs the analysis itself.
---

# Plan Validation

## Overview

This skill wraps the Brain Researcher **pre-execution closed loop**: inspect the
live tool surface, preflight the dataset, validate and review the plan, and hand
off a runnable recipe. The discipline it enforces is a single hard rule:
**validation and recipes are not execution.** Every tool in this loop is
read-only, advisory, or a handoff. None of them runs an analysis, produces
results, or writes to a run store. Your job is to say **exactly what was checked**
(which tools ran, which verdicts came back) and **what remains caller-run** (the
recipe the caller must still execute themselves).

It relies on these BR stable-tier tools: `server_info`, `tool_search`,
`plan_preflight`, `plan_create` (optional), `pipeline_plan_validate`,
`pipeline_plan_review`, and `get_execution_recipe`. Authored against
`contract_version >= 2026-05-27`.

**When NOT to use this skill:**

- The user wants the analysis actually **run** — that is the manual/admin
  execution path (`tool_execute` / `pipeline_execute`) or the caller executing
  the recipe locally, not this loop.
- The task is grounding a scientific **claim** against evidence — use
  `evidence-grounding`.
- The task is critiquing a weak, null, or surprising **result** after a run —
  use `scientific-self-critique`. This loop is pre-execution only, so there is no
  result to critique yet.

## Workflow

1. **Confirm the live surface — `server_info` + `tool_search`.** Read
   `contract_version` (must be `>= 2026-05-27`), and confirm the
   `capabilities.planning` flag is `true` and the plan tools are in
   `stable_tools`. Use `tool_search` to confirm the exact tool names before
   invoking. Do not call plan tools from memory when the live surface disagrees
   with this template. If `server_info` fails, is version-mismatched, or a tool
   is missing, follow `adapters/br-fallback-policy.md` and announce the degraded
   mode.
2. **Preflight the dataset — `plan_preflight`.** Check dataset facts, missing
   inputs, blockers, and candidate tools. **Decision:** if preflight reports
   blockers or missing inputs, stop and report them; do not validate or hand off
   a recipe for a plan that cannot run.
3. **(Optional) Materialize the plan — `plan_create`.** Produces a read-only plan
   contract with display and execution envelopes. This creates a contract only;
   it executes nothing. Use `get_latest_plan` only to recover an existing
   validated handoff block.
4. **Validate — `pipeline_plan_validate`.** Schema normalization, path/policy
   checks, and validation issues. **Decision:** act on the verdict per
   `references/verdict-actions.md` (block / revise / proceed).
5. **Review — `pipeline_plan_review`.** Domain critique of step ordering,
   parameter ranges, modality/space compatibility, and plan completeness.
   **Decision:** a `block` verdict is a hard stop; fix the plan and re-validate.
   Do not soften a block into a warning to unblock the next step.
6. **Hand off the recipe — `get_execution_recipe`.** Produce the runnable local,
   container, or cluster recipe. This is a **handoff artifact**, not a run. The
   caller still has to execute it.
7. **Report the boundary.** State which tools ran and their verdicts, then state
   plainly that the analysis has **not** been executed and the recipe remains
   caller-run. Use `spec-only` for the plan/validation artifacts and
   `handoff-only` for the recipe. Do not paste raw MCP JSON unless asked.

## Anti-patterns

- **Do not** describe `plan_preflight`, `plan_create`, `pipeline_plan_validate`,
  `pipeline_plan_review`, or `get_execution_recipe` as having executed, run, or
  produced results from an analysis. They check, contract, and hand off — nothing
  more.
- **Do not** emit an execution recipe and imply results now exist, or blur "the
  plan validated" into "the analysis ran."
- **Do not** hand off a recipe when `plan_preflight` flagged blockers or missing
  inputs without surfacing those blockers first.
- **Do not** downgrade a `block` verdict from validate/review into a warning just
  to reach `get_execution_recipe`.
- **Do not** call plan tools from memory when the live `server_info` surface
  disagrees, or invent SDK-style / client-specific `mcp__<server>__` names.
  Confirm names from `server_info` / `tool_search`.
- **Do not** silently fall back when BR is unreachable or version-mismatched —
  announce the degraded mode per `adapters/br-fallback-policy.md`.
- **Do not** skip the checkpoint because the skill is not installed in the
  client; apply the direct MCP sequence and the hard rule instead.

## Resources

### references/

- `verdict-actions.md` — the decision table mapping each `pipeline_plan_validate`
  / `pipeline_plan_review` verdict (approve / approve-with-warnings / revise /
  block) to the next action, plus the **non-execution ledger**: for every tool in
  the loop, what it actually checked versus what remains caller-run. Consult it at
  steps 4–6 to decide whether to proceed, revise, or stop.

## Example user requests

- "Is this preprocessing plan sane before I run it?"
- "Preflight this dataset and validate my GLM plan."
- "Review my DWI pipeline ordering, then give me a command I can run."
- "Give me an execution recipe for this fMRIPrep plan."
- "Check my plan and hand me a SLURM recipe — don't run it yet."
- "Validate and review this plan, then tell me what's left for me to execute."
