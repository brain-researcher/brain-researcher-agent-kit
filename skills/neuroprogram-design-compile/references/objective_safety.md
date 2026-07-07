# Objective-safety and the interpretation-vs-certification boundary

This file is the human-readable companion to `objective_safety_rules.json` and
`design_axis_taxonomy.json`. The two JSON files are the machine-readable source of
truth that the scripts consume; this file explains *why* the rules exist and *where*
the offline skill stops and the certified server begins.

## The load-bearing invariant

> A NeuroProgram's `objectives` may only target **validity / robustness / coverage**.
> Optimizing a result **magnitude** — effect size, novelty, statistical significance,
> association strength, p-value, or z-score — over a design space is **rejected**.

Optimizing the magnitude of an observed result over a space of analysis choices *is*
automated garden-of-forking-paths: you would be searching the multiverse for the
pipeline that makes your effect look biggest, then reporting that pipeline. The whole
NeuroProgram stack exists to make that impossible by construction. Magnitude is a
**constraint** and a **reported quantity**, never an optimization target.

## Three enforcement mechanisms (all ported into the rules)

1. **Typed enum.** `NeuroObjectiveV1` has exactly five members and *no* magnitude
   member, so a magnitude objective cannot even be named.
2. **Substring validator.** A raw objective string is rejected if it contains any
   forbidden substring (`effect_size`, `novelty`, `significance`, `p_value`,
   `association`, `magnitude`, `z_score`, ...) — checked *before* enum coercion, so a
   p-hacking objective cannot be smuggled past the enum as free text.
3. **Magnitude-free score map.** The objective -> score-dimension map only ever points
   at `coverage`, `efficiency_stability`, `constraint_pass_frac`, or `neg_cost`. It
   never points at `mean_efficiency` or any magnitude quantity. `mean_efficiency` is an
   eligibility **floor** (an unestimable contrast is ineligible), never a maximization
   target — maximizing detection power for the pre-chosen contrast would be a back door
   to result-favourable selection.

## Why the design search is still safe

The optimizer picks *which experiments to run*, never *which result to keep*:

- The fitness reads only the **design** — decision points, the contrast vector, and
  event timing — never `confounds.tsv` values and never any z-map or beta. Two
  different confounds files produce byte-identical scores.
- The **maximized** robustness signal is `efficiency_stability` (across-variant
  concordance), not detection power.
- **Coverage** is entropy over the *full* axis space with a hard `k >= 2` and a per-axis
  spread floor, so a near-delta prior cannot silently collapse the multiverse onto one
  favourable pipeline — it lowers coverage instead.
- **Weights** must be finite and non-negative; a negative weight would invert a
  `maximize` objective while still reporting the safe label.
- The winning family is **fingerprint-locked before execution** (commit-before-observe),
  and reconciliation is **fail-closed**: the executed family must be a superset of the
  committed one or the robustness binding is capped.
- Optimization is still bounded by the ceiling min-law — it buys better *experiments*,
  never a stronger *claim* than the evidence warrants.

## Forced-exploratory conditions (fail-closed)

The claim mode drops from `confirmatory` to `exploratory` when any of these hold, so a
hand-narrowed or under-specified program cannot masquerade as a pre-registered
confirmatory design:

- a **degenerate** (near-delta, >= 0.99 mass on one option) design prior with **no
  pre-data `prior_provenance`** attestation;
- a **declared constraint the review engine does not know** (a typo'd or stale rule id
  is not silently treated as satisfied);
- **no candidate family met the eligibility floors**.

## Interpretation vs. certification (what this skill does NOT certify)

Per the MCP-to-skills carve, `neuroprogram_compile` / `neuroprogram_optimize_design`
are *skill-movable* because their deterministic kernel — objective-safety, the design-
axis taxonomy, and the magnitude-free scoring — is pure and offline. This skill ports
exactly that kernel. It is the **interpretation** layer.

Three things stay on the certified server and are **not** reproduced here:

1. **Full contrast resolution + rule engine.** The authoritative compile resolves typed
   contrasts against real task specs and runs the full plan-review rule engine. The
   server-backed `neuroprogram_compile` / `neuroprogram_optimize_design` tools do this.
2. **KG-backed claim-evidence verification** (`verify=true`) is Neo4j / NiMARE-bound.
3. **Tamper-evident commitment.** A local fingerprint is advisory and forgeable /
   backfillable. A commitment is only trustworthy when anchored server-side with a
   trusted pre-observation timestamp (`claim_commit`, or the `neuroprogram_episode`
   commit-before-observe chain). Never backfill a commitment card after observing data.

The offline scripts in this skill answer "are these objectives magnitude-free?" and
"what does the pre-registered design family look like, and would it be forced
exploratory?" bit-for-bit and reproducibly. For the authoritative run and the sealed
commitment, hand off to the MCP tools.
