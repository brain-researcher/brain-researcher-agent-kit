#!/usr/bin/env python3
"""List and (optionally) score a NeuroProgram design family (deterministic, offline, stdlib-only).

Ports the magnitude-free design-family kernel from
``brain_researcher/autoresearch/society/optimize.py``:
  - ``_ga_axes``               -> pre-registered options per coverage axis (fail-closed on malformed)
  - ``_prior_is_degenerate``   -> near-delta prior detection (>= 0.99 mass on one option)
  - forced-exploratory logic   -> degenerate-prior / unknown-constraint downgrade
  - ``_coverage_entropy``      -> normalized entropy over the FULL axis space
  - ``make_count_efficiency_fn`` -> events-free, value-free DOF efficiency proxy
  - ``score_design_family``    -> magnitude-free DesignFamilyScore + eligibility floors

This enumerates the PRE-REGISTERED design space a program commits to searching, reports
whether the claim would be forced exploratory, and — if the caller supplies an explicit
``variants`` list — scores that family on magnitude-free properties only. NONE of the
scoring reads any result, z-map, or confounds value; a variant may carry only its
``decision_points`` and an optional ``blocked`` flag (the review verdict).

Usage:
    python scripts/list_design_family.py [program.json]

``program.json`` (defaults to references/example_design_family.json) is an object with:
    - ``design_priors``:        dict[axis, dict[option, weight]] (optional)
    - ``claim_mode``:           "confirmatory" | "exploratory"    (optional)
    - ``prior_provenance``:     str | null                        (optional)
    - ``unknown_constraints``:  list[str]                         (optional)
    - ``variants``:             list[{variant_id?, decision_points|.., blocked?}] (optional)

Prints a JSON report to stdout. Exit code 0 iff no reject-severity findings, 1 otherwise.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def _taxonomy_path() -> Path:
    return (
        Path(__file__).resolve().parents[1] / "references" / "design_axis_taxonomy.json"
    )


def _load_taxonomy(path: Path | None = None) -> dict[str, Any]:
    path = path or _taxonomy_path()
    return json.loads(path.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _decision_points(variant: dict[str, Any]) -> dict[str, Any]:
    """Accept either a nested {decision_points: {...}} or a flat decision-points dict."""
    if isinstance(variant.get("decision_points"), dict):
        return variant["decision_points"]
    return variant


# --------------------------------------------------------------------------------------
# pre-registered axis enumeration (port of _ga_axes: fail-closed on a malformed axis)
# --------------------------------------------------------------------------------------
def preregistered_axes(
    priors: dict[str, Any] | None, taxonomy: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    full_axes = taxonomy["full_axes"]
    coverage_axes = taxonomy["coverage_axes"]
    axes: dict[str, dict[str, Any]] = {}
    findings: list[dict[str, Any]] = []
    priors = priors or {}
    for axis in coverage_axes:
        full = list(full_axes[axis])
        if axis not in priors:
            # axis NOT pre-registered -> full catalog (the no-prior default)
            axes[axis] = {
                "options": full,
                "source": "full_catalog (axis not pre-registered)",
            }
            continue
        dist = priors.get(axis)
        if isinstance(dist, dict) and dist:
            pos = [k for k, w in dist.items() if _is_number(w) and float(w) > 0]
            if pos:
                axes[axis] = {"options": pos, "source": "prior positive-weight options"}
            else:
                # present but no positive weight -> fall back to declared keys, NOT the catalog
                axes[axis] = {
                    "options": list(dist.keys()),
                    "source": "declared keys (no positive weight)",
                }
        else:
            # declared but empty ({}) or non-dict -> fail CLOSED (never expand to full catalog)
            findings.append(
                {
                    "severity": "reject",
                    "code": "malformed_prior_axis",
                    "axis": axis,
                    "value": dist,
                    "reason": (
                        f"design_priors axis {axis!r} is declared but has no usable options "
                        f"({dist!r}); provide a non-empty {{value: weight}} mapping or omit the axis. "
                        "Fail-closed: a malformed axis must NOT silently expand to the full catalog "
                        "(that would let a search mutate into un-pre-registered values)."
                    ),
                }
            )
            axes[axis] = {"options": [], "source": "INVALID"}
    return axes, findings


# --------------------------------------------------------------------------------------
# degenerate-prior detection (port of _prior_is_degenerate)
# --------------------------------------------------------------------------------------
def degenerate_axes(
    priors: dict[str, Any] | None, taxonomy: dict[str, Any]
) -> list[str]:
    threshold = float(taxonomy["degenerate_prior_threshold"])
    coverage_axes = taxonomy["coverage_axes"]
    out: list[str] = []
    if not priors:
        return out
    for axis in coverage_axes:
        dist = priors.get(axis)
        if not isinstance(dist, dict) or not dist:
            continue
        weights = [float(w) for w in dist.values() if _is_number(w)]
        total = sum(w for w in weights if w > 0)
        if total <= 0:
            continue
        if any(w / total >= threshold for w in weights):
            out.append(axis)
    return out


# --------------------------------------------------------------------------------------
# magnitude-free coverage entropy (port of _coverage_entropy)
# --------------------------------------------------------------------------------------
def coverage_entropy(
    specs: list[dict[str, Any]], taxonomy: dict[str, Any]
) -> tuple[float, int]:
    full_axes = taxonomy["full_axes"]
    coverage_axes = taxonomy["coverage_axes"]
    total = 0.0
    n_axes = 0
    varied = 0
    for axis in coverage_axes:
        n_axes += 1
        counts: dict[str, int] = {}
        for dp in specs:
            v = str(dp.get(axis, ""))
            counts[v] = counts.get(v, 0) + 1
        distinct = len([v for v in counts if v])
        if distinct >= 2:
            varied += 1
        if not counts:
            continue
        n = sum(counts.values())
        ent = -sum((c / n) * math.log(c / n) for c in counts.values() if c)
        # normalize by log of the FULL axis size and clamp to 1.0 (anti-gaming ceiling)
        max_ent = math.log(max(len(full_axes[axis]), 1)) or 1.0
        total += min(1.0, ent / max_ent)
    coverage = total / n_axes if n_axes else 0.0
    return coverage, varied


# --------------------------------------------------------------------------------------
# events-free, value-free efficiency proxy (port of make_count_efficiency_fn)
# --------------------------------------------------------------------------------------
def count_efficiency(dp: dict[str, Any], taxonomy: dict[str, Any]) -> float:
    conf_counts = taxonomy["confound_regressor_counts"]
    hrf_extra = taxonomy["hrf_extra_regressors"]
    n_conf = conf_counts.get(str(dp.get("confounds", "6mot")), 6)
    extra = hrf_extra.get(str(dp.get("hrf_basis", "canonical")), 0)
    return 1.0 / (1.0 + n_conf + extra)


# --------------------------------------------------------------------------------------
# magnitude-free family score (port of score_design_family)
# --------------------------------------------------------------------------------------
def score_family(
    variants: list[dict[str, Any]], taxonomy: dict[str, Any]
) -> dict[str, Any]:
    floors = taxonomy["eligibility_floors"]
    min_variants = int(floors["MIN_VARIANTS"])
    min_axes_varied = int(floors["MIN_AXES_VARIED"])
    min_mean_eff = float(floors["MIN_MEAN_EFFICIENCY"])

    passing: list[tuple[str, dict[str, Any]]] = []
    disqualified: list[str] = []
    seen: set[str] = set()
    for i, v in enumerate(variants):
        dp = _decision_points(v)
        vid = str(v.get("variant_id", i))
        if bool(
            v.get("blocked", False)
        ):  # a blocking review finding disqualifies (hard cut)
            disqualified.append(vid)
            continue
        if (
            vid in seen
        ):  # de-duplicate: a committed multiverse is a SET of DISTINCT pipelines
            continue
        seen.add(vid)
        passing.append((vid, dp))

    specs = [dp for _vid, dp in passing]
    coverage, n_varied = coverage_entropy(specs, taxonomy)
    effs = [count_efficiency(dp, taxonomy) for dp in specs]
    mean_eff = sum(effs) / len(effs) if effs else 0.0
    if len(effs) >= 2 and mean_eff > 0:
        std = (sum((e - mean_eff) ** 2 for e in effs) / len(effs)) ** 0.5
        cv = std / mean_eff
        eff_stability = 1.0 / (1.0 + cv)
    else:
        eff_stability = 0.0
    n_pass = len(specs)
    constraint_pass_frac = n_pass / len(variants) if variants else 0.0
    est_cost = float(n_pass)  # you only run the passing variants

    eligible = True
    reason = ""
    if n_pass < min_variants:
        eligible, reason = (
            False,
            f"passing variants {n_pass} < MIN_VARIANTS={min_variants}",
        )
    elif n_varied < min_axes_varied:
        eligible, reason = (
            False,
            f"family varies on only {n_varied} axes (< {min_axes_varied})",
        )
    elif not effs or mean_eff < min_mean_eff:
        eligible, reason = False, "no estimable variant (mean_efficiency below floor)"

    return {
        "variant_ids": [vid for vid, _dp in passing],
        "coverage": coverage,
        "mean_efficiency_floor_only": mean_eff,
        "efficiency_stability_maximized": eff_stability,
        "constraint_pass_frac": constraint_pass_frac,
        "est_cost_units": est_cost,
        "n_axes_varied": n_varied,
        "disqualified_variants": disqualified,
        "eligible": eligible,
        "ineligible_reason": reason,
        "magnitude_free_inputs": True,
        "note": "no result, z-map, or confounds value was read; scores depend only on the design.",
    }


def analyze(program: dict[str, Any], taxonomy: dict[str, Any]) -> dict[str, Any]:
    priors = program.get("design_priors")
    axes, axis_findings = preregistered_axes(priors, taxonomy)
    findings = list(axis_findings)

    deg_axes = degenerate_axes(priors, taxonomy)
    degenerate = bool(deg_axes)

    declared_mode = program.get("claim_mode", "confirmatory")
    if declared_mode not in ("confirmatory", "exploratory"):
        declared_mode = "confirmatory"
    prior_provenance = program.get("prior_provenance")
    unknown_constraints = program.get("unknown_constraints") or []

    effective_mode = declared_mode
    forced_reasons: list[str] = []
    if degenerate and not prior_provenance:
        effective_mode = "exploratory"
        forced_reasons.append(
            "degenerate (near-delta) design prior on "
            + ", ".join(deg_axes)
            + " with no pre-data prior_provenance attestation"
        )
    if unknown_constraints:
        effective_mode = "exploratory"
        forced_reasons.append(
            "declared constraint(s) unknown to the review engine (fail-closed): "
            + ", ".join(str(c) for c in unknown_constraints)
        )

    # design-space cardinalities (cartesian product of options)
    n_prereg = 1
    for axis in taxonomy["coverage_axes"]:
        n_prereg *= max(len(axes[axis]["options"]), 1)
    n_full = 1
    for axis in taxonomy["coverage_axes"]:
        n_full *= len(taxonomy["full_axes"][axis])

    result: dict[str, Any] = {
        "ok": True,
        "program_id": program.get("program_id"),
        "design_space": {
            "coverage_axes": taxonomy["coverage_axes"],
            "preregistered_axes": axes,
            "n_preregistered_combinations": n_prereg,
            "n_full_axis_combinations": n_full,
        },
        "degenerate_prior": degenerate,
        "degenerate_axes": deg_axes,
        "declared_claim_mode": declared_mode,
        "effective_claim_mode": effective_mode,
        "forced_exploratory_reasons": forced_reasons,
        "eligibility_floors": taxonomy["eligibility_floors"],
        "findings": findings,
    }

    variants = program.get("variants")
    if isinstance(variants, list) and variants:
        result["family_score"] = score_family(variants, taxonomy)

    rejects = [f for f in findings if f.get("severity") == "reject"]
    result["ok"] = not rejects
    result["n_reject"] = len(rejects)
    return result


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    input_path = (
        Path(args[0]).expanduser().resolve()
        if args
        else (
            Path(__file__).resolve().parents[1]
            / "references"
            / "example_design_family.json"
        )
    )
    if not input_path.exists():
        print(
            json.dumps({"ok": False, "error": f"input not found: {input_path}"}),
            file=sys.stderr,
        )
        return 2
    program = json.loads(input_path.read_text(encoding="utf-8"))
    taxonomy = _load_taxonomy()
    result = analyze(program, taxonomy)
    result["input"] = str(input_path)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
