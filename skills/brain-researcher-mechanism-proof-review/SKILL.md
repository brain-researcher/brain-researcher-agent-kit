---
name: brain-researcher-mechanism-proof-review
description: Brain Researcher review discipline for Society, NeuroClaim, Verification Bench, gate, conductor, claim-commit, and persisted-artifact changes where tests must prove that the real mechanism fired.
---

# Brain Researcher Mechanism-Proof Review

## Scope

Use this skill for review or implementation work involving:

- Society conductor, commissioner, or survival-gate behavior
- NeuroClaim claim/evidence binding
- Verification Bench gates or external-compute floors
- persisted claim cards, refusal cards, or adjudication artifacts
- claim commit, run binding, required falsifiers, or fail-closed adapters

The central question is not "did a test pass?" It is "did the real mechanism
run and produce evidence that only that mechanism could produce?"

## Review Sequence

1. Inspect the real diff first:

```bash
git show --stat HEAD
git show HEAD
git diff --name-status <base>...<ref>
```

Use the exact form requested by the user. In read-only PR review, prefer
fetched refs and avoid switching the shared checkout.

2. Inspect every changed file from the diff, not only files named in the prompt.
Exports, CLI wiring, and adapters can change the verdict.

3. Trace the real path:

- entrypoint
- adapter/router
- conductor/gate
- persisted artifact writer
- persisted artifact reader
- final synthesized status
- production consumer

4. Separate evidence tiers:

- full mechanism proof: real path ran and produced a mechanism-specific
  artifact or status
- partial evidence: adapter call, monkeypatch route, unit happy path, or export
- no production proof: only tests/exports exist and no consumer wiring is found

## Required Probes

Choose probes that match the changed mechanism:

- malformed or legacy persisted card fails closed
- bad run id fails structurally instead of falling back
- evidence payload is bound to the resolved run, not just path-exists checked
- required falsifiers are enrolled into real strategies
- `earned_checks` cannot outrun `survived_checks`
- non-finite numeric scores cannot win selectors
- imports and external failures stay inside structured-error boundaries
- diagnostic actions do not accidentally bypass a required runnable gate

## Validation

Prefer focused tests plus narrow in-memory probes:

```bash
TMPDIR=/dev/shm PYTHONDONTWRITEBYTECODE=1 pytest <focused-target> -q -p no:cacheprovider
```

When running in a repo worktree, follow the repository Conda rule from
`AGENTS.md`. If temp directories or worktree access fail before collection,
report an environment blocker and do not convert that into a code finding.

## Findings

For read-only review, lead with findings and include:

- exact `file:line`
- concrete failing input or trigger
- expected behavior
- actual bad outcome
- whether the issue is confirmed, partial, or blocked

If no defect is confirmed, say that directly. Put remaining uncertainty in
coverage gaps, not invented findings.

## Guardrails

- Do not treat monkeypatched calls as full mechanism proof.
- Do not treat exported symbols as production consumers.
- Do not overread successful run completion as scientific or claim validity.
- Do not claim answer-proof gating unless raw evidence, persisted artifacts,
  and final synthesized status all support it.
