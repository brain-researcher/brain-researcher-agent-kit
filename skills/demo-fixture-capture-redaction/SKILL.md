---
name: demo-fixture-capture-redaction
description: Discipline for capturing a live Brain Researcher MCP response and turning it into a committable public demo fixture. Use when adding or refreshing a fixture under this kit's demos/evals — so captured JSON is redacted of local paths, local server names, and client-specific tool prefixes, validates, and passes the redaction guard before commit.
---

# Demo Fixture Capture & Redaction

## Overview

This skill governs how a live MCP response becomes a **public** demo fixture in
this kit. Captured payloads routinely contain local filesystem paths, a local MCP
server name, and client-specific tool prefixes — none of which may ship in an
open-source repo. The skill enforces capture → redact → validate → guard so a
fixture is safe and reproducible before it is committed.

Use it when adding or refreshing a fixture under `demos/` / `evals/` for this kit.
Do **not** use it for a user's own analysis outputs or anything outside this
repo's fixture set.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Capture** the live response from the relevant BR MCP tool (the tool the
   fixture exercises). Keep the raw payload only in a scratch location, never
   staged for commit as-is.
2. **Redact** per [`REDACTION_POLICY.md`](../../REDACTION_POLICY.md):
   - Local paths → placeholders: `/home/<user>/...`, `/data/...`, `/oak/...` must
     not appear.
   - Local MCP server names and client-specific `mcp__<local-server>__...` tool
     prefixes → the neutral form.
   - Any credential, token, internal hostname, or private codename → removed.
3. **Validate JSON** — the fixture must parse (CI runs `json.load` over every
   `*.json`). Malformed fixtures fail the build.
4. **Run the eval harness** — `python -m evals.runner --all` — so the fixture is
   actually consumed by a demo/eval, not dead weight.
5. **Run the redaction guard** — `python scripts/redaction_guard.py`. It MUST end
   with `Redaction guard passed`. This is the commit gate.
6. **Commit** only after 3–5 are green. Note in the message which tool + contract
   version the fixture was captured against (fixtures drift with the contract).

If BR is unreachable you cannot capture a fresh fixture; follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md) and do not
hand-fabricate a payload that pretends to be a live capture.

## Anti-patterns

- **Do not** commit a fixture containing `/home/<user>/...`, `/data/...`,
  `/oak/...`, a local server name, or an `mcp__<local-server>__...` prefix.
- **Do not** commit before `scripts/redaction_guard.py` prints
  `Redaction guard passed`.
- **Do not** commit a fixture that no eval consumes — run `evals.runner --all`.
- **Do not** hand-edit a captured payload's *substance* to make a demo look better;
  redact identifiers only, keep the response shape faithful.
- **Do not** fabricate a "captured" fixture when BR was unreachable.

## Resources

- `references/redaction-checklist.md` — the pre-commit checklist mapping each
  leak class to its placeholder, plus the exact guard/validate commands.

## Example user requests

- "Add a demo fixture for `run_scorecard` to the kit."
- "Refresh the grounding demo fixtures against the current server."
- "Capture a `plan_preflight` response and make it committable."
- "Sanitize this captured MCP output so we can ship it."
