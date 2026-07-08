#!/usr/bin/env python3
"""Offline deterministic plan validator for brain-researcher analysis plans.

Port of the ``pipeline_plan_validate`` MCP tool in its rule-engine mode
(``use_kg=False``). No live knowledge graph, no registry, no filesystem
sandbox, no network -- pure stdlib rule evaluation over a caller-supplied
plan dict.

The rule metadata (thresholds, tool sets, severities, method-compatibility
seed) lives in ``../references/*.json`` so it is auditable and can be diffed
against the source BR configs. This script holds only the evaluation logic
(the structural check functions and the roll-up), ported verbatim from
brain_researcher/services/review/{rule_engine,verdict_builder}.py and
services/review/checks/{tool_order,space_compat,method_appropriateness}.py.

Usage:
    python scripts/validate_plan.py <plan.json>
    python scripts/validate_plan.py -            # read plan JSON from stdin

Input: the same dict shape ``pipeline_plan_validate(plan=...)`` accepts, i.e.
    {"steps": [{"tool": "...", "params": {...}, "step_id": "..."}, ...],
     "project_root": "...", "run_tag": "..."}
An optional top-level {"plan": {...}} wrapper is also accepted.

Output: JSON verdict on stdout (decision / risk_level / findings / checklist).
Exit code: 0 if ok (no error/block findings), 1 if the plan is blocked or a
schema error was raised, 2 on usage error.
"""

from __future__ import annotations

import argparse
import json
import operator
import sys
from pathlib import Path
from typing import Any

_REF_DIR = Path(__file__).resolve().parent.parent / "references"

_OPS = {
    "lt": operator.lt,
    "lte": operator.le,
    "gt": operator.gt,
    "gte": operator.ge,
    "eq": operator.eq,
    "ne": operator.ne,
    "contains": lambda v, needle: needle in v if v is not None else False,
    "missing": lambda v, _: v is None,
}


# ---------------------------------------------------------------------------
# Reference loading
# ---------------------------------------------------------------------------


