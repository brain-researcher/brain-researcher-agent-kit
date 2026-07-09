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


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().resolve()


def _safe_name(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return Path(value).name


def _mapping_len(value: Any) -> int | None:
    if isinstance(value, (dict, list)):
        return len(value)
    return None


def _summarize_liu_component_provenance(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = _read_json(path)
    local = payload.get("local_projection_summary")
    if not isinstance(local, dict):
        local = {}

    missing_subject_ids = payload.get("missing_subject_ids_from_behavior")
    if not isinstance(missing_subject_ids, list):
        missing_subject_ids = local.get("missing_subject_ids_from_behavior")
    if not isinstance(missing_subject_ids, list):
        missing_subject_ids = []

    subjects_with_missing_items = local.get("subjects_with_missing_items_before_imputation")
    if not isinstance(subjects_with_missing_items, dict):
        subjects_with_missing_items = {}

    supplementary_mapping = payload.get("supplementary_table4_mapping")
    component_mapping = payload.get("component_row_mapping")
    return {
        "manifest_file": _file_record(path, "liu_component_behavior_provenance"),
        "created_from_script_module": payload.get("created_from_script_module"),
        "header_alignment_validated": payload.get("header_alignment_validated"),
        "source_behavior_csv_sha256": payload.get("source_behavior_csv_sha256"),
        "source_demixing_mat_url": payload.get("source_demixing_mat_url"),
        "source_demixing_mat_sha256": payload.get("source_demixing_mat_sha256"),
        "source_supplement_url": payload.get("source_supplement_url"),
        "paper_method_summary": payload.get("paper_method_summary"),
        "caveats": payload.get("caveats"),
        "mapping_counts": {
            "supplementary_table4_items": _mapping_len(supplementary_mapping),
            "component_rows": _mapping_len(component_mapping),
        },
        "local_projection_summary": {
            "source_row_count": local.get("source_row_count"),
            "age_sex_available_row_count": local.get("age_sex_available_row_count"),
            "complete_case_row_count": local.get("complete_case_row_count"),
            "requested_subject_count": local.get("requested_subject_count"),
            "output_row_count": local.get("output_row_count"),
            "subject_selection_mode": local.get("subject_selection_mode"),
            "selected_subject_list_name": _safe_name(local.get("selected_subject_list_path")),
            "continuous_column_count": local.get("continuous_column_count"),
            "continuous_selection_rule": local.get("continuous_selection_rule"),
            "imputed_cell_count": local.get("imputed_cell_count"),
            "raw_imputation_strategy": local.get("raw_imputation_strategy"),
            "residual_imputation_strategy": local.get("residual_imputation_strategy"),
            "missing_behavior_subject_count": len(missing_subject_ids),
            "subjects_with_imputed_items_count": len(subjects_with_missing_items),
        },
        "redaction": {
            "source_paths_exported": False,
            "subject_ids_exported": False,
            "full_column_mapping_exported": False,
        },
    }


def _summarize_liu_target_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = _read_json(path)
    validation = payload.get("validation")
    if not isinstance(validation, dict):
        validation = {}
    return {
        "manifest_file": _file_record(path, "liu_component_target_manifest"),
        "source_paper": payload.get("source_paper"),
        "benchmark_family": payload.get("benchmark_family"),
        "benchmark_name": payload.get("benchmark_name"),
        "phase_name": payload.get("phase_name"),
        "comparability_status": payload.get("comparability_status"),
        "comparability_rules": payload.get("comparability_rules"),
        "primary_metric": payload.get("primary_metric"),
        "reference_type": payload.get("reference_type"),
        "targets": payload.get("targets"),
        "validation": {
            "row_count": validation.get("row_count"),
            "column_count": validation.get("column_count"),
            "sha256": validation.get("sha256"),
            "fieldnames": validation.get("fieldnames"),
            "target_columns": validation.get("target_columns"),
            "subject_id_column": validation.get("subject_id_column"),
            "validated_at_utc": validation.get("validated_at_utc"),
        },
        "redaction": {
            "csv_path_exported": False,
            "provenance_path_exported": False,
            "subject_ids_exported": False,
        },
    }


def _summarize_liu_osf_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = _read_json(path)
    folders = payload.get("folders")
    if not isinstance(folders, dict):
        folders = {}

    folder_summary: dict[str, Any] = {}
    key_derivatives: list[dict[str, Any]] = []
    derivative_keep = {
        "bbpred_res_202401_2.pkl",
        "pyspi_hcp_schaefer100x7_subj_term_profile_updated.npy",
        "pyspi_terms_clean.txt",
        "HCP_S1200_schaefer100x7_PhiIDFull_MMI.mat",
    }
    for folder_name, folder_payload in folders.items():
        if not isinstance(folder_payload, dict):
            continue
        folder_summary[folder_name] = {
            "file_count": folder_payload.get("file_count"),
            "total_bytes": folder_payload.get("total_bytes"),
        }
        if folder_name != "derivatives":
            continue
        for entry in folder_payload.get("files", []):
            if not isinstance(entry, dict):
                continue
            if entry.get("name") not in derivative_keep:
                continue
            key_derivatives.append(
                {
                    "name": entry.get("name"),
                    "size_bytes": entry.get("size"),
                    "download_url": entry.get("download_url"),
                    "sha256": entry.get("sha256"),
                }
            )

    return {
        "manifest_file": _file_record(path, "liu_fc_pyspi_osf_manifest"),
        "generated_by_entrypoint": (
            "scripts/analysis/fc_benchmarking/setup_liu_fc_pyspi.py"
        ),
        "repo_url": payload.get("repo_url"),
        "osf_project_url": "https://osf.io/75je2",
        "osf_api_root": "https://api.osf.io/v2/nodes/75je2/files/osfstorage/",
        "vendor_commit": payload.get("vendor_commit"),
        "requested_folders": payload.get("requested_folders"),
        "folders": folder_summary,
        "key_derivative_files": key_derivatives,
        "redaction": {
            "download_dir_exported": False,
            "destination_paths_exported": False,
            "raw_subject_file_examples_exported": False,
        },
    }


def _summarize_data_manifest(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = _read_json(path)
    return {
        "manifest_file": _file_record(path, "liu_project_data_manifest"),
        "lane_id": payload.get("lane_id"),
        "vendor_commit": payload.get("vendor_commit"),
        "source_manifest_name": _safe_name(payload.get("source_manifest_path")),
        "available_atlases": payload.get("available_atlases"),
        "prediction_asset_name": _safe_name(payload.get("prediction_asset")),
        "term_count": payload.get("term_count"),
        "subject_count": payload.get("subject_count"),
        "session_count": payload.get("session_count"),
        "derivatives_file_count": payload.get("derivatives_file_count"),
        "derivatives_total_bytes": payload.get("derivatives_total_bytes"),
        "redaction": {
            "local_roots_exported": False,
            "absolute_paths_exported": False,
        },
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
    ap.add_argument(
        "--liu-component-provenance-json",
        help="redacted summary source for Liu component reconstruction provenance",
    )
    ap.add_argument(
        "--liu-target-manifest",
        help="redacted summary source for the reconstructed Liu component target manifest",
    )
    ap.add_argument(
        "--liu-osf-manifest",
        help="redacted summary source for Liu FC-pyspi OSF download URLs and checksums",
    )
    ap.add_argument(
        "--data-manifest",
        help="redacted summary source for the local Liu derivative/project data manifest",
    )
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

    liu_component_provenance = _summarize_liu_component_provenance(
        _optional_path(args.liu_component_provenance_json)
    )
    liu_target_manifest = _summarize_liu_target_manifest(
        _optional_path(args.liu_target_manifest)
    )
    liu_osf_manifest = _summarize_liu_osf_manifest(_optional_path(args.liu_osf_manifest))
    project_data_manifest = _summarize_data_manifest(_optional_path(args.data_manifest))

    manifest = {
        "schema_version": "auditable-episode-local-data-v1",
        "dataset": "HCP-YA reconstructed Liu-component A1 Cognition",
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
                "name": "Liu FC-pyspi OSF manifest",
                "url": "https://osf.io/75je2",
                "note": (
                    "Use the manifest generated by "
                    "scripts/analysis/fc_benchmarking/setup_liu_fc_pyspi.py from the "
                    "netneurolab/liu_fc-pyspi OSF asset listing instead of inventing a "
                    "new download route."
                ),
            },
            {
                "name": "Liu component behavior reconstruction provenance",
                "url": "https://raw.githubusercontent.com/yetianmed/subcortex/master/Behavior/ica.mat",
                "note": (
                    "Record source supplement, demixing-matrix URL/checksum, source CSV "
                    "checksum, and reconstruction caveats in the supplied "
                    "--liu-component-provenance-json. Component targets are reconstructed "
                    "from the paper mapping and published demixing matrix; they are not "
                    "paper-exact subject weights."
                ),
            },
            {
                "name": "HCP ConnectomeDB behavior export",
                "url": (
                    "https://wiki.humanconnectome.org/docs/"
                    "How%20to%20Access%20Data%20on%20ConnectomeDB.html"
                ),
                "note": (
                    "Create/log into an HCP account and accept applicable HCP data-use "
                    "terms before staging the behavior CSV used by the Liu projection."
                ),
            },
        ],
        "sample_size": int(len(y_true)),
        "target_construction": target_provenance,
        "source_manifests": {
            "liu_component_behavior_provenance": liu_component_provenance,
            "liu_component_target_manifest": liu_target_manifest,
            "liu_fc_pyspi_osf_manifest": liu_osf_manifest,
            "liu_project_data_manifest": project_data_manifest,
        },
        "prediction_source": prediction_source,
        "prediction_column": pred_col,
        "privacy": {
            "raw_hcp_subject_rows_exported": False,
            "subject_identifiers_exported": False,
            "audit_npz_contains_subject_ids": False,
            "absolute_local_paths_exported": False,
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
