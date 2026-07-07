# Classification control-flow rules

The taxonomy tables (patterns, labels, lesson text) live in
`risk_taxonomy.json`. This file documents the deterministic **control flow** the
scripts apply on top of those tables, so the whole kernel is auditable. Both are
a faithful port of `classify_session` and `extract_session_lessons` in Brain
Researcher's `services/shared/session_lessons.py`.

Everything here is pure and offline. No LLM judgment, no server state.

## Stable ids

Every emitted record carries a deterministic id:

```
id = "<prefix>:" + sha1("|".join(str(part or "") for part in parts))[:12]
```

- open risk: `open_risk` | `session_id or run_id` | `label` | `item text`
- validation evidence: `validation_evidence` | `evidence_type` | `item text`
- lesson: `lesson` | `session_id` | `issue_code` | `lesson text`

Because the seed includes the item text, re-running on the same digest yields
identical ids (idempotent, diff-friendly).

## Task surfaces (`infer_task_surfaces`)

1. Build the lowercased digest text (see `digest_contract.md`).
2. For each `task_surface_patterns` entry, in order, include its `name` if the
   pattern matches anywhere in the text.
3. If nothing matched, return `["other"]` (the `task_surface_fallback`).

Surfaces are additive — a session can be on several surfaces at once.

## Validation evidence (`extract_validation_evidence`)

1. Scan `done_items` then `open_items`, in order.
2. For each item, test every `validation_evidence_patterns` entry, in order.
3. On a match, emit one evidence record `{id, evidence_type, source_field,
   text}`, deduplicated by `(evidence_type, item text)`.

An item can produce multiple evidence types; the same `(type, text)` pair is
only emitted once.

## Open risks (`classify_open_risks`)

1. For each `open_items` entry, collect every `open_risk_patterns` label whose
   pattern matches (a single item can carry several labels).
2. `matched_pattern = true` if at least one label matched.
3. If **no** label matched, assign the single fallback label
   `pre-existing-debt` with `matched_pattern = false`.
4. Emit one record per (item, label): `{id, label, text, matched_pattern}`.

The fallback means every open item produces at least one risk; a
`pre-existing-debt` label with `matched_pattern=false` marks "unclassified open
item", not a confident debt finding.

## Hygiene issues (`classify_session_hygiene`)

Emitted in this fixed order when their condition holds. Severity and message
come from `hygiene_checks` in the taxonomy.

1. `missing_source_client` (medium) — `source_client` is empty/absent.
2. `missing_final_snapshot` (high) — `has_snapshot` is false.
3. `vague_open_none` (low) — any open item lowercases to a `vague_open_values`
   entry (e.g. `none`, `n/a`, `no open issues`).
4. `succeeded_without_validation_evidence` (medium) — `status` == `succeeded`
   AND `has_snapshot` AND no validation evidence was detected.
5. `prod_without_rollout_health_evidence` (high) — `prod_task_regex` matches the
   digest text AND `prod_evidence_regex` does **not** match the joined
   `done_items + open_items` text.

## Lessons (`extract_session_lessons`)

1. Run the full classification above.
2. For each hygiene issue whose `code` is a key in `lesson_map`, emit one lesson
   `{id, issue_code, text, status:"candidate"}`.
3. Hygiene codes not in `lesson_map` produce no lesson (silently skipped).

Every lesson is a **candidate**: derived from regex classifiers over one
session's digest, not causal evidence. Promoting a candidate into durable policy
(AGENTS.md, a skill, the knowledge graph) is a separate, human/certified step —
see the interpretation-vs-certification boundary in `SKILL.md`.

## Determinism guarantee

Given the same digest and the same `risk_taxonomy.json`, the scripts are a pure
function: identical JSON output every time, no randomness, no network, no clock.
This is the property the MCP → skills carve wanted — the review/interpretation
kernel is re-runnable bit-for-bit by any reviewer.