def _load_json(name: str) -> dict[str, Any]:
    return json.loads((_REF_DIR / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schema coercion (port of server._coerce_plan)
# ---------------------------------------------------------------------------


class PlanSchemaError(ValueError):
    """Raised when the plan dict cannot be coerced (hard schema failure)."""


def coerce_plan(raw: dict[str, Any]) -> dict[str, Any]:
    """Validate/normalize a plan dict. Raise PlanSchemaError on hard failure."""
    if not isinstance(raw, dict):
        raise PlanSchemaError("plan must be an object")
    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise PlanSchemaError("plan.steps must be a non-empty list")

    steps: list[dict[str, Any]] = []
    seen_step_ids: set[str] = set()
    for i, item in enumerate(steps_raw, start=1):
        if not isinstance(item, dict):
            raise PlanSchemaError(f"plan.steps[{i}] must be an object")
        tool = item.get("tool") or item.get("tool_id") or item.get("name")
        if not isinstance(tool, str) or not tool.strip():
            raise PlanSchemaError(f"plan.steps[{i}].tool is required")
        params = item.get("params") or item.get("parameters") or {}
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise PlanSchemaError(f"plan.steps[{i}].params must be an object")
        step_id = item.get("step_id") or item.get("id") or item.get("name")
        if step_id is not None and not isinstance(step_id, str):
            step_id = str(step_id)
        if isinstance(step_id, str):
            step_id = step_id.strip() or None
        if step_id:
            if step_id in seen_step_ids:
                raise PlanSchemaError(
                    f"plan.steps[{i}] has duplicate step_id '{step_id}'"
                )
            seen_step_ids.add(step_id)
        steps.append({"tool": tool.strip(), "params": params, "step_id": step_id})

    project_root = raw.get("project_root")
    if project_root is not None and (
        not isinstance(project_root, str) or not project_root.strip()
    ):
        raise PlanSchemaError(
            "plan.project_root must be a non-empty string when provided"
        )
    run_tag = raw.get("run_tag")
    if run_tag is not None and (not isinstance(run_tag, str) or not run_tag.strip()):
        raise PlanSchemaError("plan.run_tag must be a non-empty string when provided")

    return {
        "steps": steps,
        "project_root": project_root.strip() if isinstance(project_root, str) else None,
        "run_tag": run_tag.strip() if isinstance(run_tag, str) else None,
    }


# ---------------------------------------------------------------------------
# Bundle build (port of bundle_builder.build_plan_review_bundle)
# ---------------------------------------------------------------------------

_TASK_KEYS = ("task", "task_name", "task_label", "paradigm")
_CONTRAST_KEYS = ("contrast_name", "contrast_label", "contrast_id", "contrast")
_STUDY_KEYS = ("study_id", "dataset_id", "openneuro_dataset", "dataset")


def _first_string_param(
    steps: list[dict[str, Any]], keys: tuple[str, ...]
) -> str | None:
    for step in steps:
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        for key in keys:
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return None


def build_bundle(coerced: dict[str, Any], extraction: dict[str, Any]) -> dict[str, Any]:
    plan_steps: list[dict[str, Any]] = []
    declared_modalities: list[str] = []
    declared_spaces: list[str] = []

    for step in coerced["steps"]:
        params = step.get("params") or {}
        plan_steps.append(
            {
                "tool": step.get("tool") or "",
                "params": params,
                "step_id": step.get("step_id"),
            }
        )
        for key in extraction["modality_param_keys"]:
            val = params.get(key)
            if isinstance(val, str) and val:
                declared_modalities.append(val)
            elif isinstance(val, list):
                declared_modalities.extend(str(v) for v in val if v)
        for key in extraction["space_param_keys"]:
            val = params.get(key)
            if isinstance(val, str) and val:
                declared_spaces.append(val)
            elif isinstance(val, list):
                declared_spaces.extend(str(v) for v in val if v)

    kg_context: dict[str, Any] = {}
    if task := _first_string_param(plan_steps, _TASK_KEYS):
        kg_context["task"] = task
    if contrast := _first_string_param(plan_steps, _CONTRAST_KEYS):
        kg_context["contrast"] = contrast
    if study := _first_string_param(plan_steps, _STUDY_KEYS):
        kg_context["study_id"] = study

    return {
        "plan_steps": plan_steps,
        "declared_modalities": list(
            dict.fromkeys(m.lower() for m in declared_modalities)
        ),
        "declared_spaces": list(dict.fromkeys(declared_spaces)),
        "kg_context": kg_context,
    }


# ---------------------------------------------------------------------------
# Metric-rule evaluation (port of rule_engine.evaluate_plan metric path)
# ---------------------------------------------------------------------------


def _get_from_context(context: Any, path: str) -> Any:
    cursor: Any = context
    for part in path.split("."):
        if isinstance(cursor, dict) and part in cursor:
            cursor = cursor[part]
        else:
            return None
    return cursor


def _finding_from_rule(rule: dict[str, Any], *, step_id: str | None) -> dict[str, Any]:
    return {
        "rule_id": rule["rule_id"],
        "severity": rule["severity"],
        "action": rule["action"],
        "message": rule["message"],
        "suggested_fix": rule.get("suggested_fix"),
        "step_id": step_id,
        "tags": list(rule.get("tags") or []),
        "reason_tags": [],
        "kg_evidence": [],
    }


def evaluate_metric_rules(
    bundle: dict[str, Any], metric_rules: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    plan_steps = bundle["plan_steps"]
    plan_context = {"step_count": len(plan_steps)}

    for rule in metric_rules:
        metric = rule["metric"]
        comparator = rule["comparator"]
        op = _OPS.get(comparator)
        if op is None:
            continue
        threshold = rule.get("threshold")

        if metric.startswith("plan."):
            value = _get_from_context(plan_context, metric[len("plan.") :])
            if _violates(op, comparator, value, threshold):
                findings.append(_finding_from_rule(rule, step_id=None))
        elif metric.startswith("params."):
            param_key = metric[len("params.") :]
            tool_filter = rule.get("tool_filter")
            filt = {t.lower() for t in tool_filter} if tool_filter else None
            for step in plan_steps:
                tool = str(step.get("tool") or "").lower()
                if filt is not None and tool not in filt:
                    continue
                params = step.get("params") or {}
                value = _get_from_context(params, param_key)
                if value is None:
                    continue
                if _violates(op, comparator, value, threshold):
                    findings.append(
                        _finding_from_rule(rule, step_id=step.get("step_id"))
                    )
    return findings


def _violates(op, comparator: str, value: Any, threshold: Any) -> bool:
    try:
        if comparator == "missing":
            return value is None
        if value is None:
            return False
        return bool(op(value, threshold))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Structural check functions (port of checks/tool_order + checks/space_compat)
# ---------------------------------------------------------------------------


def _tool_name(step: dict[str, Any]) -> str:
    return str(step.get("tool") or "").lower()


def _first_index(steps: list[dict[str, Any]], toolset: set[str]) -> int | None:
    for idx, step in enumerate(steps):
        if _tool_name(step) in toolset:
            return idx
    return None


def registration_before_atlas_analysis(bundle, sets, rule):
    steps = bundle["plan_steps"]
    reg = _first_index(steps, set(sets["registration_tools"]))
    atlas = _first_index(steps, set(sets["atlas_tools"]))
    if atlas is None or reg is None:
        return None
    if atlas < reg:
        f = _finding_from_rule(rule, step_id=steps[atlas].get("step_id"))
        f["message"] = (
            f"Atlas/parcellation step '{steps[atlas].get('tool')}' (step {atlas + 1}) "
            f"precedes registration step '{steps[reg].get('tool')}' (step {reg + 1}); "
            "results will be in wrong space."
        )
        f["suggested_fix"] = (
            "Move the registration step before any atlas/parcellation step."
        )
        return f
    return None


def skull_stripping_before_registration(bundle, sets, rule):
    steps = bundle["plan_steps"]
    reg = _first_index(steps, set(sets["registration_tools"]))
    strip = _first_index(steps, set(sets["skull_strip_tools"]))
    if reg is None or strip is None:
        return None
    if reg < strip:
        f = _finding_from_rule(rule, step_id=steps[reg].get("step_id"))
        f["message"] = (
            f"Registration step '{steps[reg].get('tool')}' (step {reg + 1}) "
            f"precedes skull-stripping step '{steps[strip].get('tool')}' (step {strip + 1}); "
            "registering with skull may degrade accuracy."
        )
        f["suggested_fix"] = (
            "Skull-strip (bet, antsBrainExtraction) before registration."
        )
        return f
    return None


def confound_regression_before_glm(bundle, sets, rule):
    steps = bundle["plan_steps"]
    glm = _first_index(steps, set(sets["glm_tools_order"]))
    conf = _first_index(steps, set(sets["confound_tools"]))
    if glm is None:
        return None
    if conf is None or conf > glm:
        f = _finding_from_rule(rule, step_id=steps[glm].get("step_id"))
        f["message"] = (
            f"GLM step '{steps[glm].get('tool')}' (step {glm + 1}) "
            "found but no confound regression step precedes it."
        )
        f["suggested_fix"] = (
            "Add a confound regression step (e.g. confound_regression, nilearn_clean_img) "
            "before GLM to remove motion and physiological noise."
        )
        return f
    return None


def atlas_modality_compatible(bundle, sets, rule):
    modalities = {m.lower() for m in bundle["declared_modalities"]}
    spaces = set(bundle["declared_spaces"])
    eeg_meg = {m.lower() for m in sets["eeg_meg_modalities"]}
    mni = set(sets["volumetric_mni_spaces"])
    has_eeg_meg = bool(modalities & eeg_meg)
    has_mni = bool(spaces & mni)
    if has_eeg_meg and has_mni:
        f = _finding_from_rule(rule, step_id=None)
        f["message"] = (
            f"Modalities {sorted(modalities & eeg_meg)} combined with volumetric MNI "
            f"space/atlas {sorted(spaces & mni)} - modality/space mismatch."
        )
        f["suggested_fix"] = (
            "Use a surface-based or EEG-compatible atlas (e.g. fsaverage) "
            "or source imaging in MNI space."
        )
        return f
    return None


def dwi_tool_on_bold_data(bundle, sets, rule):
    modalities = {m.lower() for m in bundle["declared_modalities"]}
    tools_lower = {str(s.get("tool") or "").lower() for s in bundle["plan_steps"]}
    bold = set(sets["bold_modalities"])
    dwi = {t.lower() for t in sets["dwi_tools_space"]}
    if (modalities & bold) and (tools_lower & dwi):
        offending = sorted(tools_lower & dwi)
        f = _finding_from_rule(rule, step_id=None)
        f["message"] = f"DWI tool(s) {offending} declared alongside BOLD/fMRI modality."
        f["suggested_fix"] = (
            "Separate DWI and fMRI pipelines; do not mix tractography steps with BOLD GLM."
        )
        return f
    return None


def mixed_mni_versions(bundle, sets, rule):
    spaces = set(bundle["declared_spaces"])
    for step in bundle["plan_steps"]:
        params = step.get("params") or {}
        for key in ("space", "target_space", "atlas_space", "output_space"):
            val = params.get(key)
            if isinstance(val, str) and val:
                spaces.add(val)
    has_2009c = any("2009" in s or "NLin2009" in s for s in spaces)
    has_6 = any("NLin6" in s or "6Asym" in s for s in spaces)
    if has_2009c and has_6:
        f = _finding_from_rule(rule, step_id=None)
        f["message"] = (
            "Both MNI152NLin2009cAsym and MNI152NLin6Asym detected in the same plan."
        )
        f["suggested_fix"] = (
            "Use MNI152NLin2009cAsym throughout (fMRIPrep default). "
            "MNI152NLin6Asym is the FSL standard - choose one consistently."
        )
        return f
    return None


# ---------------------------------------------------------------------------
# Method appropriateness (port of checks/method_appropriateness.py, seed path)
# ---------------------------------------------------------------------------


def _resolve_canonical(text: str, alias_map: dict[str, list[str]]) -> str | None:
    text_lower = text.strip().lower()
    if text_lower in alias_map:
        return text_lower
    for canonical, aliases in alias_map.items():
        if text_lower in aliases or text_lower == canonical:
            return canonical
    return None


def _collect_text_hints(bundle: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    for step in bundle["plan_steps"]:
        tool = str(step.get("tool") or "").strip()
        if tool:
            hints.append(tool)
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        for value in params.values():
            if isinstance(value, str) and value.strip():
                hints.append(value.strip())
            elif isinstance(value, bool):
                hints.append("true" if value else "false")
    for value in bundle.get("kg_context", {}).values():
        if isinstance(value, str) and value.strip():
            hints.append(value.strip())
    return hints


def _infer_design_type(bundle, seed):
    hints = _collect_text_hints(bundle)
    design_aliases = seed["design_aliases"]
    design_param_keys = seed["method_inference"]["design_param_keys"]
    design_type_param_keys = seed["method_inference"]["design_type_param_keys"]

    for step in bundle["plan_steps"]:
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        for param_key, canonical in design_param_keys.items():
            if bool(params.get(param_key)):
                return canonical, hints

    for step in bundle["plan_steps"]:
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        explicit = None
        for k in design_type_param_keys:
            if isinstance(params.get(k), str) and params.get(k).strip():
                explicit = params.get(k)
                break
        if isinstance(explicit, str) and explicit.strip():
            resolved = _resolve_canonical(explicit, design_aliases)
            if resolved:
                return resolved, hints

    joined = " ".join(hints).lower()
    for canonical, aliases in design_aliases.items():
        if canonical in joined:
            return canonical, hints
        for alias in aliases:
            if alias in joined:
                return canonical, hints
    return None, hints


def _infer_method_type(bundle, seed):
    hints = _collect_text_hints(bundle)
    method_aliases = seed["method_aliases"]
    method_param_keys = seed["method_inference"]["method_param_keys"]

    for step in bundle["plan_steps"]:
        params = step.get("params") if isinstance(step.get("params"), dict) else {}
        explicit = None
        for k in method_param_keys:
            if isinstance(params.get(k), str) and params.get(k).strip():
                explicit = params.get(k)
                break
        if isinstance(explicit, str) and explicit.strip():
            resolved = _resolve_canonical(explicit, method_aliases)
            if resolved:
                return resolved, hints

    for step in bundle["plan_steps"]:
        tool = str(step.get("tool") or "").strip().lower()
        if not tool:
            continue
        resolved = _resolve_canonical(tool, method_aliases)
        if resolved:
            return resolved, hints

    joined = " ".join(hints).lower()
    for canonical, aliases in method_aliases.items():
        if canonical in joined:
            return canonical, hints
        for alias in aliases:
            if alias in joined:
                return canonical, hints
    return None, hints


def _query_seed_compatibility(design_type, method_type, seed):
    design_aliases = seed["design_aliases"]
    method_aliases = seed["method_aliases"]
    canonical_design = _resolve_canonical(design_type, design_aliases) or design_type
    canonical_method = _resolve_canonical(method_type, method_aliases) or method_type
    for rule in seed["rules"]:
        rule_design = _resolve_canonical(str(rule.get("design") or ""), design_aliases)
        rule_method = _resolve_canonical(str(rule.get("method") or ""), method_aliases)
        if rule_design == canonical_design and rule_method == canonical_method:
            return {
                "rule_id": rule.get("id", f"{canonical_design}_vs_{canonical_method}"),
                "compatible": rule.get("compatible"),
                "severity": rule.get("severity", "error"),
                "rationale": rule.get("rationale"),
                "evidence": rule.get("evidence"),
                "message": rule.get("rationale"),
                "suggested_fix": rule.get("suggested_fix"),
                "source": "seed",
            }
    return None


def _is_incompatible(payload: dict[str, Any]) -> bool:
    if payload.get("compatible") is False:
        return True
    status = (
        str(payload.get("status") or payload.get("compatibility") or "").strip().lower()
    )
    return status in {"incompatible", "mismatch", "disallowed", "invalid"}


def method_appropriateness_check(bundle, sets, rule, seed):
    design_type, design_hints = _infer_design_type(bundle, seed)
    method_type, method_hints = _infer_method_type(bundle, seed)
    if design_type is None or method_type is None:
        return None
    payload = _query_seed_compatibility(design_type, method_type, seed)
    if not payload or not _is_incompatible(payload):
        return None

    kg_evidence: list[str] = []
    rationale = payload.get("rationale")
    if isinstance(rationale, str) and rationale.strip():
        kg_evidence.append(rationale.strip())
    structured_evidence = payload.get("evidence")
    if isinstance(structured_evidence, dict):
        for key, value in structured_evidence.items():
            if value is not None:
                kg_evidence.append(f"{key}={value}")
    kg_evidence.append("curated method compatibility seed")
    if design_hints:
        kg_evidence.append(f"Design hints: {', '.join(sorted(set(design_hints[:8])))}.")
    if method_hints:
        kg_evidence.append(f"Method hints: {', '.join(sorted(set(method_hints[:8])))}.")

    seed_rule_id = str(
        payload.get("rule_id") or f"REVIEW_{design_type}_{method_type}_MISMATCH"
    ).upper()

    # The engine's rule-metadata merge forces severity/action from the
    # REVIEW_METHOD_APPROPRIATENESS rule (error/block) regardless of seed severity.
    return {
        "rule_id": seed_rule_id,
        "severity": rule["severity"],
        "action": rule["action"],
        "message": str(
            payload.get("message")
            or f"Design '{design_type}' is incompatible with method '{method_type}'."
        ),
        "suggested_fix": str(
            payload.get("suggested_fix")
            or "Choose a statistical method that matches the study design's "
            "independence/dependence structure."
        ),
        "step_id": None,
        "tags": list(rule.get("tags") or []),
        "reason_tags": [],
        "kg_evidence": kg_evidence,
        "detected_design": design_type,
        "detected_method": method_type,
        "seed_severity": payload.get("severity"),
    }


_STRUCTURAL_DISPATCH = {
    "registration_before_atlas_analysis": registration_before_atlas_analysis,
    "skull_stripping_before_registration": skull_stripping_before_registration,
    "confound_regression_before_glm": confound_regression_before_glm,
    "atlas_modality_compatible": atlas_modality_compatible,
    "dwi_tool_on_bold_data": dwi_tool_on_bold_data,
    "mixed_mni_versions": mixed_mni_versions,
}


def evaluate_structural_rules(bundle, structural_rules, sets, seed):
    findings = []
    for rule in structural_rules:
        check = rule["check"]
        if check == "method_appropriateness_check":
            f = method_appropriateness_check(bundle, sets, rule, seed)
        else:
            fn = _STRUCTURAL_DISPATCH.get(check)
            f = fn(bundle, sets, rule) if fn else None
        if f is not None:
            findings.append(f)
    return findings


# ---------------------------------------------------------------------------
# Roll-up + checklist + rationale (port of verdict_builder)
# ---------------------------------------------------------------------------


def roll_up_decision(findings: list[dict[str, Any]]) -> tuple[str, str]:
    if not findings:
        return "approve", "low"
    severities = {f["severity"] for f in findings}
    has_block_action = any(f.get("action", "warn") == "block" for f in findings)
    if has_block_action or "critical" in severities:
        return "block", "critical"
    if "error" in severities:
        return "revise", "high"
    if "warn" in severities:
        return "approve_with_warnings", "medium"
    return "approve", "low"


def generate_checklist(
    bundle: dict[str, Any], checklist_sets: dict[str, Any]
) -> list[str]:
    checklist: list[str] = []
    steps = bundle["plan_steps"]
    tools_lower = [str(s.get("tool") or "").lower() for s in steps]

    checklist.append(f"Plan has {len(steps)} step(s)")
    if bundle["declared_modalities"]:
        checklist.append(
            f"Declared modalities: {', '.join(bundle['declared_modalities'])}"
        )
    if bundle["declared_spaces"]:
        checklist.append(f"Declared spaces: {', '.join(bundle['declared_spaces'])}")

    reg = set(checklist_sets["registration"])
    glm = set(checklist_sets["glm"])
    conf = set(checklist_sets["confound"])
    has_registration = any(t in reg for t in tools_lower)
    has_glm = any(t in glm for t in tools_lower)
    has_confound = any(t in conf for t in tools_lower)

    checklist.append(f"Registration step present: {has_registration}")
    if has_glm:
        checklist.append(f"GLM step present: {has_glm}")
        checklist.append(f"Confound regression before GLM: {has_confound}")

    tr_values = [
        s.get("params", {}).get("tr")
        for s in steps
        if isinstance(s.get("params"), dict) and s["params"].get("tr") is not None
    ]
    if tr_values:
        checklist.append(f"TR values in plan: {tr_values}")
    fwhm_values = [
        s.get("params", {}).get("fwhm")
        for s in steps
        if isinstance(s.get("params"), dict) and s["params"].get("fwhm") is not None
    ]
    if fwhm_values:
        checklist.append(f"FWHM values in plan: {fwhm_values}")
    return checklist


def build_rationale(findings: list[dict[str, Any]], decision: str) -> str:
    if not findings:
        return f"Plan review passed all checks. Decision: {decision}."
    lines = [f"Plan review - Decision: {decision}. {len(findings)} finding(s):"]
    for f in findings:
        lines.append(f"  [{f['severity'].upper()}] {f['rule_id']}: {f['message']}")
    return " | ".join(lines)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def validate(plan_raw: dict[str, Any]) -> dict[str, Any]:
    rules = _load_json("plan_review_rules.json")
    seed = _load_json("method_compatibility_seed.json")

    try:
        coerced = coerce_plan(plan_raw)
    except PlanSchemaError as exc:
        return {
            "ok": False,
            "schema_error": str(exc),
            "decision": "block",
            "risk_level": "critical",
            "findings": [],
            "checklist_generated": [],
            "reviewer_rationale": f"Plan rejected at schema coercion: {exc}",
            "engine": {"use_kg": False, "rules_source": "plan_review_rules.json"},
        }

    bundle = build_bundle(coerced, rules["bundle_extraction"])

    findings = evaluate_metric_rules(bundle, rules["metric_rules"])
    findings += evaluate_structural_rules(
        bundle, rules["structural_rules"], rules["tool_sets"], seed
    )

    decision, risk_level = roll_up_decision(findings)
    checklist = generate_checklist(bundle, rules["checklist_tool_sets"])
    rationale = build_rationale(findings, decision)

    n_error = sum(1 for f in findings if f["severity"] in ("error", "critical"))
    n_warn = sum(1 for f in findings if f["severity"] == "warn")
    n_block = sum(1 for f in findings if f.get("action") == "block")
    ok = n_error == 0 and n_block == 0

    return {
        "ok": ok,
        "schema_error": None,
        "decision": decision,
        "risk_level": risk_level,
        "findings": findings,
        "counts": {
            "error": n_error,
            "warn": n_warn,
            "block": n_block,
            "total": len(findings),
        },
        "checklist_generated": checklist,
        "reviewer_rationale": rationale,
        "normalized_plan": {
            "project_root": coerced["project_root"],
            "run_tag": coerced["run_tag"],
            "steps": coerced["steps"],
        },
        "detected_context": bundle["kg_context"],
        "engine": {
            "use_kg": False,
            "rules_source": "references/plan_review_rules.json",
            "seed_source": "references/method_compatibility_seed.json",
            "n_metric_rules": len(rules["metric_rules"]),
            "n_structural_rules": len(rules["structural_rules"]),
        },
    }


def _read_input(path: str) -> dict[str, Any]:
    if path == "-":
        raw = json.loads(sys.stdin.read())
    else:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, dict) and "plan" in raw and isinstance(raw["plan"], dict):
        return raw["plan"]
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline plan validator (pipeline_plan_validate, use_kg=False)."
    )
    parser.add_argument("plan", help="Path to plan JSON, or '-' for stdin.")
    parser.add_argument(
        "--compact", action="store_true", help="Compact one-line JSON output."
    )
    args = parser.parse_args(argv)

    try:
        plan_raw = _read_input(args.plan)
    except (OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps({"ok": False, "error": f"could not read plan JSON: {exc}"}),
            file=sys.stderr,
        )
        return 2

    result = validate(plan_raw)
    print(json.dumps(result, indent=None if args.compact else 2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
