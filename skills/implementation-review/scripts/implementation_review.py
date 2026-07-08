#!/usr/bin/env python3
"""Deterministic implementation-review rubrics for QSM and rapidtide.

Faithful, dependency-free port of the Brain Researcher MCP tools
``qsm_implementation_review`` and ``rapidtide_implementation_review``.

- QSM  : static analysis of caller-supplied reconstruction *code* for
         direct-inversion / local-field dataflow hazards.
- rapidtide: rule check of a caller-supplied *method_contract* (plus optional
         numeric ``subject_summaries``) against the canonical sLFO lag-mapping
         method.

Both are NON-DISPLACIVE: they emit hard constraints, findings, and QC checks,
never a replacement reconstruction recipe. They only certify that known-bad
choices are not passing review as if they were scientifically safe.

The executable rule constants below are ported verbatim from the BR source
(``services/review/qsm_pitfall_critic.py`` and ``rapidtide_critic.py``) and are
mirrored, human-readable, in ``references/qsm_review_rules.yaml`` and
``references/rapidtide_review_rules.yaml``. ``--selftest`` re-runs frozen
behavioral fixtures as a regression guard against edits to THIS script; it does
not import ``brain_researcher`` and so cannot detect upstream BR drift.

Usage:
    python implementation_review.py <input.json>
    python implementation_review.py --selftest

Input JSON (routed by the ``method`` field):

    QSM:
        {"method": "qsm", "code": "<pipeline code>", "filename": "recon.py"}

    rapidtide:
        {"method": "rapidtide",
         "task_profile": "sLFO_delay_mapping",
         "method_contract": { ... },
         "subject_summaries": [ ... ]}

Output: a single JSON verdict object on stdout (see
``references/output_contract.md``). Exit code is 0 whenever a verdict is
produced (including ``block``); non-zero only on malformed input.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

# ===========================================================================
# Shared verdict primitives  (mirror of core.contracts.code_review)
# ===========================================================================

# ReviewFinding.severity is one of {"warn", "error", "critical"}
# ReviewFinding.action   is one of {"block", "warn"}
# CodeReviewVerdict.decision   in {"approve","approve_with_warnings","revise","block"}
# CodeReviewVerdict.risk_level in {"low","medium","high","critical"}


def _finding(
    *,
    rule_id: str,
    severity: str,
    action: str,
    message: str,
    suggested_fix: str,
    reason_tags: list[str],
    artifact_name: str | None = None,
) -> dict[str, Any]:
    """Build a ReviewFinding dict matching pydantic model_dump() field order."""
    return {
        "rule_id": rule_id,
        "severity": severity,
        "action": action,
        "message": message,
        "suggested_fix": suggested_fix,
        "step_id": None,
        "artifact_name": artifact_name,
        "kg_evidence": [],
        "reason_tags": list(reason_tags),
        "novelty": None,
    }


def _verdict(
    *,
    decision: str,
    risk_level: str,
    findings: list[dict[str, Any]],
    checklist_generated: list[str],
    reviewer_rationale: str,
    kg_rules_consulted: list[str] | None = None,
) -> dict[str, Any]:
    """Build a CodeReviewVerdict dict matching pydantic model_dump()."""
    return {
        "decision": decision,
        "risk_level": risk_level,
        "findings": findings,
        "kg_rules_consulted": list(kg_rules_consulted or []),
        "checklist_generated": list(checklist_generated),
        "reviewer_rationale": reviewer_rationale,
    }


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts: list[str] = []
        for key, item in value.items():
            parts.append(str(key))
            parts.append(_text(item))
        return " ".join(parts)
    if isinstance(value, (list, tuple, set)):
        return " ".join(_text(item) for item in value)
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except Exception:
        return str(value)


def _normalized_text(*values: Any) -> str:
    return " ".join(_text(value) for value in values).lower()


# ===========================================================================
# QSM implementation review
# ===========================================================================

_QSM_REASON_TAGS = ["qsm_reconstruction", "domain_invariant", "anti_pitfall"]

_QSM_HARD_CONSTRAINTS = [
    "Dipole inversion must consume an explicitly named local_field.",
    "Direct inversion of total, raw, inter-echo, or phase-difference fields is forbidden.",
    "Background/local-field removal output must be the dipole-inversion input.",
    "Phase-to-field conversion must state delta_TE and B0/gamma scaling or an equivalent unit convention.",
]

_QSM_QC_PROTOCOL = [
    "Check output shape, affine, voxel size, and finite voxel ratio before finalizing.",
    "Check robust susceptibility quantiles, IQR, and standard deviation in the brain mask.",
    "Check a local high-pass or detrended contrast proxy to catch contrast collapse.",
    "Check calcification/streak behavior separately from global smoothness when calcification is present.",
]

_QSM_NON_DISPLACEMENT_NOTICE = (
    "Use this QSM response as an audit-only constraint set. Do not replace the "
    "agent's reconstruction algorithm unless a hard constraint is violated."
)

_QSM_FORBIDDEN_GUIDANCE = [
    "Do not suggest generic fMRI preprocessing, fMRIPrep, FEAT, or fieldmap-distortion workflows for QSM reconstruction.",
    "Do not prescribe full-resolution iterative TV/ADMM as mandatory.",
    "Do not recommend TKD-only without contrast-preservation QC.",
]

_QSM_BAD_INVERSION_INPUT_NAMES = frozenset(
    {
        "totalfield",
        "total_field",
        "fieldppm",
        "field_ppm",
        "rawfield",
        "raw_field",
        "phasefield",
        "phase_field",
        "interecho",
        "inter_echo",
        "interechofield",
        "inter_echo_field",
        "deltappm",
        "delta_ppm",
    }
)

_QSM_INVERSION_CALL_RE = re.compile(
    r"(?P<callee>\b[a-zA-Z_][a-zA-Z0-9_]*"
    r"(?:admm|tv|tkd|dipole|invert|inversion|qsm)"
    r"[a-zA-Z0-9_]*\b)\s*\((?P<args>[^)]{0,300})\)",
    re.IGNORECASE | re.DOTALL,
)

_QSM_ASSIGN_LOCAL_FIELD_RE = re.compile(
    r"\b(?P<name>[a-zA-Z_][a-zA-Z0-9_]*local[a-zA-Z0-9_]*field[a-zA-Z0-9_]*)\s*=",
    re.IGNORECASE,
)

_QSM_TKD_CONTRAST_MARKERS = (
    "tikhonov",
    "admm",
    "total variation",
    "tv regular",
    "medi",
    "fansi",
    "contrast",
    "highpass",
    "high-pass",
)


def _qsm_field_name(value: Any) -> str:
    text = _normalized_text(value)
    return re.sub(r"[^a-z0-9_]+", "", text)


def _qsm_looks_like_local_field(value: Any) -> bool:
    name = _qsm_field_name(value)
    return name in {
        "localfield",
        "local_field",
        "resharplocalfield",
        "resharp_local_field",
        "vsharplocalfield",
        "vsharp_local_field",
        "backgroundremovedfield",
        "background_removed_field",
    } or ("local" in name and "field" in name)


def _qsm_looks_like_bad_inversion_input(value: Any) -> bool:
    name = _qsm_field_name(value)
    return name in _QSM_BAD_INVERSION_INPUT_NAMES or any(
        bad in name
        for bad in (
            "totalfield",
            "fieldppm",
            "rawfield",
            "phasefield",
            "interechofield",
            "deltappm",
        )
    )


def _qsm_has_background_removal_code(text: str) -> bool:
    return any(
        marker in text
        for marker in (
            "background_removal",
            "background removal",
            "resharp",
            "vsharp",
            "v-sharp",
            "sharp",
            "lbv",
            "local_field",
            "local field",
        )
    )


def _qsm_first_call_arg(args: str) -> str:
    first = args.split(",", 1)[0]
    return first.strip().strip("\"'")


def _qsm_roll_up(findings: list[dict[str, Any]]) -> tuple[str, str]:
    if any(f["action"] == "block" or f["severity"] == "critical" for f in findings):
        return "block", "critical"
    if any(f["severity"] == "error" for f in findings):
        return "revise", "high"
    if any(f["severity"] == "warn" for f in findings):
        return "approve_with_warnings", "medium"
    return "approve", "low"


def _qsm_rationale(findings: list[dict[str, Any]], decision: str) -> str:
    # Verbatim from qsm_pitfall_critic._rationale (ASCII hyphen, all findings).
    if not findings:
        return f"QSM pitfall review passed all checks. Decision: {decision}."
    head = [f"QSM pitfall review - Decision: {decision}. {len(findings)} finding(s):"]
    for finding in findings:
        head.append(
            f"[{finding['severity'].upper()}] {finding['rule_id']}: {finding['message']}"
        )
    return " | ".join(head)


def _rt_rationale(findings: list[dict[str, Any]], decision: str) -> str:
    # Verbatim from rapidtide_critic._rationale (em dash, first 5 findings).
    if not findings:
        return f"rapidtide method review passed all canonical checks. Decision: {decision}."
    head = [
        f"rapidtide method review — Decision: {decision}. {len(findings)} finding(s):"
    ]
    for finding in findings[:5]:
        head.append(
            f"[{finding['severity'].upper()}] {finding['rule_id']}: {finding['message']}"
        )
    return " | ".join(head)


def review_qsm(code: str, filename: str | None = None) -> dict[str, Any]:
    """Review generated QSM code for direct-inversion dataflow hazards.

    Mirror of ``review_qsm_implementation_payload`` + the MCP wrapper's
    ``domain_invariant_review`` envelope.
    """
    text = _normalized_text(filename, code)
    findings: list[dict[str, Any]] = []

    local_vars = {
        _qsm_field_name(match.group("name"))
        for match in _QSM_ASSIGN_LOCAL_FIELD_RE.finditer(code or "")
    }
    has_inversion_call = False
    has_bad_inversion_input = False
    has_ambiguous_inversion_input = False

    for match in _QSM_INVERSION_CALL_RE.finditer(code or ""):
        has_inversion_call = True
        arg = _qsm_first_call_arg(match.group("args"))
        arg_name = _qsm_field_name(arg)
        if _qsm_looks_like_bad_inversion_input(arg):
            has_bad_inversion_input = True
            continue
        if (
            arg_name
            and arg_name not in local_vars
            and not _qsm_looks_like_local_field(arg)
        ):
            has_ambiguous_inversion_input = True

    if has_inversion_call and has_bad_inversion_input:
        findings.append(
            _finding(
                rule_id="QSM_IMPLEMENTATION_DIRECT_FIELD_INVERSION",
                severity="critical",
                action="block",
                message=(
                    "QSM implementation appears to pass a total/raw/inter-echo "
                    "or phase-derived field directly into a dipole inversion call."
                ),
                suggested_fix=(
                    "Route total_field through explicit background/local-field "
                    "removal and call inversion with the resulting local_field."
                ),
                reason_tags=_QSM_REASON_TAGS,
            )
        )

    if has_inversion_call and not _qsm_has_background_removal_code(text):
        findings.append(
            _finding(
                rule_id="QSM_IMPLEMENTATION_MISSING_BACKGROUND_REMOVAL",
                severity="critical",
                action="block",
                message=(
                    "QSM implementation contains an inversion call but no "
                    "detectable background/local-field removal stage."
                ),
                suggested_fix=(
                    "Create an explicit local_field via RESHARP/V-SHARP/LBV or "
                    "equivalent background removal before dipole inversion."
                ),
                reason_tags=_QSM_REASON_TAGS,
            )
        )

    if (
        has_inversion_call
        and _qsm_has_background_removal_code(text)
        and not has_bad_inversion_input
        and has_ambiguous_inversion_input
    ):
        findings.append(
            _finding(
                rule_id="QSM_IMPLEMENTATION_AMBIGUOUS_INVERSION_INPUT",
                severity="critical",
                action="block",
                message=(
                    "QSM implementation has background/local-field operations, "
                    "but at least one inversion call does not clearly consume a "
                    "local_field variable."
                ),
                suggested_fix=(
                    "Name the background-removal output local_field and pass that "
                    "variable directly into dipole inversion."
                ),
                reason_tags=_QSM_REASON_TAGS,
            )
        )

    if "tkd" in text and not any(
        marker in text for marker in _QSM_TKD_CONTRAST_MARKERS
    ):
        findings.append(
            _finding(
                rule_id="QSM_IMPLEMENTATION_TKD_WITHOUT_CONTRAST_QC",
                severity="error",
                action="warn",
                message=(
                    "QSM implementation appears to rely on TKD without a visible "
                    "contrast-preservation or high-pass QC check."
                ),
                suggested_fix=(
                    "Add contrast proxy/QC checks or use a contrast-preserving "
                    "regularized inversion."
                ),
                reason_tags=_QSM_REASON_TAGS,
            )
        )

    decision, risk_level = _qsm_roll_up(findings)
    checklist = [
        *_QSM_HARD_CONSTRAINTS,
        *_QSM_QC_PROTOCOL,
        "Implementation review is audit-only and must not prescribe a replacement pipeline.",
    ]
    verdict = _verdict(
        decision=decision,
        risk_level=risk_level,
        findings=findings,
        checklist_generated=checklist,
        reviewer_rationale=_qsm_rationale(findings, decision),
    )
    verdict["domain_invariant_review"] = {
        "task_type": "qsm_reconstruction",
        "advice_mode": "audit_only",
        "hard_constraints": _QSM_HARD_CONSTRAINTS,
        "non_displacement_notice": _QSM_NON_DISPLACEMENT_NOTICE,
        "qc_protocol": _QSM_QC_PROTOCOL,
        "forbidden_guidance": _QSM_FORBIDDEN_GUIDANCE,
    }
    return verdict


# ===========================================================================
# rapidtide implementation review
# ===========================================================================

_RT_REASON_TAGS = ["rapidtide", "slfo_lag", "method_appropriateness"]

# Canonical sLFO band (Hz): low-frequency oscillation, below respiratory/cardiac.
_RT_LFO_BAND_LOW_HZ = 0.009
_RT_LFO_BAND_HIGH_HZ = 0.15
# A lag-search window narrower than this (seconds, total span) clips real sLFO
# transit delays, which span roughly -10..+10 s across the brain.
_RT_MIN_LAG_SEARCH_SPAN_S = 8.0
# Canonical refinement uses multiple passes to purify the probe regressor.
_RT_MIN_REFINEMENT_PASSES = 2
# Long TR needs oversampling for sub-TR lag resolution.
_RT_OVERSAMPLE_TR_THRESHOLD_S = 1.5
# Fraction of voxels whose peak lag sits at the search boundary that indicates a
# genuinely too-narrow window (observable confirmation, not just a declaration).
_RT_LAG_BOUNDARY_RAIL_FRACTION = 0.10

_RT_CHECKLIST = [
    "cross_correlation_lag_search",
    "lag_search_range_s",
    "refinement_passes",
    "temporal_filter_band_hz",
    "regressor_source",
]


def _rt_as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def _rt_as_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number


def _rt_as_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _rt_pair(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return None
    low, high = _rt_as_float(value[0]), _rt_as_float(value[1])
    if low is None or high is None:
        return None
    return (min(low, high), max(low, high))


def _rt_roll_up(findings: list[dict[str, Any]]) -> tuple[str, str]:
    if not findings:
        return "approve", "low"
    if any(f["action"] == "block" or f["severity"] == "critical" for f in findings):
        return "block", "critical"
    if any(f["severity"] == "error" for f in findings):
        return "revise", "high"
    return "approve_with_warnings", "medium"


def review_rapidtide(
    task_profile: str,
    method_contract: dict[str, Any],
    subject_summaries: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Review a rapidtide-style sLFO lag analysis against the canonical method.

    Mirror of ``rapidtide_critic.review_rapidtide_implementation``. Raises
    ValueError on the same malformed inputs the BR tool rejects.
    """
    profile = _rt_as_str(task_profile)
    if not profile:
        raise ValueError("task_profile is required")
    if not isinstance(method_contract, dict):
        raise ValueError("method_contract must be an object")
    if subject_summaries is not None and not isinstance(subject_summaries, list):
        raise ValueError("subject_summaries must be a list when provided")

    findings: list[dict[str, Any]] = []

    # 1. The defining canonical step: cross-correlation lag search. A static
    #    zero-lag regression is a different (wrong) method for sLFO delay mapping.
    if "cross_correlation_lag_search" in method_contract and not _rt_as_bool(
        method_contract.get("cross_correlation_lag_search")
    ):
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_STATIC_ZERO_LAG_CORRELATION",
                severity="critical",
                action="block",
                message=(
                    "Analysis uses a static (zero-lag) regression instead of a "
                    "time-lagged cross-correlation search. This is not the "
                    "canonical rapidtide sLFO delay-mapping method."
                ),
                suggested_fix=(
                    "Search peak cross-correlation over a lag window per voxel; "
                    "do not fit a single fixed-lag GLM."
                ),
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 2. Lag-search window: required, and must be wide enough not to clip delays.
    lag_range = _rt_pair(method_contract.get("lag_search_range_s"))
    if lag_range is None:
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_LAG_SEARCH_RANGE_MISSING",
                severity="error",
                action="block",
                message="No lag-search range declared; cannot verify sLFO delays are not clipped.",
                suggested_fix="Declare lag_search_range_s, e.g. [-10, 10] s, covering plausible transit delays.",
                reason_tags=_RT_REASON_TAGS,
            )
        )
    else:
        span = lag_range[1] - lag_range[0]
        if span < _RT_MIN_LAG_SEARCH_SPAN_S:
            findings.append(
                _finding(
                    rule_id="RAPIDTIDE_LAG_SEARCH_RANGE_TOO_NARROW",
                    severity="error",
                    action="block",
                    message=(
                        f"Lag-search span {span:.1f}s is narrower than the "
                        f"~{_RT_MIN_LAG_SEARCH_SPAN_S:.0f}s needed for whole-brain sLFO "
                        "transit delays; true peaks will rail at the boundary."
                    ),
                    suggested_fix="Widen lag_search_range_s (e.g. [-10, 10] s) and re-run.",
                    reason_tags=_RT_REASON_TAGS,
                )
            )

    # 3. Probe-regressor refinement (canonical iterative purification).
    passes = method_contract.get("refinement_passes")
    passes_num = _rt_as_float(passes)
    if passes_num is not None and passes_num < _RT_MIN_REFINEMENT_PASSES:
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_NO_REGRESSOR_REFINEMENT",
                severity="error",
                action="warn",
                message=(
                    f"Only {int(passes_num)} refinement pass(es); the canonical "
                    "method iteratively refines the probe regressor (>= "
                    f"{_RT_MIN_REFINEMENT_PASSES})."
                ),
                suggested_fix="Run >=2 refinement passes so the regressor reflects the sLFO, not the raw global mean.",
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 4. Naive global-mean regressor without refinement.
    regressor_source = (
        _rt_as_str(method_contract.get("regressor_source")) or ""
    ).lower()
    if regressor_source in {"global_mean", "global_signal", "mean"} and (
        passes_num is None or passes_num < _RT_MIN_REFINEMENT_PASSES
    ):
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_NAIVE_GLOBAL_REGRESSOR",
                severity="warn",
                action="warn",
                message=(
                    "Probe regressor is the raw global mean without refinement; "
                    "this conflates sLFO with non-sLFO global signal."
                ),
                suggested_fix="Derive and iteratively refine the sLFO probe regressor instead of using the raw global mean.",
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 5. Temporal filter band must isolate the LFO band.
    band = _rt_pair(method_contract.get("temporal_filter_band_hz"))
    if band is not None and (
        band[0] < _RT_LFO_BAND_LOW_HZ - 1e-6 or band[1] > _RT_LFO_BAND_HIGH_HZ + 1e-6
    ):
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_FILTER_BAND_OUTSIDE_LFO",
                severity="warn",
                action="warn",
                message=(
                    f"Temporal filter band [{band[0]:.3g}, {band[1]:.3g}] Hz extends "
                    f"outside the sLFO band [{_RT_LFO_BAND_LOW_HZ}, {_RT_LFO_BAND_HIGH_HZ}] Hz; "
                    "respiratory/cardiac signal can contaminate the regressor."
                ),
                suggested_fix="Restrict the bandpass to the LFO band (~0.009-0.15 Hz).",
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 6. Oversampling for sub-TR lag resolution when TR is long.
    tr_s = _rt_as_float(method_contract.get("tr_s"))
    oversample = _rt_as_float(method_contract.get("oversample_factor"))
    if (
        tr_s is not None
        and tr_s >= _RT_OVERSAMPLE_TR_THRESHOLD_S
        and oversample is not None
        and oversample < 2.0
    ):
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_INSUFFICIENT_OVERSAMPLING",
                severity="warn",
                action="warn",
                message=(
                    f"TR={tr_s:.2g}s with oversample_factor={oversample:.2g}; lag "
                    "resolution is limited to the TR without oversampling."
                ),
                suggested_fix="Increase oversample_factor (>=2) for sub-TR lag resolution at long TR.",
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 7. Lag-map despeckling.
    if "lag_map_despeckle" in method_contract and not _rt_as_bool(
        method_contract.get("lag_map_despeckle")
    ):
        findings.append(
            _finding(
                rule_id="RAPIDTIDE_LAG_MAP_NO_DESPECKLE",
                severity="warn",
                action="warn",
                message="Lag-map despeckling disabled; isolated voxels can hold spurious extreme lags.",
                suggested_fix="Enable despeckling so neighbours correct isolated lag outliers.",
                reason_tags=_RT_REASON_TAGS,
            )
        )

    # 8. Observable confirmation: peak lags railing at the search boundary.
    for summary in subject_summaries or []:
        if not isinstance(summary, dict):
            continue
        sid = _rt_as_str(summary.get("subject")) or _rt_as_str(summary.get("id"))
        rail = _rt_as_float(summary.get("lag_boundary_fraction"))
        if rail is not None and rail > _RT_LAG_BOUNDARY_RAIL_FRACTION:
            findings.append(
                _finding(
                    rule_id="RAPIDTIDE_LAG_RAILING_AT_BOUNDARY",
                    severity="error",
                    action="block",
                    artifact_name=sid,
                    message=(
                        f"{rail:.0%} of voxels peak at the lag-search boundary"
                        + (f" in {sid}" if sid else "")
                        + "; the search window truncates real delays."
                    ),
                    suggested_fix="Widen the lag-search range until boundary railing is negligible, then re-run.",
                    reason_tags=_RT_REASON_TAGS,
                )
            )

    decision, risk_level = _rt_roll_up(findings)
    return _verdict(
        decision=decision,
        risk_level=risk_level,
        findings=findings,
        checklist_generated=list(_RT_CHECKLIST),
        reviewer_rationale=_rt_rationale(findings, decision),
    )


