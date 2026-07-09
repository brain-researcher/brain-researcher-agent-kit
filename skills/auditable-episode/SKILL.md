---
name: auditable-episode
description: Run one offline, deterministic, PII-scrubbed auditable-research episode. It seals a commitment card first, verifies its hash before emitting anything, runs offline neuroclaim_compile on a NiMARE backend plus the deterministic permutation_null battery, and emits a redacted audit bundle. Use to demonstrate or re-validate the commit-before-observe audit chain portably: a planted signal is supported with a banked score, and a null is rejected with the score withheld. Needs a Brain Researcher source checkout.
---

# Auditable episode (offline, deterministic, portable)

Reproduces the Society **audit chain** — seal → adjudicate → emit — with zero external dependencies:
no Neo4j, no network, no cluster, no bundled governed data. It is a portable proof that the
ordering holds (commit-before-observe) and that the emitted bundle actually carries the sealed card
plus the deterministic verdict.

## When to use
- Show the commit-before-observe audit chain end to end **anywhere**, offline (laptop, CI, a fresh
  clone) — a true signal is `supported_within_scope` + score banked, a null is `rejected` + score
  **withheld**.
- Smoke-test after touching `society/` sealing (`lock_commitment`), the `permutation_null` gate, or
  `services/review/audit_bundle.py`, without standing up Neo4j or the cluster.
- Hand someone a minimal, PII-free reproducer of "how does BR seal and audit a claim?".
- **NOT for** a real scientific result. The signal is a toy in-memory fixture. For a real governed
  analysis on real data, use the project-specific governed workflow for that dataset and keep it
  separate from this portable demo.

## Honest scope (one caveat is load-bearing)
- The **fully-offline, reproducible-anywhere guarantee covers ONLY the deterministic
  `permutation_null` battery** — it is pure seeded numpy (`compute_permutation_null_probe`, `seed=0`)
  so the null p is bit-identical on any machine. That is the adjudicator of *effect reality*
  (supported vs withheld), and it is what survival-gates the score.
- The `neuroclaim_compile` step runs offline too, but on the **NiMARE** coordinate backend over a
  tiny in-memory synthetic corpus. **An offline nimare verdict ≠ the online `kg_verify` verdict.**
  It is offline-but-version-sensitive (depends on nimare/nilearn) and is recorded as *complementary
  literature-convergence evidence only*, with its `backend`+`profile` provenance and an explicit
  caveat in the claim card and the evidence file. It does **not** survival-gate the score.

## Prerequisites
1. **A BR src checkout** off `origin/master` (a worktree is fine). Pass `--br-src <root>` or set
   `PYTHONPATH=<root>/src`. `preflight.py` import-checks every enabling primitive and REFUSES on
   version skew (see Gotchas).
2. **conda env `brain_researcher`** with `numpy`, `nimare`, `nilearn`. Preflight refuses if the
   offline NiMARE backend is not importable (otherwise `neuroclaim_compile` would silently fall
   back to the online KG backend and the "offline" claim would be a lie).
3. No Neo4j, no Gemini key, no data downloads. The runner sets `USE_GEMINI_CLI=false` and
   `BR_NEUROCLAIM_BACKEND=nimare`.

## Run
```bash
conda activate brain_researcher
cd /path/to/brain-researcher-agent-kit

# both fixtures (true -> supported+banked, null -> rejected+withheld) + reference self-check
PYTHONPATH=/path/to/br/src python skills/auditable-episode/scripts/run_episode.py

# one component only
PYTHONPATH=/path/to/br/src python skills/auditable-episode/scripts/run_episode.py --component true
PYTHONPATH=/path/to/br/src python skills/auditable-episode/scripts/run_episode.py --component null

# let the runner wire the checkout onto sys.path for you
python skills/auditable-episode/scripts/run_episode.py --br-src /path/to/br@master
```

