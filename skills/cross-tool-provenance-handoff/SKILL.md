---
name: cross-tool-provenance-handoff
description: Use when a persisted run's outputs (a bundle, scorecard, or artifacts) are being handed to a downstream Brain Researcher report or review tool and the run_id, artifact checksums, profile id, and consumed-by links must survive every step of the handoff intact.
---

# Cross-Tool Provenance Handoff

## Overview

Use this skill when the output of one Brain Researcher run becomes the input to a
downstream report or review tool — the moment provenance is most easily lost.
The discipline is simple and non-negotiable: the **source `run_id`**, the
**artifact checksums** you forward, the **profile id** a scorecard was read
under, and the **consumed-by relationship** (which downstream product consumed
which run + checksums) must be carried through the whole chain and stated in the
handoff. A report or review that cannot name the run and checksums it consumed is
not traceable, and a silently swapped run or stale scorecard is a provenance bug,
not a convenience.

This skill wraps the stable-tier tools `run_bundle_get`, `run_scorecard`, and the
`artifact_*` inspection surface (`artifact_list`, `artifact_get_metadata`), then
feeds a downstream `scientific_report_generate`, `run_scientific_review`,
`run_code_review`, or `request_scientific_review`. It was authored against
`contract_version >= 2026-05-27` and depends on the `run_observability`
capability. It adds no new logic — only the threading discipline around the
existing calls.

**When NOT to use.** Skip it for a single read-and-stop lookup where nothing is
forwarded (just inspecting a run). It is also not the evidence gate: if the
downstream is a *final* report drafted from literature/KG evidence, the
`grounding_gate_evidence_basis` decision belongs to `final-report-gate` /
`evidence-grounding`. This skill governs the identifier/checksum chain between
tools, not whether the underlying claim is grounded.

## Workflow

1. **Preflight the surface** — call `server_info`. Confirm `contract_version >=
   2026-05-27`, that `run_observability` is `true`, and that `stable_tools`
   lists the run/artifact tools you need. Confirm the downstream tool name from
   the live surface (`server_info` / `tool_search`) — never call it from memory.
   If BR is unreachable or version-mismatched, follow
   [`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md):
   announce degraded mode and do not fabricate the chain.
2. **Pin the source run** — identify the run with `run_list` or
   `run_find_latest_reviewable` and record its `run_id`. This id is the root of
   the provenance chain; it must not change for the rest of the handoff.
3. **Pull the observation surface** — call `run_bundle_get(run_id)` for the
   normalized bundle and/or `run_scorecard(run_id, ...)` for the scorecard.
   Record the **`profile_id`** the scorecard was resolved under (it defaults to
   the server's `DEFAULT_LOOP_PROFILE_ID`; pass it explicitly when comparing
   across profiles). Use `loop_profile_get` if the downstream needs the policy
   behind that profile.
4. **Checksum every artifact you will forward** — enumerate with
   `artifact_list(run_id)`, then call `artifact_get_metadata` per artifact to
   capture its size/time/**checksum**. The checksum is the integrity anchor: the
   downstream product must reference the same checksum it actually consumed.
5. **Verify integrity before the handoff** — compare the `run_id`, `profile_id`,
   and artifact checksums you are about to forward against what you read. If any
   is missing, mismatched, or came back null, consult
   [`references/handoff-integrity-table.md`](references/handoff-integrity-table.md)
   and **reject or downgrade** — do not proceed with a silent substitution.
6. **Hand off, threading the identifiers** — call the downstream tool with the
   pinned `run_id` (and `profile_id` when relevant): `scientific_report_generate`
   (pass exactly one of `run_id` / `autoresearch_dir`), `run_scientific_review`,
   `run_code_review`, or `request_scientific_review`. Record the **consumed-by**
   relationship: which `run_id` and which artifact checksums this downstream
   product consumed.
7. **Chain the evidence gate for final reports** — if the downstream is a final
   report, unresolved evidence must block polished emission (route to
   `final-report-gate`). `scientific_report_generate` already gates internally —
   do not double-gate, but do not bypass it either to keep the chain "clean".
8. **State provenance in the handoff** — the user-facing summary names the source
   `run_id`, the `profile_id`, the artifact checksums forwarded, and the
   downstream product that consumed them. Summarize; do not paste raw bundle or
   scorecard JSON unless the user asks.

## Anti-patterns

- Forwarding an artifact without first capturing its checksum via
  `artifact_get_metadata` — an unchecksummed handoff is unverifiable.
- Letting the `run_id` drift mid-chain: reading run A's bundle but generating the
  report or review against run B.
- Letting the `profile_id` drift: handing a scorecard read under one profile to a
  downstream tool under a different profile without saying so.
- Dropping the consumed-by link: emitting a report/review that never records
  which run and which checksums it consumed.
- Proceeding past a checksum / profile / run_id mismatch instead of rejecting or
  downgrading per `references/handoff-integrity-table.md`.
- Fabricating a checksum, `profile_id`, or `run_id` when the tool returned none —
  report it as missing and degrade rather than invent it.
- Calling the downstream report/review tool from memory or inventing a
  client-specific `mcp__...` name instead of confirming it from `server_info` /
  `tool_search`.
- Generating a final report from unresolved evidence just to keep the chain
  intact — block and return a degraded handoff instead.
- Pasting raw `run_bundle_get` / `run_scorecard` JSON into the final answer.

## Resources

### references/

- `handoff-integrity-table.md` — the reject / downgrade / proceed decision table,
  keyed on which provenance field (`run_id`, artifact checksum, `profile_id`, or
  the consumed-by link) is missing or mismatched, with the required action and
  the user-facing line for each case.

## Example user requests

- "Take the scorecard from run `<id>` and generate the report."
- "Feed this run's bundle into a scientific review."
- "Hand the latest reviewable run off to a code review and keep the provenance."
- "Turn run `<id>`'s artifacts into a LaTeX report — I need to know exactly which
  outputs it used."
- "Score this run, then write it up, and make sure the write-up cites the run and
  artifact checksums it consumed."
- "Pass the run bundle to `request_scientific_review` without losing the run id."
