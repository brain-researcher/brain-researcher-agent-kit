# Handoff integrity decision table

Consulted at Workflow step 5, before the handoff. For each provenance field, decide
**proceed / downgrade / reject** by what came back. The rule: never proceed past a
missing or mismatched field with a silent substitution.

| Field | State | Action | User-facing line |
|---|---|---|---|
| `run_id` | present, stable across the chain | **proceed** | "sourced from run `<id>`" |
| `run_id` | drifted (read A, about to hand off B) | **reject** | "aborting: run id changed mid-handoff (read `<A>`, handoff `<B>`)" |
| `run_id` | null / unresolved | **reject** | "cannot hand off: no source run id" |
| artifact checksum | present, matches what will be forwarded | **proceed** | "forwarding `<name>` (sha256:`<…>`)" |
| artifact checksum | mismatch (forwarded ≠ read) | **reject** | "aborting: artifact `<name>` checksum changed since read" |
| artifact checksum | null / `checksum_status != ok` | **downgrade** | "forwarding `<name>` WITHOUT an integrity checksum (unverifiable)" |
| `profile_id` | present, same profile downstream | **proceed** | "scorecard read under profile `<id>`" |
| `profile_id` | differs downstream, disclosed | **downgrade** | "note: scorecard read under `<A>`, consumed under `<B>`" |
| `profile_id` | differs downstream, undisclosed | **reject** | fix: disclose or re-read under the target profile |
| consumed-by link | recorded (which run + checksums the product consumed) | **proceed** | "report consumed run `<id>` + `<n>` artifacts" |
| consumed-by link | absent | **reject** | "cannot emit an untraceable product; record what it consumed first" |

## Notes

- **Reject** = stop the handoff and report the mismatch; do not substitute.
- **Downgrade** = proceed but state the integrity gap explicitly in the handoff, so
  the consumer knows which anchor is weak.
- A `null` checksum is a *downgrade* (forward it, flagged), but a checksum
  *mismatch* is a *reject* (the bytes changed — never forward silently).
- When multiple fields are degraded, take the strictest action (any reject → reject).
- Never fabricate a checksum / `profile_id` / `run_id` to clear a row — a fabricated
  anchor is worse than a disclosed gap.
