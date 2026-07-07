---
name: neuroprogram-design-compile
description: Compile and objective-safety-check a declarative NeuroProgram (a hypothesis plus its fMRI GLM analysis-design choices) fully offline, before any data is observed. Enforces the load-bearing objective-safety invariant — magnitude objectives such as "maximize effect size", novelty, significance, association, p-value, or z-score are REJECTED; only validity/robustness/coverage objectives are allowed — and enumerates the magnitude-free design-family search space over the HRF-basis, confound-model, and high-pass axes, flagging degenerate priors that force an exploratory claim. Use when a user wants to pre-register an fMRI GLM analysis program, check that a program's objectives are not automated garden-of-forking-paths, enumerate or sanity-check a multiverse design family, or prepare inputs before calling the server-backed neuroprogram_compile / neuroprogram_optimize_design MCP tools.
---

# NeuroProgram design compile

## Overview

A *NeuroProgram* is a declarative research program: a typed hypothesis, the review-engine
`constraints` its compiled plan must satisfy, the `claims` it intends to license, a set of
`objectives`, and pinned `design_priors` over the analysis-choice axes. Compiling it lowers the
program onto a runnable multiverse design and a pre-registration ceiling — **before any result
is observed**.

This skill ports the **deterministic, offline kernel** of that flow so it can run with only this
repo and no server:

1. **Objective-safety gate** — the load-bearing invariant. A program's objectives may only target
   *validity / robustness / coverage*. Optimizing a result **magnitude** (effect size, novelty,
   significance, association, p-value, z-score) over a design space is automated
   garden-of-forking-paths and is **rejected**. See `references/objective_safety.md`.
2. **Magnitude-free design family** — enumerate the pre-registered search space over the
   HRF-basis / confound-model / high-pass axes, detect a degenerate (near-delta) prior that
   forces an exploratory claim, and — for an explicit variant list — score the family on
   magnitude-free properties only (coverage, across-variant efficiency stability, constraint pass
   rate, cost). The scoring never reads a result, z-map, or confounds value.

The auditable rule tables live in `references/` (JSON, consumed by the scripts) with prose in
`references/objective_safety.md`. The two scripts are stdlib-only and deterministic — a reviewer
can re-run them bit-for-bit.

What this skill does **not** do offline (hand off to the certified MCP server): full contrast
resolution against real task specs + the complete plan-review rule engine, KG-backed claim
verification, the real events-based design-efficiency search + Pareto fingerprint-lock, and the
tamper-evident commitment. See the Workflow's Step 4–5.

## Workflow

### Step 0: Parse the program

From the user's request assemble a program object:

- `objectives`: list of strings (e.g. `["maximize_robustness", "maximize_coverage"]`).
- `weights`: optional objective -> number.
- `design_priors`: optional `{axis: {option: weight}}` over `hrf_basis`, `confounds`, `high_pass`
  (omit an axis to search its full catalog; see `references/design_axis_taxonomy.json`).
- `claim_mode`: `confirmatory` (default) or `exploratory`; `prior_provenance` (a pre-data
  attestation string) and `unknown_constraints` if known.
- `variants`: optional explicit multiverse (list of `{variant_id, decision_points, blocked?}`).

Write it to a JSON file. The bundled fixtures `references/example_program.json` and
`references/example_design_family.json` are runnable templates.

### Step 1: Run the objective-safety gate (BLOCKING)

```bash
python scripts/check_objective_safety.py path/to/program.json
```

This rejects any objective containing a magnitude substring, rejects negative/non-finite weights,
and self-audits that the objective -> score-dimension map never points at a magnitude quantity.
**Exit code 1 means the program is unsafe — stop and report the rejection with its reason; do not
proceed to compile.** Never rewrite a magnitude objective into a safe label to get past the gate;
surface it to the user. `verdict: "objective_safe"` (exit 0) is required before Step 2.

### Step 2: Enumerate and (optionally) score the design family

```bash
python scripts/list_design_family.py path/to/program.json
```

Reports:

- `design_space.preregistered_axes` — the options each axis will actually search (fail-closed:
  a declared-but-empty axis is a `malformed_prior_axis` reject, not a silent expansion to the full
  catalog), plus the pre-registered vs. full combination counts.
