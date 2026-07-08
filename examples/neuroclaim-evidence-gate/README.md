# Demo · neuroclaim-evidence-gate

**Honesty-gate slice**: the `neuroclaim_compile` primitive compiles each claim into a
transparent, provenance-carrying `NeuroClaimReportV1` and refuses to overstate it — one
claim per honesty branch, each proving a distinct invariant.

## What this exercises

`neuroclaim_compile` gates the agent's OWN claims before it asserts them. Two honesty
levels are never blurred — a *structural* failure yields the crisp `ill_typed` verdict and
short-circuits; otherwise a *soft evidential* verdict is produced and no evidential verdict
ships without a mandatory sensitivity sweep. This demo pins down four properties:

| Claim (`input/claims.json`) | Branch | Invariant proven |
|---|---|---|
| Amygdala > for fearful vs neutral faces | evidential, supported | mandatory `sensitivity.ran == true` |
| "The DLPFC **engages** working memory" | reverse-inference | capped to `qualified` + reverse-inference caveat (P(region\|cognition) ≠ P(cognition\|region), Poldrack 2006) |
| EEG dataset routed into an fMRI first-level GLM | ill-typed | `ill_typed` + `verdict_basis="structural"`, evidence layer never consulted |
| Backend unreachable (Neo4j offline) | degraded | `unresolved` + `degraded=true`, never laundered to supported |

## Inputs

- `input/claims.json` — 4 claims + scopes, each entry mapping 1:1 onto the
  `neuroclaim_compile` tool arguments. The ill-typed entry supplies a `plan` that mixes an
  EEG dataset into a volumetric-MNI fMRI GLM; the degraded entry flags
  `simulate: evidence_backend_unreachable`.

## Expected output

- `expected_output/neuroclaim_report_<i>.json` — the `{"ok": true, ...NeuroClaimReportV1...}`
  report for each claim (the exact shape the MCP tool returns).
- `expected_output/_capture_notes.md` — how the committed reference set was produced
  (real compiler kernel + real rule engine for the structural branch; a stubbed evidence
  backend for the evidential/degraded branches), and what a live capture must reproduce.

The committed `expected_output/` fixture is scoreable offline with the demo runner.

## Run

```bash
bash run.sh
```

## Rubric

- `rubric.yaml` declares validity (each report's status is warranted by its own
  evidence/typecheck, never overstated) and rejection-quality (reverse-inference,
  ill-typed, and unreachable-backend cases are downgraded/refused, not silently reported).
- The deterministic checks live in `evals/checks.py::check_neuroclaim_evidence_gate`.