# ===========================================================================
# Router / CLI
# ===========================================================================


def run_review(payload: dict[str, Any]) -> dict[str, Any]:
    """Route a payload to the QSM or rapidtide reviewer. Returns an envelope
    matching the MCP tool: {"ok": bool, ...verdict... | "error": str}."""
    if not isinstance(payload, dict):
        return {"ok": False, "error": "input_must_be_object"}

    method = str(payload.get("method", "")).strip().lower()

    if method == "qsm":
        code = payload.get("code")
        if not (isinstance(code, str) and code.strip()):
            return {"ok": False, "error": "code_required"}
        filename = payload.get("filename")
        try:
            verdict = review_qsm(code, filename=filename)
        except Exception as exc:  # pragma: no cover - defensive parity with MCP
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **verdict}

    if method == "rapidtide":
        task_profile = payload.get("task_profile")
        if not (isinstance(task_profile, str) and task_profile.strip()):
            return {"ok": False, "error": "task_profile_required"}
        method_contract = payload.get("method_contract")
        if not isinstance(method_contract, dict):
            return {"ok": False, "error": "method_contract_must_be_object"}
        subject_summaries = payload.get("subject_summaries")
        try:
            verdict = review_rapidtide(
                task_profile=task_profile,
                method_contract=method_contract,
                subject_summaries=subject_summaries,
            )
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True, **verdict}

    return {
        "ok": False,
        "error": "unknown_method",
        "detail": "Set 'method' to 'qsm' or 'rapidtide'.",
    }