- `degenerate_prior` / `degenerate_axes` — a near-delta prior (>= 0.99 mass on one option).
- `effective_claim_mode` + `forced_exploratory_reasons` — the claim is **forced to exploratory**
  when a degenerate prior lacks `prior_provenance`, or a declared constraint is unknown to the
  engine. Report the effective mode honestly; never label a forced-exploratory program
  confirmatory.
- `family_score` (only when `variants` are supplied) — the magnitude-free `DesignFamilyScore`:
  `coverage`, `efficiency_stability_maximized` (the robustness signal), `mean_efficiency_floor_only`
  (a floor, never maximized), `constraint_pass_frac`, `n_axes_varied`, `eligible` /
  `ineligible_reason` against the floors (`MIN_VARIANTS=2`, `MIN_AXES_VARIED=2`).

Note the eligibility floors: a runnable multiverse must have >= 2 passing variants and vary on
>= 2 of the 3 axes, or it is ineligible (and would force exploratory).

### Step 3: Interpret and report

Summarize for the user: is the program objective-safe? What design family will be searched? Would
the claim be confirmatory or forced exploratory, and why? If the offline family is ineligible or
degenerate, recommend broadening the priors (add axis options / raise `MIN_AXES_VARIED` coverage)
or supplying a genuine `prior_provenance` — never narrow the multiverse to a single favourable
pipeline.

### Step 4: Authoritative compile / optimize (server-backed, optional)

The offline scripts validate the objective-safety and design-family kernel. For the full,
authoritative run, hand off to the MCP tools (they run the same objective-safety rules plus the
pieces that need real task specs and the rule engine):

- `neuroprogram_compile` — resolves typed contrasts against real GLM task specs, runs the full
  plan-review rule engine over the declared `constraints`, composes the V-HRL ceiling, and returns
  the strongest claim status the program may license + a pre-registration commitment fingerprint.
  Set `verify=true` only when you want the KG/NiMARE claim-evidence gate (slower, Neo4j-bound).
- `neuroprogram_optimize_design` — the real magnitude-free Pareto search over the pre-registered
  design space using the **events-based** nilearn design-matrix efficiency (the offline
  `count_efficiency` here is an events-free DOF proxy), then fingerprint-locks the winning family.

Pass the *same* objectives/priors you validated offline; the server re-enforces objective-safety
(a magnitude objective is rejected there too).

### Step 5: Commit-before-observe (server-backed, required for a sealed claim)

A local fingerprint is advisory and forgeable. A commitment is only trustworthy when anchored
server-side with a trusted pre-observation timestamp: use `claim_commit`, or run the full
`neuroprogram_episode` chain (compile -> optimize -> execute multiverse -> bounded claim card) which
freezes both commitment fingerprints **before** the runner ever executes. **Never backfill a
commitment card after observing data.**

## Reliability rules

1. The objective-safety gate is blocking. If Step 1 rejects, stop — do not compile, and do not
   launder a magnitude objective into a safe-sounding label.
2. Report the `effective_claim_mode`, not the declared one. Degeneracy / unknown constraints /
   ineligible family all force exploratory.
3. The magnitude-free scoring reads only the design (decision points, contrast, event timing);
   never feed it a result, z-map, or confounds value, and never inject a custom efficiency
   function that does.
4. The offline `count_efficiency` is a coarse DOF proxy. For real design efficiency use the
   server-backed `neuroprogram_optimize_design`.
5. Certification (KG verification, tamper-evident commitment) stays on the MCP server — see
   `references/objective_safety.md` (interpretation-vs-certification boundary).

## Resources

### references/

- `objective_safety_rules.json` — allowed objectives, forbidden magnitude substrings, the
  objective -> score-dimension map, weight constraints, forced-exploratory conditions (machine
  source of truth for `check_objective_safety.py`).
- `design_axis_taxonomy.json` — the full axis catalog, coverage axes, confound regressor counts,
  HRF extra-regressor counts, default design priors, eligibility floors, and degeneracy threshold
  (machine source of truth for `list_design_family.py`).
- `objective_safety.md` — prose on the invariant, the three enforcement mechanisms, why the design
  search is safe, and the interpretation-vs-certification boundary.
- `example_program.json`, `example_program_magnitude_reject.json`, `example_design_family.json` —
  runnable fixtures (a safe program, an unsafe one, and a design family).

### scripts/

- `check_objective_safety.py` — the objective-safety gate over a program JSON.
- `list_design_family.py` — pre-registered design-family enumeration + degeneracy / claim-mode
  forcing + optional magnitude-free family scoring.
