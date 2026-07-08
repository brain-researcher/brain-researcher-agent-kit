# Degraded handoff (blocked report)

When `grounding_gate_evidence_basis` says the basis is too weak for a final report,
the skill returns a **degraded handoff** instead of a polished document. The point
is that the recipient can tell exactly which evidence layer the output came from
and what would unblock the real report.

## Must contain

1. **Header** — one line stating the report was *not* emitted and why:
   "Final report blocked: evidence basis did not pass the grounding gate."
2. **Grounded subset** — the claims/anchors that DID resolve, with their strength.
   These are safe to state.
3. **Unresolved anchors** — the specific anchors that failed to resolve or came
   back degraded, each tied to the claim it would support.
4. **Confirmatory vs. exploratory** — of the grounded claims, which are confirmatory
   and which are exploratory follow-ups (never blur the two in a handoff).
5. **Unblock step** — the concrete next action that would let a full report pass
   the gate (e.g. "resolve dataset id X", "re-run grounding after KG backfill",
   "gather the missing causal-link evidence").

## Wording template

```
Final report blocked — evidence basis did not pass the grounding gate.

Grounded (safe to state):
  - <claim> — anchors <ids> resolved (confirmatory)
  - <claim> — anchors <ids> resolved (exploratory)

Not established (report withheld):
  - <claim> — anchor <id> unresolved / degraded

To unblock a full report:
  - <specific next step>
```

## Do not

- Do not emit the polished report "with caveats" as a substitute — a caveated full
  report still reads as authoritative. Block it and hand off.
- Do not omit the unblock step; a degraded handoff without a path forward is just a
  refusal.
