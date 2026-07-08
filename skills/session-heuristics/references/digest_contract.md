# Session digest input contract

The heuristics operate on a single **research-session digest** — a JSON object
describing one Brain Researcher agent session. This is the object returned under
the `digest` key by the MCP tool `research_session_digest`.

## How to obtain a digest (MCP read — not part of this skill's scripts)

Getting the digest requires the live Brain Researcher run store, so it is an MCP
call, not a local computation:

```text
research_session_digest(run_id="<run id>")
# or
research_session_digest(session_id="<stable session id>")
```

The response envelope looks like:

```json
{ "ok": true, "run_id": "...", "session_id": "...", "digest": { ... } }
```

Save the whole response (or just the `digest` object) to a file and pass it to
`scripts/session_heuristics.py`. The script unwraps a top-level `digest` key
automatically, so either form works.

If the MCP server is unavailable, say so — do not fabricate a digest.

## Fields the heuristics read

Only these fields influence classification. Everything else in the digest is
ignored by this skill.

| Field | Type | Used for |
| --- | --- | --- |
| `session_id` | string | identity; stable-id seed; surface text |
| `run_id` | string | identity fallback; surface text |
| `status` | string | `succeeded_without_validation_evidence` hygiene gate (compared lowercased to `succeeded`) |
| `source_client` | string | `missing_source_client` hygiene check |
| `has_snapshot` | bool | `missing_final_snapshot` hygiene check; gate for validation/prod checks |
| `snapshot.goal` | string | task-surface + prod-task text |
| `snapshot.next_command` | string | task-surface + prod-task text |
| `event_tags` | string[] | task-surface + prod-task text |
| `done_items` | string[] | validation evidence; prod-evidence text; success signal |
| `open_items` | string[] | open-risk classification; vague-open check; prod-evidence text |

Notes:

- `done_items` / `open_items` come from the final `write_session_snapshot`
  (`snapshot.done` / `snapshot.open`); a session with no snapshot has neither.
- List fields are normalized with "keep non-empty stripped strings"; non-list
  values are treated as empty.
- Text-based inference lowercases and joins `session_id`, `run_id`,
  `snapshot.goal`, `snapshot.next_command`, `event_tags`, `done_items`, and
  `open_items` (in that order) into one string.

## Minimal valid digest

```json
{
  "session_id": "br-example-20260707",
  "run_id": "run_20260707_example",
  "status": "succeeded",
  "source_client": "claude_code",
  "has_snapshot": true,
  "snapshot": { "goal": "...", "next_command": "" },
  "event_tags": [],
  "done_items": ["..."],
  "open_items": ["..."]
}
```

Run `scripts/validate_digest.py <digest.json>` to check which load-bearing
fields are populated before trusting the classification. A near-empty digest
reports *no* risks because there is nothing to classify — that is input-limited,
not a clean session.
