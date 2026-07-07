---
name: session-lessons-to-memory-promotion
description: At the end of a research session, extract lessons and open risks and promote only the durable, verdict-backed ones into Brain Researcher memory / the KG — never promoting an unverified lesson. Use to close out a research session and turn what was learned into accepted memory without laundering an unverified claim into the knowledge base.
---

# Session Lessons → Memory Promotion

## Overview

This skill closes a research session by turning what was learned into *accepted*
memory — under the invariant that a lesson or claim may **not** be promoted to
accepted memory or the BR-KG without a verification verdict. Candidate-lane items
stay quarantined until they pass acceptance. This is the research-lesson promotion
flow, distinct from coding-session handoff.

Use it at the end of a research session to capture lessons + open risks and file the
durable ones. Do **not** use it for coding-session state transfer (that is
`brain-researcher-session-handoff`).

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Digest the session.** `research_session_digest` for the one session — the
   per-session carrier the extraction tools operate on.
2. **Extract lessons + risks** (per-session pure tools only):
   `session_lesson_extract` and `session_risk_classify` over the digest;
   `session_open_risks_query` to see repeated blockers.
3. **Screen for promotability.** A lesson/claim is promotable only if it carries a
   verification verdict. An unverified lesson stays a candidate — it is *not*
   promoted.
4. **Promote the durable ones.** `memory_write` for verdict-backed memory cards;
   `session_backfill_to_kg` (dry-run by default) to preview KG writes. Use
   `dry_run=false` only when Neo4j is configured **and** the user explicitly wants KG
   writes.
5. **Report** what was promoted, what stayed quarantined (and why — no verdict), and
   the open risks worth carrying forward.

If BR is unreachable or a session tool is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not write memory/KG you could not verdict-gate.

## Anti-patterns

- **Do not** promote a lesson/claim to accepted memory or the BR-KG without a
  verification verdict — quarantine it instead.
- **Do not** run `session_backfill_to_kg(dry_run=false)` without configured Neo4j
  and explicit user intent; treat the dry-run rows as a preview.
- **Do not** use the whole-store-scan tools here (`session_learning_report_generate`,
  `session_policy_cards_generate`, `session_signal_report_generate`,
  `research_log_summary`) — they scan every user's runs (a cross-user privacy
  surface). Stay on the per-session pure tools.
- **Do not** paste raw digest/lesson JSON into the user answer; summarize promoted vs.
  quarantined.
- **Do not** silently drop an open risk; carry it forward explicitly.

## Resources

None — clean per-session tool sequence. The promotability rule (verdict-gated) is in
the Workflow; the privacy exclusion is in Anti-patterns.

## Example user requests

- "Wrap up this session — capture the lessons and file the durable ones."
- "What did we learn here that's worth saving to memory?"
- "Promote the verified lessons to the KG (dry-run first)."
- "What open risks from this session should carry forward?"
