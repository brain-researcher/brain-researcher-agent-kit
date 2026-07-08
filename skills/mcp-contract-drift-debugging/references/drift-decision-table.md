# Contract-drift decision table

The auditable triage for "the live Brain Researcher MCP surface disagrees with
what I expected." Read the signal off `server_info` (and `tool_get` for
arguments), pick the action, and emit the user-facing line. This table is the
reject-vs-downgrade rubric for the `mcp-contract-drift-debugging` skill and is
aligned to `adapters/br-fallback-policy.md`. Authored against
`contract_version >= 2026-05-27`.

## Triage

| Observed drift | Signal to read | Action | User-facing line |
|---|---|---|---|
| Server unreachable | `server_info` fails / times out | **Refuse** stable-tier intents; run manual fallbacks only | `Brain Researcher MCP is unavailable; running in degraded mode.` |
| Contract older than kit minimum | `contract_version` < `2026-05-27` | **Refuse** any intent needing fields the old server won't return | `BR contract is <ver> but this kit requires 2026-05-27; upgrade brain-researcher-public or downgrade the kit.` |
| `contract_version` field absent | key missing from `server_info` | **Refuse** stable tier; treat as pre-OSS; run only inspect + manual fallbacks | `BR build predates the OSS contract; only tool inspection is available.` |
| Contract newer than kit minimum | `contract_version` >= `2026-05-27` | **Proceed** (BR honors one-release deprecation windows) | (no line needed) |
| Intended tool is deprecated | name in `deprecated_tools`, has `replaced_by` | **Downgrade**: use `replaced_by` now; migrate within one release cycle | `<old> is deprecated; using <replaced_by>. Update your adapter-map within one release cycle.` |
| Intended tool not exposed | name not in `stable_tools` and no `replaced_by` | **Downgrade**: rediscover via `tool_search` / `tool_resolve`; else walk the intent `fallback` chain | `BR did not expose <tool>; substituted <fallback> — <what was/was not done>.` |
| Unknown / remembered name | name in neither `stable_tools` nor `deprecated_tools` | **Refuse to call from memory**; rediscover via `tool_search` + confirm with `tool_get` | `<name> is not on the live surface; resolved to <confirmed> via tool_search.` |
| Bad-argument error, tool resolves | `tool_get` schema differs from the call | **Downgrade**: re-map arguments to the current schema, then retry | `<tool> argument <field> changed; re-mapped and retried.` |
| Capability flag off | `capabilities.<flag>` is `false` | **Refuse** intents that depend on that capability | `BR capability <flag> is disabled on this server; cannot run <intent>.` |

## Notes

- **Never falls back.** `ground-evidence` and `generate-report` have no safe
  non-BR substitute. If BR is unreachable or version-mismatched, do not emit a
  final report — downgrade claims to unverified and stop. See the "What never
  falls back" section of `adapters/br-fallback-policy.md`.
- **Deprecation is one cycle.** A `deprecated_tools` entry is honored for exactly
  one release cycle. Accept the call, migrate to `replaced_by`, and log the delta
  so the caller updates before the next contract bump.
- **Rediscover, do not guess.** When a name is unknown, the only valid sources
  for the replacement are `server_info.stable_tools`, `tool_search` /
  `tool_search_structured` / `tool_resolve`, and `tool_get`. Do not fabricate a
  name or preserve a client-specific `mcp__<local-server>__...` prefix.
- **Announce every substitution.** Any refuse/downgrade path must appear in a
  `degraded:` line in the user-facing summary, e.g.:

  ```
  degraded: review-plan -> deprecated pipeline_plan_review resolved to <replaced_by>;
            ground-evidence -> skipped (no fallback); report emission blocked.
  ```