def _selftest() -> int:
    """Re-run the BR unit fixtures to prove the port matches the source tool."""
    failures: list[str] = []

    def check(name: str, cond: bool) -> None:
        if not cond:
            failures.append(name)

    # --- rapidtide fixtures (mirror tests/unit/review/test_rapidtide_critic.py) ---
    canonical = {
        "cross_correlation_lag_search": True,
        "lag_search_range_s": [-10.0, 10.0],
        "refinement_passes": 3,
        "regressor_source": "refined_sLFO",
        "temporal_filter_band_hz": [0.009, 0.15],
        "oversample_factor": 4,
        "tr_s": 2.0,
        "lag_map_despeckle": True,
    }
    v = review_rapidtide("sLFO_delay_mapping", dict(canonical))
    check("rt_canonical_approves", v["decision"] == "approve" and not v["findings"])

    c = dict(canonical, cross_correlation_lag_search=False)
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "rt_static_zero_lag_blocks",
        v["decision"] == "block"
        and v["risk_level"] == "critical"
        and "RAPIDTIDE_STATIC_ZERO_LAG_CORRELATION" in ids,
    )

    c = dict(canonical, lag_search_range_s=[-2.0, 2.0])
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "rt_narrow_range_blocks",
        v["decision"] == "block" and "RAPIDTIDE_LAG_SEARCH_RANGE_TOO_NARROW" in ids,
    )

    c = {k: val for k, val in canonical.items() if k != "lag_search_range_s"}
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "rt_missing_range_blocks",
        v["decision"] == "block" and "RAPIDTIDE_LAG_SEARCH_RANGE_MISSING" in ids,
    )

    c = dict(canonical, refinement_passes=1)
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "rt_no_refinement_revises",
        v["decision"] == "revise" and "RAPIDTIDE_NO_REGRESSOR_REFINEMENT" in ids,
    )

    c = dict(canonical, regressor_source="global_mean", refinement_passes=1)
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check("rt_naive_global_warns", "RAPIDTIDE_NAIVE_GLOBAL_REGRESSOR" in ids)

    c = dict(
        canonical, temporal_filter_band_hz=[0.01, 0.5], tr_s=3.0, oversample_factor=1
    )
    v = review_rapidtide("sLFO_delay_mapping", c)
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "rt_wide_band_and_oversample_warn",
        "RAPIDTIDE_FILTER_BAND_OUTSIDE_LFO" in ids
        and "RAPIDTIDE_INSUFFICIENT_OVERSAMPLING" in ids
        and v["decision"] == "approve_with_warnings",
    )

    v = review_rapidtide(
        "sLFO_delay_mapping",
        dict(canonical),
        subject_summaries=[{"subject": "sub-01", "lag_boundary_fraction": 0.3}],
    )
    railing = [
        f for f in v["findings"] if f["rule_id"] == "RAPIDTIDE_LAG_RAILING_AT_BOUNDARY"
    ]
    check(
        "rt_boundary_railing_blocks",
        v["decision"] == "block"
        and bool(railing)
        and railing[0]["artifact_name"] == "sub-01",
    )

    for bad in (("", {}), ("x", None)):
        try:
            review_rapidtide(bad[0], bad[1])  # type: ignore[arg-type]
            check(f"rt_rejects_{bad}", False)
        except ValueError:
            check(f"rt_rejects_{bad}", True)

    # --- QSM fixtures (behavioral, from qsm_pitfall_critic semantics) ---
    v = review_qsm(
        "local_field = resharp(total_field)\nchi = dipole_inversion(local_field)"
    )
    check(
        "qsm_clean_local_field_approves",
        v["decision"] == "approve" and not v["findings"],
    )

    v = review_qsm("chi = dipole_inversion(total_field)")
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "qsm_direct_total_field_blocks",
        v["decision"] == "block"
        and "QSM_IMPLEMENTATION_DIRECT_FIELD_INVERSION" in ids
        and "QSM_IMPLEMENTATION_MISSING_BACKGROUND_REMOVAL" in ids,
    )

    v = review_qsm("chi = admm_qsm(some_field)")
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "qsm_missing_background_blocks",
        v["decision"] == "block"
        and "QSM_IMPLEMENTATION_MISSING_BACKGROUND_REMOVAL" in ids,
    )

    v = review_qsm("local_field = vsharp(x)\nchi = dipole_inversion(mystery_field)")
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "qsm_ambiguous_input_blocks",
        v["decision"] == "block"
        and "QSM_IMPLEMENTATION_AMBIGUOUS_INVERSION_INPUT" in ids,
    )

    v = review_qsm("local_field = resharp(f)\nchi = tkd_inversion(local_field)")
    ids = {f["rule_id"] for f in v["findings"]}
    check(
        "qsm_tkd_without_contrast_revises",
        v["decision"] == "revise"
        and "QSM_IMPLEMENTATION_TKD_WITHOUT_CONTRAST_QC" in ids,
    )

    if failures:
        print(json.dumps({"selftest": "FAIL", "failures": failures}, indent=2))
        return 1
    print(
        json.dumps(
            {"selftest": "PASS", "cases": "all rapidtide + qsm fixtures matched"},
            indent=2,
        )
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        sys.stderr.write(
            "usage: python implementation_review.py <input.json>\n"
            "       python implementation_review.py --selftest\n"
        )
        return 2
    if argv[0] == "--selftest":
        return _selftest()

    path = argv[0]
    try:
        with open(path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        sys.stderr.write(f"input file not found: {path}\n")
        return 2
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"invalid JSON in {path}: {exc}\n")
        return 2

    result = run_review(payload)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
