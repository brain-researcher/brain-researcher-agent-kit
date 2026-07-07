---
name: sealed-commitment-preregistration
description: Lock a confirmatory fMRI analysis design — a tamper-evident commitment hash over the program and its magnitude-free design family — BEFORE any result is observed, then stop. Use when a user wants to pre-register / commit a confirmatory analysis; it seals the design and hands off, and never backfills a commitment after results exist.
---

# Sealed-Commitment Pre-registration

## Overview

This skill is the commit-before-observe discipline: compile a declarative
NeuroProgram, freeze its design family, and seal a tamper-evident commitment hash —
**before any data is observed** — then stop. Execution happens out-of-band. The
whole point is that the commitment is trustworthy *because* it predates the result;
so this skill's cardinal rule is that a commitment card is never backfilled.

Use it when a user wants to pre-register / lock a **confirmatory** analysis. Do
**not** use it to actually execute the committed family on data (that is the local
`neuroprogram-real-fmri` flow) or to run a full governed autonomous episode
(`governed-autoresearch-episode`). This is the lightweight seal-and-stop slice.

Authored against Brain Researcher MCP `contract_version >= 2026-05-27`.

## Workflow

1. **Bridge the hypothesis to a design.** `hypothesis_compile_design` — it maps the
   two-pole critical test onto real task conditions and **abstains** if the poles
   are not genuine conditions in the dataset. Honor the abstain; do not force it.
2. **Compile the program.** `neuroprogram_compile` — lowers the program onto a
   runnable plan + the pre-registration ceiling. Objective-safety is enforced here:
   a **magnitude objective is rejected** (see `references/commitment-rules.md`).
3. **Freeze the design family.** `neuroprogram_optimize_design` — magnitude-free
   Pareto search over the analysis axes; the family is what gets committed.
4. **Seal.** `neuroprogram_episode` fingerprint-locks the design family and returns
   the `program_commitment_hash` + `family` hash. **Record both, then STOP** —
   execution is out-of-band.
5. **Report the claim ceiling.** State `claim_mode` (confirmatory only if the prior
   is non-degenerate and constraints are known; otherwise **forced exploratory**),
   and that without external-dataset support the eventual claim cannot exceed L3.

If BR is unreachable or a neuroprogram tool is missing, follow
[`adapters/br-fallback-policy.md`](../../adapters/br-fallback-policy.md): announce
degraded mode; do not hand-write a "commitment hash."

## Anti-patterns

- **Do not** seal after any result is observed, and **never backfill** a commitment
  card onto an analysis that already ran (that collapses the tamper-evidence claim).
- **Do not** accept a magnitude objective (effect size, significance, novelty,
  p-value, z-score, detection power); those are rejected — surface the rejection.
- **Do not** label a run confirmatory when the prior is degenerate or a constraint
  is unknown — that forces `claim_mode=exploratory`; report it honestly.
- **Do not** override `hypothesis_compile_design`'s abstain by inventing task poles.
- **Do not** describe sealing as having executed the analysis — it commits and stops.

## Resources

- `references/commitment-rules.md` — the objective-safety rule (allowed vs rejected
  objectives), the confirmatory→exploratory downgrade conditions, and the
  claim-ceiling (L3-without-external-support) note.

## Example user requests

- "Pre-register this confirmatory GLM before I run it."
- "Lock the design family and give me the commitment hash."
- "Commit this analysis plan so the result can't be p-hacked afterward."
- "Set up a sealed commitment for the Finger>Foot contrast on ds000114."
