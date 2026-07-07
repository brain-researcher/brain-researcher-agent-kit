# Verification-bench gates (VB-1/2/3) + answer-proof rule

The three gates `claim_commit` + the dispatch path enforce. They exist so that
reward / execution / magnitude alone never accepts a claim.

## The three gates

| Gate | Fires at | Rule |
|---|---|---|
| **VB-1** | finalize | A **required axis with no verdict** blocks finalize. You cannot call a run done while a required falsifier axis is unadjudicated. |
| **VB-2** | ranking / reward | A claim whose **required falsifier refuted it** has its score **withheld** — it cannot win a magnitude ranking. Survival gates the reward. |
| **VB-3** | external dispatch | An **incomplete battery blocks dispatch**. `slurm_submit` reads `{run_dir}/society`; if the required battery isn't complete, the submit is gated. |

## Answer-proof rule (raw arrays only)

Feed `claim_commit` the **raw per-item arrays** (the evidence), never a precomputed
summary like `retained_pct` or a p-value. A precomputed statistic is an
*answer-proof channel*: it lets the caller smuggle the conclusion past the gate. The
adjudicator must compute survival from raw evidence itself.

## Autonomous behavior

- `BR_VB_ADJUDICATE_AUTONOMOUS` governs whether an autonomous run auto-adjudicates
  its claim at the seam. When on, the run commits + adjudicates before the gated
  dispatch without a human in the loop — the gates above still apply.

## What "gated vs bare-magnitude" shows

`run_compare` / `run_scorecard` should demonstrate that the survival-gated winner
differs from the naive top-magnitude candidate — that difference *is* the value of
the bench. If they are identical, say so; if gating demoted the loudest candidate,
report which falsifier refuted it.
