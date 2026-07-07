---
name: evidence-grounding
description: Discipline for grounding a scientific claim in resolvable evidence before it is stated as final. Use whenever an agent is about to assert a Brain Researcher finding, cite a paper/dataset/KG fact, or answer an "is this actually supported?" question — so unresolved anchors are downgraded or rejected instead of silently asserted.
---

# Evidence Grounding

## Overview

This skill enforces one rule: **a final scientific claim may not rest on an
evidence anchor that does not resolve.** It wraps the Brain Researcher grounding
tools with the decision of *what to do when the evidence is weak or missing* —
downgrade the claim's strength, or reject the claim outright.

Use it when the agent is about to state a finding as settled, attach a citation,
or answer "is X actually supported by the evidence?". Do **not** use it for
brainstorming, framing, or exploratory prompts where nothing is being asserted as
fact — grounding an idea you are not yet claiming just adds noise.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Enumerate the anchors.** List every evidence reference the claim depends on
   (KG node ids, dataset ids, paper ids, run ids, prior memory cards).
2. **Resolve each anchor** with `grounding_resolve`. An anchor that returns
   unresolved / not-found / degraded is a *weak anchor* — record it, do not drop it.
3. **Gate the evidence basis** with `grounding_gate_evidence_basis` over the full
   set. Read its verdict as the authority on whether the basis is strong enough to
   carry a *final* claim.
4. **Choose the partial action** (the core decision — see
   `references/reject-vs-downgrade.md`):
   - `partial_action="reject"` when the claim's central anchor is unresolved, or
     the claim would be *false* without it. The claim does not go out.
   - `partial_action="downgrade"` when peripheral anchors are missing but a
     weaker, honestly-scoped version of the claim still holds. State the weaker
     claim and name what is unverified.
5. **State the evidence layer explicitly** in the answer: which anchors resolved,
   which did not, and whether the emitted claim is full-strength or downgraded.

If BR is unreachable or the grounding tools are absent, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
the degraded mode and default to the *conservative* action (reject a claim you
cannot ground rather than assert it unverified).

## Anti-patterns

- **Do not** emit a final scientific claim while any central anchor is unresolved.
  Downgrade or reject — never assert-and-hope.
- **Do not** treat a `degraded`/`timeout` grounding result as a pass. Degraded is a
  weak anchor, not a resolved one.
- **Do not** silently drop an anchor that failed to resolve; surface it.
- **Do not** upgrade a downgraded claim back to full strength later in the same
  answer without re-grounding.
- **Do not** paste raw grounding JSON into the user answer; summarize resolved vs.
  unresolved and the resulting claim strength.

## Resources

- `references/reject-vs-downgrade.md` — the decision table for
  `partial_action="reject"` vs `"downgrade"`, with worked examples.

## Example user requests

- "Is it actually established that the dlPFC supports working memory maintenance?"
- "Add citations to this paragraph and tell me which ones you couldn't verify."
- "Before you put this in the report, is the evidence solid?"
- "Ground this claim against the knowledge graph."
