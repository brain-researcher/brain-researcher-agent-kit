# Commitment rules (objective-safety, claim-mode, ceiling)

The invariants the sealed-commitment flow must hold. These are enforced by the BR
neuroprogram tools server-side; this table is so the agent knows *why* a rejection
or downgrade happened and reports it honestly.

## Objective-safety (enforced by neuroprogram_compile)

Objectives may only target **validity / robustness / coverage**. A **magnitude
objective is rejected** — optimizing a result magnitude over a design space is
automated garden-of-forking-paths.

| Allowed (validity/robustness/coverage) | Rejected (magnitude) |
|---|---|
| maximize robustness, maximize coverage, structure-completeness, causal-support, committed-family-verification | effect size, significance, novelty, association strength, p-value, z-score, detection power / sensitivity — or any objective outside the allowed closed set |

If the program carries a rejected objective, the compile fails — surface the
rejection, do not relabel the objective to sneak it through.

## Confirmatory → forced exploratory

`claim_mode` is **confirmatory** only when both hold:

- the design prior is **non-degenerate** (not ~all mass on one option), and
- all declared constraints are **known** to the review engine.

Otherwise the claim mode is **forced to exploratory**. Report the effective mode;
never call a forced-exploratory program confirmatory.

## Claim ceiling

- Without **external-dataset** support, the eventual claim **cannot exceed L3**.
- Sealing commits the *design*; it does not raise the ceiling. The ceiling is
  reported at commit time so the user knows the strongest claim the run could license.

## The cardinal rule

Seal **before** any result is observed. Never backfill a commitment card after
results exist — the hash's value is that it predates the observation.
