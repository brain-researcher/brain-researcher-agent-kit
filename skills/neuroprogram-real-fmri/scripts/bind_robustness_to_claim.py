#!/usr/bin/env python3
"""Reduce fitlins z-maps to a robustness profile and bind it into a claim."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn.image import load_img, resample_to_img


def build_summary(
    stage: str,
    variants: list[str],
    contrast: str,
    session: str | None,
    atlas_path: str,
    z_thr: float,
) -> tuple[pd.DataFrame, dict[str, float]]:
    seg = f"ses-{session}/" if session else ""
    label = f"ses-{session}_" if session else ""
    rows: list[dict[str, object]] = []
    means: dict[str, float] = {}

    for variant_id in variants:
        expected = (
            f"{stage}/out_{variant_id}/node-dataLevel/{seg}"
            f"{label}contrast-{contrast}_stat-z_statmap.nii.gz"
        )
        found = glob.glob(expected) or glob.glob(
            f"{stage}/out_{variant_id}/**/*contrast-{contrast}_stat-z_statmap.nii.gz",
            recursive=True,
        )
        if not found:
            raise SystemExit(f"missing z-map for variant {variant_id}: {expected}")

        zimg = load_img(found[0])
        z = zimg.get_fdata()
        atlas = resample_to_img(
            atlas_path,
            zimg,
            interpolation="nearest",
            force_resample=True,
            copy_header=True,
        )
        labels = np.asarray(atlas.get_fdata()).astype(int)
        means[variant_id] = float(np.nanmean(z[np.isfinite(z) & (z != 0)]))

        for label_id in np.unique(labels):
            if label_id == 0:
                continue
            mask = (labels == label_id) & np.isfinite(z)
            if not mask.any():
                continue
            vals = z[mask]
            rows.append(
                {
                    "model_id": "multiverse",
                    "variant_id": variant_id,
                    "contrast": contrast,
                    "metric": "mean_z",
                    "region_id": str(int(label_id)),
                    "value": float(np.mean(vals)),
                    "pct_active": float(np.mean(vals > z_thr)),
                    "z_thr": z_thr,
                }
            )

    return pd.DataFrame(rows), means


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", default=None)
    parser.add_argument("--contrast", required=True)
    parser.add_argument("--atlas", required=True)
    parser.add_argument("--variants", nargs="+", default=["mv01", "mvB", "mvC"])
    parser.add_argument("--session", default="test")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--program-report")
    parser.add_argument("--claim-text", default="The target contrast is robust across pipelines")
    parser.add_argument("--z-thr", type=float, default=2.3)
    args = parser.parse_args()

    stage = args.stage or str(Path.cwd() / ".br_runs" / "neuroprogram_fitlins")
    summary_df, means = build_summary(
        stage,
        args.variants,
        args.contrast,
        args.session,
        args.atlas,
        args.z_thr,
    )
    print(
        f"summary_df: {len(summary_df)} rows "
        f"({summary_df.variant_id.nunique()} variants x "
        f"{summary_df.region_id.nunique()} parcels)"
    )
    print("whole-brain mean z per variant:", {k: round(v, 4) for k, v in means.items()})

    from brain_researcher.autoresearch.society.cards import (
        ClaimSpecV1,
        ScopeBoundaryV1,
        lock_commitment,
    )
    from brain_researcher.autoresearch.society.conductor import synthesize_claim_card
    from brain_researcher.autoresearch.society.falsifiers import FalsifierOutcome
    from brain_researcher.autoresearch.society.multiverse import (
        MultiverseProfile,
        multiverse_ceiling,
    )
    from brain_researcher.autoresearch.society.neuroprogram import NeuroProgramReportV1
    from brain_researcher.autoresearch.state_contract import StopArtifact
    from brain_researcher.core.analysis.multiverse_robustness_report import (
        build_multiverse_robustness_report,
    )

    report = build_multiverse_robustness_report(
        summary_df,
        contrast=args.contrast,
        metric="mean_z",
    )
    report.setdefault("input", {})["contrast"] = args.contrast
    profile = MultiverseProfile.from_robustness_report(report, run_id=args.run_id)
    print("MultiverseProfile:", profile.model_dump())
    print("multiverse_ceiling:", multiverse_ceiling(profile).model_dump())

    program_report = None
    if args.program_report:
        with open(args.program_report, encoding="utf-8") as handle:
            raw_report = json.load(handle)
        program_report = NeuroProgramReportV1(
            **{k: v for k, v in raw_report.items() if k != "ok"}
        )

    claim = ClaimSpecV1(
        claim_id="C",
        claim_text=args.claim_text,
        scope_boundary=ScopeBoundaryV1(modality="fMRI"),
        allowed_alternatives=["confound"],
        failure_criteria="sign flips",
        confirmatory=True,
        extra={"contrast": args.contrast},
    )
    commitment = lock_commitment(claim, ["gsr"], {"gsr": {"path": "x", "hash": "h"}})
    stop = StopArtifact(
        line_id="l",
        session_id="s",
        final_status="completed",
        stop_reason="completed",
        total_cycles=1,
        stall_count=0,
        elapsed_seconds=1.0,
        last_score=0.8,
        scorer_name="x",
        last_scorer_payload_path=None,
    )
    survivor = FalsifierOutcome(
        strategy="gsr",
        refuted=False,
        degenerate=False,
        judgment_passed=True,
        completeness_passed=True,
        decision="proceed",
        summary="ok",
        reasons=(),
        required_actions=(),
        rubric_ref="x",
        hard=False,
    )
    card = synthesize_claim_card(
        claim,
        commitment,
        stop,
        [survivor],
        multiverse_profiles=[profile],
        multiverse_run_id=args.run_id,
        neuroprogram_report=program_report,
    )
    calibration = card.extra["calibration"]
    out = Path(stage) / "robustness_bound_claim.json"
    out.write_text(
        json.dumps(
            {
                "profile": profile.model_dump(),
                "card_status": card.status.value,
                "binding": calibration["multiverse_binding_status"],
                "zmap_means": means,
            },
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    print("FINAL card.status:", card.status.value)
    print("multiverse_binding_status:", calibration["multiverse_binding_status"])
    print("saved:", out)


if __name__ == "__main__":
    main()
