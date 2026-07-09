---
name: tb-science-task-authoring
description: Author or harden a terminal-bench-science / Harbor benchmark task from a scientific paper (neuroimaging-focused). Covers choosing reproduction vs rigor genre, the empirical difficulty ladder that actually defeats frontier agents, the choice-dependence lever for making a reproduction hard (un-cued GSR/band-pass/ROI sensitivity), the no-fake-traps rule, writing a human-looking + schema-robust verifier, and oracle/agent calibration with hand re-scoring. Use when converting a paper into a tb-science/Harbor task, when a task "isn't hard enough", or when a verifier looks machine-generated.
---

# Authoring hard tb-science (Harbor) tasks from papers

Hard-won playbook. **Core principle: difficulty comes from the science and the data, not from elaborate scoring.** A weighted multi-layer rubric with regex-scored claims is both *easy to defeat* and *obviously machine-generated*.

## When to use
- Converting a neuroimaging paper into a tb-science / Harbor benchmark task.
- A task "isn't hard enough" — frontier agents pass it; you need the difficulty ladder + choice-dependence lever.
- A verifier looks machine-generated (weighted rubric / artifact-contract trio) and needs a human-looking, schema-robust rewrite.
- NOT for: running an existing task (that's Harbor CLI); non-benchmark reproduction (use `neuroprogram-real-fmri`).

Worked examples in this repo (`benchmarks/tb-science-task/`), a measured difficulty ladder:
- **`GRADIENT-001`** — un-cued *characterise the principal gradient* → both GPT-5.5 xhigh & Claude Opus 4.8 overclaim a single identity → **FAIL** (hard).
- *easy control (measured during dev, not shipped)* — clean reproduction of Richardson 2018's within-network result, pipeline fully pinned → both compute it and report honestly → **PASS**. This is the baseline that proves the difficulty below is the un-cued choice, not reproduction itself.
- **`SOCIALBRAIN-001`** — reproduce Richardson's headline anti-correlation, but it only holds under GSR (an un-cued, contested choice) → both run one default pipeline and give a flat verdict → **FAIL** (hard reproduction).
- **`DEVCONN-001`** — reproduce the developmental local-to-distributed connectivity result; children move ~2× more, so it's a head-motion confound (collapses under motion control) → agents compute it, none volunteer the motion check → **FAIL** (GPT-5.5 4/4, Claude 3/3; the *wrong-cause* axis).

## Step 0 — Validate the result reproduces BEFORE building anything

The single most important gate. **Never assume the paper's headline reproduces on data you can actually get.**
- Empirically run the paper's method on the accessible cohort first (a throwaway script).
- Example failure: Margulies-2016 "G1 = DMN-apex" is **HCP-specific** and does NOT reproduce on `nilearn.fetch_development_fmri` (ds000228); the apex network even flips across band-pass/subsample choices. Only discovered by running it.

Three outcomes decide the genre:
| reproduces on open data? | do this |
|---|---|
| yes, robustly | **reproduction task** (paper → result) — cleanest |
| needs credentialed data (HCP/UKB) | get the data, or pick another paper |
| fragile / doesn't reproduce | don't fake a reproduction — the **fragility itself** becomes the task (rigor genre) |

## Step 1 — Pick the genre deliberately

| | reproduction (paper→result) | process / rigor |
|---|---|---|
| instruction | condensed methods section | condensed methods section |
| ground truth | the paper's reported number | correct scientific *behaviour* |
| verifier | **one numeric match** (± tolerance) | reads the conclusion and *judges* |
| looks human | natively | needs care (judgement ≠ number) |
| precondition | result must reproduce | none |

Reproduction is cleaner and more authentic — *prefer it*. But note (measured): a clean reproduction of a **robust** result is **not hard** — frontier agents just run the pipeline and report it honestly (measured: an easy fully-pinned control variant, both agents pass). To make a reproduction *hard* without leaving the genre, see the next section — you inject un-cued judgement by choosing a result that is **choice-dependent**, keeping the verifier mostly numeric + one honesty check. Fall back to the pure rigor genre only when the result won't reproduce at all, or you specifically want to test open-ended judgement.

## Step 2 — The difficulty ladder (what actually defeats a frontier agent)

Validated against GPT-5.5 xhigh and Claude Opus 4.8:
1. **Procedural rigor** (alignment, spatial/spin nulls, self-falsification) → **does NOT defeat them**. It's in their priors; ask and they do it. (GPT-5.5 passed a spin-null+self-falsify task at 0.99.)
2. **Condensed-methods underspecification** ("hidden info") → mostly absorbed by priors.
3. **Anti-prior ("the textbook is wrong here")** → only fair if the textbook is *robustly* wrong on the data. If it's merely fragile, a correct pipeline can reproduce the textbook → you'd punish a correct solution. Usually **not gateable**.
4. **Un-cued volunteered behaviour** → **this defeated both frontier models.** Without being told, do they spontaneously check robustness / volunteer skepticism / refuse to overclaim?
   - GPT-5.5: ran one pipeline, asserted one confident identity, checked nothing.
   - Claude: did a bootstrap *robustness ritual* but on the wrong axis (within-pipeline resampling, not across analytic choices) → false reassurance, still overclaimed.
   - **The cue is load-bearing: cued, they do it right; un-cued, they don't.** The frontier gap is metacognitive, not compute.

**Takeaway: to make it hard, don't add more rigor requirements — test what the agent won't do unprompted.**

Note the failure is symmetric: agents are confidently wrong in *either* direction. On `SOCIALBRAIN-001` both flatly concluded "doesn't reproduce" — a confident *refutation* that missed the result reproduces under a choice they never tried. Under- and over-claiming are the same un-cued-judgement gap.

**The un-cued failure axes — the design space.** Each axis = a check a careful scientist
volunteers and the agent, un-cued, does not. The three we've shipped are just the *named*
ones; the space is much larger. Grouped by **what the agent fails to question** — pick one
per task, and ground it in a real, measured pitfall (Step 0):

**A · the result's robustness** — does it hold across defensible analytic choices?
- **Over-claim an identity** — asserts one confident answer, checks nothing. (`GRADIENT-001` ✓ — each model asserts a *different* single gradient identity; the divergence is the fragility.)
- **Confident refutation** — a null hides a result that appears under one un-cued choice; the agent runs one default pipeline and flatly says "doesn't reproduce". (`SOCIALBRAIN-001` ✓ — the GSR lever.)
- **Point-estimate, no multiverse** — reports one number, never the spec-curve / vibration of effects (Steegen 2016; garden of forking paths). *candidate.*

**B · the cause** — is it the effect I think, or an artifact?
- **Wrong-cause confound** — reproduces an effect, never checks a confound. (`DEVCONN-001` ✓ — a developmental effect that is really head motion (Power 2012); a Claude run even volunteered a *different* caveat but still missed the true cause.) Same machinery, other levers: physiological noise (respiration/cardiac aliasing), site/scanner batch (ComBat), temporal band-pass. *candidates.*
- **Reverse inference** — infers a cognitive process from an activation without the base rate (Poldrack 2006). *candidate.*
- **Correlation → causation / direction** — treats connectivity or activation as directed influence or necessity. *candidate.*

**C · the statistical inference**
- **Circularity / double-dipping / leakage** — selects on the same data it tests, or a predictor with subject/site leakage inflating accuracy (Kriegeskorte 2009). *candidate (Lane D).*
- **Multiple comparisons / cluster inflation** — reports a blob uncorrected (Eklund 2016, ~60% false positives). *candidate.*
- **Significance ≠ effect size** — with large n everything is "significant"; reports p, not magnitude/CI. *candidate.*
- **Power / small-sample instability** — a headline from n≈15 reported as fact. *candidate.*
- **Aggregation fallacy** — a group-level correlation is asserted of individuals (Simpson's paradox). *candidate.*

**D · the data / sample**
- **Selection / regression to the mean** — top-responders selected, then "decline". *candidate.*
- **Over-generalization** — the result is dataset-specific and doesn't transfer (e.g. HCP-specific gradients — we hit exactly this; validate transfer before gating). *candidate.*

Rules across all of them: (1) each axis still needs its own **Step 0** — the pitfall must
produce a *real measured signal on your data* before you gate on it (no-fake-traps); (2) a
task already covering one axis is **not** made harder by piling on rigor — reach for a
*different* axis; (3) vary **axis × dataset × modality** across the suite (Suite-level design).

## Step 2.5 — Make a *reproduction* hard: the choice-dependence lever

This is how to get a task that is **authentic + human-looking (reproduction) AND hard**, instead of falling back to the rigor genre.

Pick a famous result whose reproduction **hinges on one defensible-but-contested analytic choice** — the classic neuroimaging levers: **global-signal regression (GSR)** (induces anti-correlations), **temporal band-pass**, **ROI/parcellation definition**, GLM/HRF or motion-scrubbing options. Then:
1. **Pin everything except that one lever** (e.g. pin the ROIs), and leave the lever to the analyst.
2. Keep the instruction **un-cued** — name the result to reproduce, never mention the lever, robustness, or sensitivity.
3. The honest answer must *discover and report the choice-dependence*; an agent that runs one default pipeline gets a flat yes/no and **fails**.

**Step 0 for the lever (mandatory — it's the no-fake-traps rule):** prove the lever actually flips the result before building. Worked example (`SOCIALBRAIN-001`): Richardson's ToM–pain anti-correlation is `r_s=−0.07` (n.s.) with a standard clean but `r_s=−0.34` (≈ the paper's −0.35) once GSR is added. Real, dramatic, and GSR is a genuine decade-long controversy — so the trap is fair: a mature reproduction *should* check it. Verifier then stays mostly numeric (connectivity computed) + one honesty check (does `findings.md` link the lever to the result — see Step 5 for the false-positive trap in writing that check).

## Step 3 — Never fake a trap

Every difficulty/trap must produce a **real measured signal on the data**. Validate each one before writing the verifier around it.
- Kept: alignment necessity (unaligned r≈0 vs aligned r≈0.68); apex fragility (apex flips across configs).
- Dropped as noise: template circularity (inflation 0.010); parcel-coverage (0/20 subjects ever incomplete).
- If a candidate trap isn't real, fold it in honestly as a *reported self-check*, or drop it — do not gate on it.

## Step 4 — Write a human-looking AND schema-robust verifier

Tells that scream "machine-generated" (avoid):
- weighted multi-layer rubric (`WEIGHTS = {...}`), `score.json`, named regex constants scoring prose;
- an instruction that **describes its own scoring rubric**;
- bespoke artifact contracts (e.g. a `method_route.json`/`claim_support.json`/`artifact_contract_scan.json` trio).

Human version (see `GRADIENT-001/tests/test_outputs.py`):
- a short reviewer-style `pytest` with **plain `assert`s** and a comment stating the ground truth;
- a natural deliverable (`findings.md` write-up + `run_metadata.json`), not a rigor-artifact trio;
- for reproduction tasks, literally `assert abs(result - expected) < tol`.

**Schema robustness is non-negotiable** (it bit us 3×). Agents emit varied output shapes — network labels `"Visual"` vs `"Vis"`; `aligned_signed` as a scalar vs a nested `{pairwise_pearson_mean: ...}` dict. A verifier that hard-codes one shape **fails correct solutions on format, not science**. Canonicalise labels; search any-depth for the number. Always inspect a real agent's captured output (`--artifact /app/output`) to find brittleness.

Honest limit: a rigor-genre verifier still *grades a judgement* (reads the conclusion), so it can't be as clean as a reproduction task's numeric match. That ceiling is intrinsic to the genre — don't pretend otherwise.

## Step 5 — Calibrate with oracle + adversarial + real agent

- **Oracle must pass** (reward 1.0) — the reference solution proves the task is solvable in-container.
- **Shortcuts must fail** — build adversarial outputs (skip the key step / use the wrong method) and confirm the gates bite.
- **Run ≥2 different frontier families** (e.g. GPT-5.5 xhigh *and* Claude Opus), k≥3 each for a firm claim. n=1-per-model is preliminary — agents are stochastic. Read *why* each failed: divergent failure modes are themselves evidence the trap is real, not a verifier quirk. (`GRADIENT-001`: GPT-5.5 checked nothing; Claude ran a bootstrap *robustness ritual on the wrong axis* — within-pipeline resampling, not across analytic choices — and still overclaimed. Both fail, differently, for the same un-cued reason.)
- **Distinguish "did the science wrong" from "formatted output wrong."** A 0.79 fail that's actually a label-string mismatch is NOT a hard task — it's a verifier bug. Inspect before concluding.
- **Re-score the real agent output and read its pass/fail by hand — a green/red light is not enough.** When the verifier grades a prose *insight*, a keyword check will false-pass a write-up that merely *names* the thing. The fix is always the same: **require the insight to be linked to the RESULT**, never a bare keyword, then re-tune the regex against the *actual* agent + adversarial texts until reference passes and every flat/naming answer fails.

  **The recurring false-positive class — a confound/lever word colliding with *pipeline vocabulary* (bit us twice).** The trap words you grade on (`gsr`, `global signal`, `motion`, `confound`, `regress`, `reduced`, `nuisance`) are the *same words agents use to describe their preprocessing*. So a pipeline description false-passes a naming check:
  - `SOCIALBRAIN-001`: check looked for "global signal" → GPT-5.5 passed by writing "**no global signal regression**" (describing its pipeline), never having tested GSR.
  - `DEVCONN-001`: check had a `(confound…)[0,45](motion)` branch and a `reduced`→`regressed`→`motion` chain → Claude passed by writing "fMRIPrep **reduced confounds regressed (motion**, aCompCor, …)" (a nuisance-regressor list), never having checked head motion. It had even volunteered a *different* skeptical caveat (global-amplitude), so it *looked* insightful — the green light was a lie.
  Guards that hold: (1) the trap word must co-occur with a **result token** (the age/group/developmental effect, "reproduce", "anti-correlation") or a **collapse token** ("only with", "no longer significant", "vanishes under control") — proximity to the trap word alone is not enough; (2) **never put pipeline vocabulary in your trigger set** — dropping a bare `reduc\w*` (which matched "reduced confounds") was the actual fix; (3) build the adversarial set *from the real runs*: a passing agent's own pipeline sentence is your hardest negative. A judgement check is only as good as its tuning against real outputs — and the output that looks like a pass is the one to read most carefully.

## Suite-level design — don't build a monoculture

A single hard task is not a benchmark. Across the suite, vary three things independently, or every task exercises the same weakness:
- **failure axis** (over-claim / confident-refutation / wrong-cause — see Step 2);
- **dataset** (all our first tasks sit on `nilearn.fetch_development_fmri`/ds000228 — convenient, but a shared quirk becomes a shared blind spot);
- **modality / method** (resting-state connectivity ≠ task-GLM activation ≠ structural/diffusion ≠ EEG).

When two candidate tasks share all three, the second adds little. Prefer the candidate that opens a *new* axis or a *new* data+modality even if it's more work to validate — e.g. a task-fMRI GLM multiverse (fitlins) breaks the connectivity monoculture, a motion/QC-FC task opens the wrong-cause axis.

## Task layout (Harbor)

```
TASK/
  instruction.md        # condensed methods voice; NO scoring-rubric section
  task.toml             # difficulty, dataset_id, cpus/mem, timeouts, allow_internet
  environment/Dockerfile# pinned deps (verify they actually install+run)
  solution/{solve.sh, compute.py}   # reference; writes the natural deliverable
  tests/{test.sh, test_outputs.py}  # test.sh -> uvx pytest -> reward.txt
```

## Engineering gotchas

- Runtime data download needs `allow_internet=true`; **osf.io throttles/timeouts** after repeated fresh pulls (nilearn's urllib has no socket read-timeout, so a throttled connection hangs *indefinitely* on one file, not just slow). During **development/agent runs**, mount the host cache to skip the download entirely:
  `--mounts-json '[{"type":"bind","source":"/path/to/nilearn_data","target":"/nilearn_data","read_only":true}]' --ae NILEARN_DATA=/nilearn_data` (validated: oracle reward=1, downloads=0). Keep it a **local run flag, never committed** — the shipped task must still fetch at runtime (`allow_internet=true`), and external runners/CI will still hit osf, so flag that reliability caveat in the proposal. The mount removes the ~30-min download but **not** the compute (e.g. GSR's per-subject whole-brain global-signal extraction ≈15 min is irreducible). Highest value on *agent* runs, where an osf hang otherwise burns tokens and wall-clock.
- `--artifact /app/output` drags multi-GB niftis into `/tmp` and can fill the session tmpfs (kills Bash). Only use it when inspecting outputs; clean up after.
- Pin Dockerfile deps to versions you've **actually run** (e.g. `brainspace==0.1.20` verified under `numpy==2.1.3`), not guessed.
- A choice-dependence task may need a heavier reference (e.g. GSR = whole-brain `NiftiMasker` per subject on top of the download) — budget the timeout (`SOCIALBRAIN-001` oracle ≈ 35 min over 155 subjects; `timeout_sec=5400`).
- Harbor agents: `-a oracle` (reference), `-a codex -m gpt-5.5 --ak reasoning_effort=xhigh`, `-a claude-code -m claude-opus-4-8`. The claude-code agent reads auth only from host env (`CLAUDE_CODE_OAUTH_TOKEN`/`ANTHROPIC_API_KEY`) — it does NOT inherit the local `~/.claude` login.

## One-line flow

Pick paper → **verify it reproduces on obtainable data** → if it does, reproduction task (numeric verifier); to make it *hard*, pick a result that hinges on one un-cued choice (GSR/band-pass/ROI) and **validate the lever flips it**; if it doesn't reproduce at all, an un-cued rigor task on the real fragility → validate every trap/lever is real → write a short human-looking, schema-robust verifier → calibrate with oracle + adversarial + a real agent, **re-scoring the real agent output by hand** (and check *why* it passes/fails).

## Related memory
`project_tbscience_gradient_trap_experiments.md` (running Harbor oracle/agent on the GRADIENT task; the un-cued-vs-cued difficulty findings).
