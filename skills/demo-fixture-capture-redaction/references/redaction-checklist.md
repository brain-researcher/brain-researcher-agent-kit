# Redaction checklist (before committing a demo fixture)

Work top to bottom. The fixture is not committable until every row is clear and the
guard passes. Authoritative rules live in
[`REDACTION_POLICY.md`](../../REDACTION_POLICY.md); this is the operational
checklist.

## Leak classes → what to do

| Leak class | Example | Action |
|---|---|---|
| User home path | a `/home/<user>/projects/...`-style absolute path | replace with a neutral placeholder |
| Cluster / data mounts | `/oak/...`, `/data/...`, `/scratch/...` | replace with a neutral placeholder |
| Local MCP server name | a machine-specific server label | replace with the neutral server name |
| Client tool prefix | `mcp__<local-server>__tool_name` | strip to the bare tool name |
| Credentials / tokens | api keys, bearer tokens, JWTs | remove entirely |
| Internal hostnames | internal service DNS, pod names | remove or neutralize |
| Private codenames | unreleased project names | remove |

## Preserve (do NOT alter)

- The **response shape**: keys, nesting, types, array lengths that a demo/eval
  asserts on.
- Tool `contract_version` and toolset identifiers — the fixture is pinned to them.
- Real numeric results / verdicts — redact identifiers, not substance.

## Commands (all must pass, in order)

```bash
# 1. JSON validity (CI runs this over every *.json)
python - <<'PY'
import json, pathlib
for p in pathlib.Path("demos").rglob("*.json"):
    json.load(open(p))
print("json ok")
PY

# 2. the fixture is actually consumed by a demo/eval
python -m evals.runner --all

# 3. the commit gate — must print "Redaction guard passed"
python scripts/redaction_guard.py
```

## Commit note

Record which BR tool and `contract_version` the fixture was captured against, so a
future contract bump makes the staleness obvious.
