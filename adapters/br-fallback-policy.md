# Fallback policy

How the kit should behave when the Brain Researcher MCP server is unreachable, version-mismatched, or missing a tool the adapter expects.

## Reachability check

Before any intent dispatch, call `server_info`. If it fails or times out:

- Mark BR as `unreachable` for the session and announce that in the user-facing output: "Brain Researcher MCP is unavailable; running in degraded mode."
- Do not silently fall back; an external integrator deserves to know which evidence layer their result came from.

## Version mismatch

`server_info` returns `contract_version` (date-based string from `contracts/VERSION` in `brain-researcher-public`). Each intent in `adapter-map.json` declares `contract_version_required` (the kit's minimum).

- **Server newer than kit minimum**: proceed. BR commits to one-release deprecation windows for the stable tier.
- **Server older than kit minimum**: refuse to dispatch any intent that depends on contract fields the older server doesn't return. Announce the mismatch: "BR contract is 2026-03-17 but this kit requires 2026-05-27; upgrade brain-researcher-public or downgrade brain-researcher-agent-kit."
- **Missing `contract_version` field entirely**: treat as pre-OSS / experimental BR build; refuse stable-tier intents and run only `inspect-tools` + manual fallbacks.

## Missing tool

If `server_info.stable_tools` does not contain a tool listed in an intent's `prefer` array:

1. Try the rest of the `prefer` array in order.
2. If none match, walk the `fallback` array; these are intentionally non-BR fallbacks (e.g. `local_plan_linter`, `manual_command_construction`, `manual_citation_audit`).
3. Announce the substitution: "BR did not expose `pipeline_plan_review`; ran local plan-linter against syntax only — domain critique not performed."

## Deprecated tool

If the tool name lands in `server_info.deprecated_tools`:

- The response includes `replaced_by`. Use the replacement instead.
- Log a one-line note in the agent's session output so callers can update their adapter-map on the next iteration.
- Do not block on deprecation — accept the deprecated call for one release cycle.

## What never falls back

Some intents have no safe non-BR fallback:

- `ground-evidence` — without BR's KG and document resolvers, there is no equivalent verification path. If BR is unreachable, do not emit a final report; downgrade all claims to "unverified" and stop.
- `generate-report` — without `scientific_report_generate` and `grounding_gate_evidence_basis`, the kit must not draft a report at all. Emit the structured evidence bundle instead and let a human assemble.

## Degraded-mode reporting

When operating in any fallback path, the kit's user-facing summary must include a `degraded:` line listing the affected intents and the fallback that was used. Example:

```
degraded: validate-plan -> local_plan_linter (BR pipeline_plan_validate unavailable);
          ground-evidence -> skipped (no fallback); report emission blocked.
```