## Expected output
```
PREFLIGHT OK — all enabling primitives import and the offline NiMARE backend is present.

[auditable-episode] component=true status=supported_within_scope banked=0.489 \
  perm(r=0.489 p=0.0005 refuted=False) offline_nimare=supported_within_scope(nimare) hash=0fcd70fa6e40
[auditable-episode] component=null status=rejected WITHHELD \
  perm(r=-0.035 p=0.6477 refuted=True) offline_nimare=unresolved(nimare) hash=7720d5123461

reference self-check OK — true=supported+banked, null=rejected+withheld
```
`score=WITHHELD` on the null is the point: a committed HARD axis (`permutation_null`) refuted it, so
the survival-gated score is withheld. The permutation p is reproducible byte-for-byte anywhere.

## How it works
- `scripts/preflight.py` — import-checks the REAL primitives (`neuroclaim_compile`,
  `commit_and_adjudicate_claim`, `lock_commitment`, `compute_permutation_null_probe`,
  `derive_default_battery` OR `compile_required_battery`, `persist_audit_bundle` OR
  `export_audit_bundle`, `NimareBackend`, the `DETERMINISTIC_GATES` dispatcher) and asserts
  `nimare`+`nilearn` import. Any miss ⇒ nonzero exit with a fix hint. (The audit symbol is
  `persist_audit_bundle`/`export_audit_bundle` — there is no `emit_audit_bundle`.)
- `scripts/controller.py` — the orchestration, in this exact order: (1) build the claim + its
  committed `permutation_null` battery via `derive_default_battery` (refuse if it comes back empty —
  version-skew guard); (2) **seal** with `lock_commitment` and assert `verify_hash()` **before
  emitting anything**; (3) write the sealed card to `society/commitment_card.json` (first write);
  (4) run the deterministic `permutation_null` battery + the offline `neuroclaim_compile`
  (asserting `evidence_verdict.backend == "nimare"` — proof it did not fall back to KG); (5) write
  the claim card (survival-gated on the permutation battery) + a **redacted** evidence file;
  (6) emit via `persist_audit_bundle`, then **re-open the bundle and assert** it contains the sealed
  card (hash unchanged), the `permutation_null` verdict, and no leaked PII.
- `scripts/run_episode.py` — two tiny in-memory fixtures (PII-free by construction), fresh
  `run_dir` per component, forces the offline env, runs the reference self-check.

## Honesty / invariants (what makes this a real audit, not theater)
- **Commit before observe.** The card is sealed and `verify_hash()`-checked *before* the compile or
  battery runs. Nothing is emitted from an unverifiable card.
- **Never backfill a sealed card.** The controller refuses if `society/commitment_card.json` already
  exists; the runner uses a fresh `run_dir` each time.
- **Assert the mechanism fired.** The bundle is re-read from disk and its sealed hash, the
  permutation verdict, and PII-absence are asserted — not trusted from a log line. Silent
  degradation into a plausible-wrong "success" is this project's #1 trap.
- **No silent KG fallback.** The NiMARE backend is passed as an instance and `available()` is
  asserted; `on_evidence_unavailable="error"` means an unreachable backend raises rather than
  laundering a verdict.
- **Redaction is tested, not claimed.** `_redaction_self_test()` injects a PII canary and asserts
  the scrub removes it before the real evidence is written; the permutation probe stores an
  `inputs_fingerprint`, never the raw per-subject arrays.

## Gotchas
- **Version skew is silent.** A carved/old checkout can be missing a primitive or ship a toothless
  `derive_default_battery` (→ empty battery). Preflight import-checks each symbol; the controller
  also refuses a battery whose axes ≠ `["permutation_null"]`. Run from a worktree off
  `origin/master`.
- **`nimare`/`nilearn` absent ⇒ REFUSE, don't degrade.** Without them the KG fallback would fire.
  Preflight blocks this.
- The synthetic-corpus reverse inference emits benign `RuntimeWarning: invalid value encountered in
  divide` from `nimare.mkda` (zero-denominator voxels); the runner filters warnings. The verdict is
  unaffected.
