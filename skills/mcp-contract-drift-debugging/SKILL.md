---
name: mcp-contract-drift-debugging
description: Use when a Brain Researcher MCP call fails with an unknown-tool, bad-argument, or contract/version error, or when a tool name from memory or the AGENTS template no longer matches the live server surface — reconcile names, arguments, and contract against server_info, tool_search, and tool_get before retrying.
---

# MCP Contract Drift Debugging

## Overview

This skill enforces one discipline: when the live Brain Researcher MCP surface
disagrees with what you remember or what the template says, **stop calling from
memory and re-confirm every name, argument, and contract field against the
server itself**. Tool names, argument schemas, and the stable tier evolve;
guessing at a name that "used to work" produces a plausible-looking call that
silently fails or hits the wrong tool.

The relied-on stable-tier tools are `server_info` (contract, stable/deprecated
inventory, capabilities), `tool_search` (capability rediscovery), and `tool_get`
(exact name + argument schema). Authored against **`contract_version >= 2026-07-08`**.

**When NOT to use.** If the server is reachable, the tool you want is in
`stable_tools`, and the name matches, there is no drift — just call it. This is
not the general health check (that is `server_info` + `system_self_test`, see the
"Health check" section of `AGENTS.brain-researcher.md`), and it is not for
diagnosing scientific/result errors — only for tool/contract mismatch.

## Workflow

1. **Snapshot the live contract — `server_info`.** Read `contract_version`, the
   `stable_tools` array, `deprecated_tools` (with each entry's `replaced_by`),
   the `capabilities` flags, and the toolset hash. If `server_info` itself fails
   or times out, BR is `unreachable`: announce degraded mode and stop per the
   "Reachability check" in `adapters/br-fallback-policy.md`.

2. **Gate on `contract_version`.** Compare to the kit minimum `2026-05-27`.
   Server newer → proceed. Server older → refuse any stable-tier intent that
   needs contract fields the old server won't return, and announce the mismatch.
   `contract_version` field absent → treat as pre-OSS/experimental: run only
   inspection + manual fallbacks. Follow the "Version mismatch" rules in the
   fallback policy. See `references/drift-decision-table.md` for the exact triage.

3. **Locate your intended tool on the live surface.** Is the name in
   `stable_tools`? If it is in `deprecated_tools`, read `replaced_by`, switch to
   the replacement now, and **plan for the rename within one release cycle** —
   the deprecated alias is accepted for exactly one cycle, not indefinitely
   (e.g. `sherlock_guide`/`sherlock_slurm` alias `slurm_guide`/`slurm_submit`).
   If the name is in neither array, do **not** call it from memory — go to step 4.

4. **Rediscover by capability, not by guessing — `tool_search`.** Query the
   intent in words (`tool_search`), or use `tool_search_structured` for a
   method/software/version lookup, `tool_resolve` to map a method/op key to a
   concrete tool, or `workflow_search` for a workflow-level route. Take the
   current tool name from the result, never from an SDK-style guess.

5. **Confirm the exact schema — `tool_get`.** Before re-invoking, call `tool_get`
   on the resolved name to read its current argument schema, then re-map your
   arguments (a "bad argument" drift is usually a renamed or retyped field, not a
   missing tool). Do not reuse stale argument shapes from memory.

6. **Retry with the confirmed name + arguments.** If the intended capability is
   still not exposed, walk the intent's `fallback` chain (see "Missing tool" in
   the fallback policy), and announce the substitution in a `degraded:` line so
   the caller knows which layer produced the result.

7. **Record the drift for the caller.** Note the one-line delta (deprecated →
   `replaced_by`, renamed argument, contract bump) in the session output so the
   caller can update their `adapter-map` on the next iteration. Persist it with
   `memory_write` only if the user explicitly asks.

## Anti-patterns

- **Calling a tool from memory or the AGENTS template when `server_info` /
  `tool_search` disagree.** The live surface is the source of truth; reconcile
  first.
- **Inventing SDK-style or client-specific names.** Never fabricate a name or
  carry a `mcp__<local-server>__...` prefix; confirm from `server_info`,
  `tool_search`, or `tool_get`.
- **Dispatching a stable-tier intent against a server older than `2026-05-27`,**
  or against a build with no `contract_version` field.
- **Dropping a deprecated tool the instant you see it.** Migrate to `replaced_by`
  but accept the deprecated call for one release cycle; do not block on it.
- **Skipping `tool_get` and passing stale arguments** to a tool that resolved by
  name but changed its schema.
- **Falling back silently.** Every substitution or degraded path must be
  announced to the caller.
- **Treating this as a health probe or a fix for scientific/result errors** — it
  is scoped to tool/contract mismatch only.

## Resources

### references/

- `drift-decision-table.md` — the triage table: each observed drift (unreachable,
  version older/newer/missing, deprecated tool, missing tool, unknown name, bad
  argument) mapped to its `server_info` signal, the proceed / degrade / refuse
  action, and the user-facing line. The auditable reject-vs-downgrade rubric,
  aligned to `adapters/br-fallback-policy.md`.

## Fallback path

This skill's degraded behavior is governed by
**`adapters/br-fallback-policy.md`** — specifically its "Version mismatch",
"Missing tool", and "Deprecated tool" sections. When BR is unreachable,
version-mismatched, or missing a tool, follow that policy and surface a
`degraded:` line; do not silently substitute.

## Example user requests

- "The `pipeline_plan_review` call is throwing unknown-tool — did it get renamed?"
- "My agent's tool list doesn't match what the server exposes anymore."
- "`server_info` says contract `2026-03-17` but the kit needs `2026-05-27` — what can I still run?"
- "`tool_search` says a tool I depend on is deprecated; what do I switch to?"
- "This BR call fails with a bad-argument error — reconcile the arguments against the live schema."
- "Reconcile my remembered BR tool names against the current server surface before we retry."
