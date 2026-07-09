#!/usr/bin/env python3
"""Prepare local HCP/A1 inputs for the auditable-episode runner.

This script does not redistribute or bypass HCP data access. It assumes the user has
already staged the HCP-YA behavioral table and the Liu/Tian component table under the
appropriate Data Use Terms, then converts those local files into the small
``auditable_episode_inputs.npz`` + ``auditable_episode_manifest.json`` contract consumed by
``run_episode.py --data-dir``.

For a scientific A1 rerun, pass subject-level out-of-sample predictions via
``--predictions-csv``. Without predictions, the script refuses unless
``--allow-planted-demo`` is set, because a planted positive-control vector is an audit-plumbing
demo, not evidence for the HCP claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

COMPONENT_COLS = [
    "ICA_Cognition",
    "ICA_TobaccoUse",
    "ICA_PersonalityEmotion",
    "ICA_IllicitDrugUse",
    "ICA_MentalHealth",
]
IQ_COLS = ["PMAT24_A_CR", "ListSort_Unadj", "ReadEng_Unadj"]
PREDICTION_CANDIDATES = [
    "pred_ICA_Cognition",
    "ICA_Cognition_pred",
    "prediction",
    "y_pred",
    "pred",
]
FOLD_CANDIDATES = ["fold_id", "fold", "cv_fold"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_record(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "name": path.name,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _zscore(values: Any):
    import numpy as np

    arr = np.asarray(values, dtype=float)
    sd = float(arr.std())
    if sd == 0.0:
        raise ValueError("cannot z-score a constant vector")
    return (arr - float(arr.mean())) / sd


def _orthogonal_null(y: Any, seed: int):
    import numpy as np

    rng = np.random.default_rng(seed)
    y = _zscore(y)
    raw = rng.standard_normal(len(y))
    raw = raw - (float(raw @ y) / float(y @ y)) * y
    return _zscore(raw)


def _autodetect(columns: list[str], candidates: list[str], label: str) -> str:
    for col in candidates:
        if col in columns:
            return col
    raise ValueError(
        f"Could not detect {label}; pass it explicitly. Available columns: {columns}"
    )


def _load_fold_ids(fold_manifest: Path, n_rows: int):
    import numpy as np

    payload = json.loads(fold_manifest.read_text(encoding="utf-8"))
    folds = payload.get("folds")
    if not isinstance(folds, list):
        raise ValueError(f"{fold_manifest} has no list-valued 'folds' field")

    fold_ids = np.full(n_rows, -1, dtype=int)
    for pos, entry in enumerate(folds):
        fold_id = int(entry.get("fold_id", pos))
        for idx in entry.get("test_indices", []):
            idx = int(idx)
            if idx < 0 or idx >= n_rows:
                raise ValueError(f"fold test index {idx} outside 0..{n_rows - 1}")
            if fold_ids[idx] != -1:
                raise ValueError(f"row index {idx} assigned to multiple folds")
            fold_ids[idx] = fold_id
    missing = np.where(fold_ids < 0)[0]
    if missing.size:
        raise ValueError(
            "fold manifest did not assign "
            f"{missing.size} rows, first missing index={int(missing[0])}"
        )
    return fold_ids


def _build_residualized_target(
    behavior_csv: Path, hcp_subjects_csv: Path, subject_col: str
):
    import numpy as np
    import pandas as pd

    behavior = pd.read_csv(behavior_csv)
    hcp = pd.read_csv(hcp_subjects_csv)
    required_behavior = [subject_col, *COMPONENT_COLS]
    missing = [c for c in required_behavior if c not in behavior.columns]
    if missing:
        raise ValueError(f"{behavior_csv} missing columns: {missing}")
    required_hcp = [subject_col, *IQ_COLS]
    missing = [c for c in required_hcp if c not in hcp.columns]
    if missing:
        raise ValueError(f"{hcp_subjects_csv} missing columns: {missing}")

    merged = behavior.merge(hcp[required_hcp], on=subject_col, how="left")
    if len(merged) != len(behavior):
        raise ValueError(
            f"merge changed row count: behavior={len(behavior)} merged={len(merged)}"
        )

    iq_missing = {c: int(merged[c].isna().sum()) for c in IQ_COLS}
    iq_means = {c: float(merged[c].mean(skipna=True)) for c in IQ_COLS}
    for col in IQ_COLS:
        merged[col] = merged[col].fillna(iq_means[col])

    y = merged["ICA_Cognition"].to_numpy(dtype=float)
    x = np.column_stack(
        [
            np.ones(len(merged)),
            merged["PMAT24_A_CR"].to_numpy(dtype=float),
            merged["ListSort_Unadj"].to_numpy(dtype=float),
            merged["ReadEng_Unadj"].to_numpy(dtype=float),
        ]
    )
    beta, *_ = np.linalg.lstsq(x, y, rcond=None)
    y_hat = x @ beta
    resid = y - y_hat
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    out = behavior.copy()
    out["ICA_Cognition"] = resid
    provenance = {
        "ols_formula": "ICA_Cognition ~ 1 + PMAT24_A_CR + ListSort_Unadj + ReadEng_Unadj",
        "iq_columns": IQ_COLS,
        "iq_missing_count": iq_missing,
        "iq_imputation": "fill with full-sample mean of present values",
        "iq_means": iq_means,
        "ols_betas": {
            "Intercept": float(beta[0]),
            "PMAT24_A_CR": float(beta[1]),
            "ListSort_Unadj": float(beta[2]),
            "ReadEng_Unadj": float(beta[3]),
        },
        "r2_explained_by_iq": r2,
        "residual_mean": float(resid.mean()),
        "residual_std": float(resid.std(ddof=0)),
    }
    return out, provenance


def _load_target(args: argparse.Namespace):
    import pandas as pd

    if args.target_csv:
        target_path = Path(args.target_csv).expanduser().resolve()
        target = pd.read_csv(target_path)
        missing = [
            c
            for c in [args.subject_column, "ICA_Cognition"]
            if c not in target.columns
        ]
        if missing:
            raise ValueError(f"{target_path} missing columns: {missing}")
        provenance = {"target_source": "precomputed residualized target CSV"}
        source_records = [_file_record(target_path, "residualized_target_csv")]
        return target, provenance, source_records

    if not args.liu_behavior_csv or not args.hcp_subjects_csv:
        raise ValueError(
            "Either pass --target-csv, or pass both --liu-behavior-csv and --hcp-subjects-csv"
        )
    behavior_path = Path(args.liu_behavior_csv).expanduser().resolve()
    hcp_path = Path(args.hcp_subjects_csv).expanduser().resolve()
    target, provenance = _build_residualized_target(
        behavior_path, hcp_path, args.subject_column
    )
    source_records = [
        _file_record(behavior_path, "liu_tian_component_behavior_csv"),
        _file_record(hcp_path, "hcp_ya_behavioral_csv"),
    ]
    return target, provenance, source_records


def _load_predictions(args: argparse.Namespace, target):
    import numpy as np
    import pandas as pd

    pred_path = Path(args.predictions_csv).expanduser().resolve()
    preds = pd.read_csv(pred_path)
    if args.subject_column not in preds.columns:
        raise ValueError(f"{pred_path} missing subject column {args.subject_column!r}")
    pred_col = args.prediction_column or _autodetect(
        list(preds.columns), PREDICTION_CANDIDATES, "prediction column"
    )
    if pred_col not in preds.columns:
        raise ValueError(f"{pred_path} missing prediction column {pred_col!r}")
    merged = target[[args.subject_column, "ICA_Cognition"]].merge(
        preds[
            [
                args.subject_column,
                pred_col,
                *[c for c in FOLD_CANDIDATES if c in preds.columns],
            ]
        ],
        on=args.subject_column,
        how="left",
        validate="one_to_one",
    )
    if merged[pred_col].isna().any():
        missing = int(merged[pred_col].isna().sum())
        raise ValueError(f"{missing} target rows had no prediction in {pred_path}")
    y_pred = merged[pred_col].to_numpy(dtype=float)
    if not np.all(np.isfinite(y_pred)):
        raise ValueError("prediction column contains non-finite values")
    fold_ids = None
    fold_col = args.fold_column
    if fold_col is None:
        fold_cols = [c for c in FOLD_CANDIDATES if c in merged.columns]
        fold_col = fold_cols[0] if fold_cols else None
    if fold_col:
        fold_ids = merged[fold_col].to_numpy(dtype=int)
    return y_pred, fold_ids, _file_record(pred_path, "subject_level_predictions_csv"), pred_col


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--output-dir", required=True, help="where to write local audit inputs")
    ap.add_argument("--target-csv", help="precomputed residualized target CSV")
    ap.add_argument("--liu-behavior-csv", help="paper-derived Liu/Tian component behavior CSV")
    ap.add_argument("--hcp-subjects-csv", help="HCP-YA behavioral subject CSV staged under DUA")
    ap.add_argument("--predictions-csv", help="subject-level out-of-sample predictions CSV")
    ap.add_argument("--prediction-column", help="prediction column in --predictions-csv")
    ap.add_argument("--fold-manifest", help="A1 fold manifest JSON with folds[].test_indices")
    ap.add_argument("--fold-column", help="fold column in --predictions-csv, if no manifest")
    ap.add_argument("--subject-column", default="Subject")
    ap.add_argument("--expected-n", type=int, default=326)
    ap.add_argument(
        "--allow-planted-demo",
        action="store_true",
        help=(
            "if no predictions CSV is available, create a planted positive control from the "
            "HCP-derived target; this is audit plumbing only, not scientific evidence"
        ),
    )
    args = ap.parse_args()

    try:
        import numpy as np
        import pandas as pd  # noqa: F401
    except Exception as exc:
        raise SystemExit(
            "Missing dependencies. Run inside the BR brain_researcher conda env with "
            f"numpy and pandas installed. Import error: {exc}"
        ) from exc

    out = Path(args.output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    target, target_provenance, source_records = _load_target(args)
    if args.expected_n and len(target) != args.expected_n:
        raise SystemExit(
            f"target has {len(target)} rows, expected {args.expected_n}; "
            "override with --expected-n 0"
        )

    y_true = target["ICA_Cognition"].to_numpy(dtype=float)
    if not np.all(np.isfinite(y_true)):
        raise SystemExit("target ICA_Cognition contains non-finite values")

    prediction_source = "subject_level_predictions"
    pred_col = None
    fold_ids = None
    if args.predictions_csv:
        y_pred, pred_fold_ids, pred_record, pred_col = _load_predictions(args, target)
        source_records.append(pred_record)
        fold_ids = pred_fold_ids
    elif args.allow_planted_demo:
        seed_material = "".join(record["sha256"][:12] for record in source_records)
        seed = int(hashlib.sha256(seed_material.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        y_pred = _zscore(_zscore(y_true) + 0.05 * rng.standard_normal(len(y_true)))
        prediction_source = "planted_positive_control_from_hcp_target"
    else:
        raise SystemExit(
            "--predictions-csv is required for a scientific A1 audit input. Use "
            "--allow-planted-demo only for a local-data audit-plumbing demo."
        )

    if args.fold_manifest:
        fold_path = Path(args.fold_manifest).expanduser().resolve()
        fold_ids = _load_fold_ids(fold_path, len(y_true))
        source_records.append(_file_record(fold_path, "a1_fold_manifest"))
    elif fold_ids is None:
        if not args.allow_planted_demo:
            raise SystemExit(
                "Pass --fold-manifest or a fold column in --predictions-csv so fold-aware "
                "permutation checks match the A1 run."
            )
        fold_ids = np.arange(len(y_true), dtype=int) % 5

    null_seed_material = "".join(record["sha256"][:12] for record in source_records)
    null_seed = int(hashlib.sha256(null_seed_material.encode("utf-8")).hexdigest()[:8], 16)
    null_y_pred = _orthogonal_null(y_true, seed=null_seed)

    npz_path = out / "auditable_episode_inputs.npz"
    np.savez(
        npz_path,
        true_y_true=y_true,
        true_y_pred=y_pred,
        true_fold_ids=fold_ids,
        null_y_true=y_true,
        null_y_pred=null_y_pred,
        null_fold_ids=fold_ids,
    )

    target_values_path = out / "hcp_a1_target_values.csv"
    target_values = pd.DataFrame(
        {
            "row_index": np.arange(len(y_true), dtype=int),
            "y_true_ica_cognition_residual": y_true,
            "y_pred": y_pred,
            "fold_id": fold_ids,
        }
    )
    target_values.to_csv(target_values_path, index=False)

    manifest = {
        "schema_version": "auditable-episode-local-data-v1",
        "dataset": "HCP-YA A1 intelligence-residualized Cognition",
        "source_dataset": "Human Connectome Project Young Adult behavioral data",
        "source_access": (
            "User-staged local HCP data under HCP Data Use Terms. This repository does not "
            "redistribute HCP subject data or credentials."
        ),
        "paper_source": {
            "primary_case": (
                "BR bounded autoresearch A1 over HCP-YA / Liu-Tian behavioral components"
            ),
            "methods_context": (
                "Benchmarking FC methods using five ICA-derived HCP behavioral components"
            ),
            "url": "https://www.nature.com/articles/s41592-025-02704-4",
        },
        "download_or_staging_routes": [
            {
                "name": "HCP ConnectomeDB access instructions",
                "url": (
                    "https://wiki.humanconnectome.org/docs/"
                    "How%20to%20Access%20Data%20on%20ConnectomeDB.html"
                ),
                "note": (
                    "Create/log into an HCP account and accept the applicable HCP "
                    "data-use terms before downloading behavioral data."
                ),
            },
            {
                "name": "HCP-YA 2025 ConnectomeDB/BALSA release note",
                "url": (
                    "https://www.humanconnectome.org/study/hcp-young-adult/"
                    "article/updated-hcp-young-adult-data-released-connectomedb-powered-balsa"
                ),
                "note": (
                    "Current HCP-YA portal path; non-imaging data are unchanged from "
                    "S1200 where applicable."
                ),
            },
            {
                "name": "HCP on AWS Open Data Registry",
                "url": "https://registry.opendata.aws/hcp-openaccess/",
                "note": "Cloud route for open-access HCP-YA objects; HCP DUA still applies.",
            },
        ],
        "sample_size": int(len(y_true)),
        "target_construction": target_provenance,
        "prediction_source": prediction_source,
        "prediction_column": pred_col,
        "privacy": {
            "raw_hcp_subject_rows_exported": False,
            "subject_identifiers_exported": False,
            "audit_npz_contains_subject_ids": False,
            "local_source_files_remain_user_controlled": True,
        },
        "local_inputs": {
            "npz": npz_path.name,
            "npz_sha256": _sha256(npz_path),
            "target_values_csv": target_values_path.name,
            "target_values_sha256": _sha256(target_values_path),
        },
        "source_files": source_records,
        "components": {
            "true": {
                "claim_text": (
                    "HCP-YA A1 intelligence-residualized Cognition prediction reproduces "
                    "out-of-sample above-zero association under the local staged inputs"
                ),
                "construction": (
                    "y_true is ICA_Cognition residualized against PMAT24_A_CR, "
                    "ListSort_Unadj, and ReadEng_Unadj. y_pred comes from subject-level "
                    "out-of-sample predictions when --predictions-csv is provided; if "
                    "--allow-planted-demo was used, this is only a planted audit-plumbing "
                    "positive control."
                ),
            },
            "null": {
                "claim_text": (
                    "HCP-YA A1 local-data negative-control prediction reproduces "
                    "out-of-sample above-zero association"
                ),
                "construction": (
                    "y_pred is a deterministic vector orthogonalized against the same "
                    "HCP-derived y_true from a seed derived from source-file hashes."
                ),
            },
        },
    }
    manifest_path = out / "auditable_episode_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Wrote HCP/A1 auditable-episode inputs to: {out}")
    print(f"  manifest: {manifest_path}")
    print(f"  arrays:   {npz_path}")
    print("\nRun the full audit chain against these local files with:")
    print(
        "  PYTHONPATH=/path/to/brain_researcher/src "
        "python skills/auditable-episode/scripts/run_episode.py "
        f"--data-dir {out} --br-src /path/to/brain_researcher"
    )
    if prediction_source != "subject_level_predictions":
        print(
            "\nWARNING: --allow-planted-demo was used. This proves local-data audit plumbing, "
            "not the A1 scientific result.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
