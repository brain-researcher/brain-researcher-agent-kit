---
name: brain-researcher-scientific-review-gate
description: Brain Researcher scientific-review discipline for artifact-level evidence, claim contracts, coverage-as-finding, and conservative report readiness.
---

# Brain Researcher Scientific Review Gate

## Scope

Use this skill when reviewing Brain Researcher scientific runs, analysis
artifacts, review bundles, manuscript claims, or product claims about scientific
execution. It adapts general scientific critical-thinking and peer-review
rubrics to BR's concrete artifact/review/report stack.

## Core Rule

Separate these states explicitly:

- `implemented`: present in code or artifact and validated on the current
  surface
- `partial`: present in some paths, profiles, or adapters only
- `spec-only`: documented contract or plan without runtime enforcement
- `handoff-only`: recipe or plan prepared for another actor to execute

Never treat a completed run as proof that the scientific claim is valid.

## Review Workflow

1. Identify the claim contract.
   - confirmatory vs exploratory
   - analysis type and outcome
   - required diagnostics for that claim
2. Build or inspect the review bundle.
   - source artifacts, sidecars, run card, feature contracts, split manifests,
     null probes, and report verdict stamps
3. Run deterministic checks before narrative judgment.
   - value domain, finiteness, shape, PSD/range/symmetry, split integrity,
     estimator diagnostics, provenance, and required-diagnostic coverage
4. Treat silence as evidence only when the producer contract says the diagnostic
   is optional.
   - for known-risk confirmatory operations, missing diagnostics are findings
5. Reconcile asserted fields against measured fields.
   - examples: `matrix_kind` vs measured matrix properties, Fisher-z state vs
     value range, split scope vs fit scope, source layer vs claim strength
6. Run scientific self-critique before report readiness.
   - "so what" check, null-result diagnosis, companion analysis, plausible
     confounds, alternative explanations, and effect-size priors

## High-Leverage Invariants

Use invariant probes when enumerating every possible bug is unrealistic:

- full-pipeline label-permutation null for leakage and selection-on-test
- subsample stability for fragile single-fold or single-subject effects
- round-trip checks for transforms such as Fisher-z
- sign, orientation, affine, and template-space checks for maps
- rank, condition number, and estimator compatibility for partial correlation

For permutation nulls, prefer a harness-owned full-pipeline rerun over accepting
`pipeline_scope: full_pipeline` as an unverified assertion.

## Reporting Discipline

When reporting a scientific result:

- state what was tested, what artifact was reviewed, and what diagnostics passed
- downgrade or block claims when required evidence is absent
- label exploratory follow-up separately from confirmatory results
- do not claim evidence-quality lift from a batch polluted by tool failure,
  rate limits, malformed JSON, or incomplete adapters
- include residual risk when a producer path is not covered by sidecar emitters

## What Not To Import Wholesale

General scientific marketplace skills contain useful rubrics, but many assume
generic paper-writing flows, broad file-format automation, or mandatory diagram
generation. In BR, keep the active gate tied to artifact evidence and claim
contracts. Use diagrams or broad EDA only when they answer the current scientific
or product question.
