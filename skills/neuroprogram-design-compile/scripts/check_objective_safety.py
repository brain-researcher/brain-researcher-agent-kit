#!/usr/bin/env python3
"""Objective-safety gate for a NeuroProgram (deterministic, offline, stdlib-only).

Ports the load-bearing objective-safety invariant from
``brain_researcher/autoresearch/society/neuroprogram.py`` (NeuroObjectiveV1,
_FORBIDDEN_OBJECTIVE_SUBSTRINGS, _reject_magnitude_objectives) and the weight
validation in ``optimize.py`` (optimize_design_family).

A NeuroProgram's ``objectives`` may ONLY target validity / robustness / coverage.
Optimizing a result MAGNITUDE (effect size, novelty, significance, association,
p-value, z-score) over a design space is automated garden-of-forking-paths and is
REJECTED. This script re-implements that check bit-for-bit so a reviewer can run it
on any caller-supplied program JSON without a server.

Usage:
    python scripts/check_objective_safety.py [program.json]

``program.json`` (defaults to references/example_program.json) is an object with:
    - ``objectives``: list[str]        (required for a meaningful check)
    - ``weights``:    dict[str, float] (optional; objective -> weight)

Prints a JSON findings report to stdout. Exit code 0 iff objective-safe (no
reject-severity findings), 1 otherwise.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def _rules_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "references"
        / "objective_safety_rules.json"
    )


def _load_rules(path: Path | None = None) -> dict[str, Any]:
    path = path or _rules_path()
    return json.loads(path.read_text(encoding="utf-8"))


def _is_number(value: Any) -> bool:
    # bool is a subclass of int in Python; a boolean weight is not a valid number.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_objectives(program: dict[str, Any], rules: dict[str, Any]) -> dict[str, Any]:
    """Validate a program's objectives and weights against the objective-safety rules."""
    allowed = set(rules["allowed_objectives"])
    forbidden = list(rules["forbidden_objective_substrings"])
    dimension_map = dict(rules["objective_dimension_map"])
    magnitude_free = set(rules["magnitude_free_dimensions"])
    min_weight = float(rules["weight_constraints"]["min"])

    findings: list[dict[str, Any]] = []
    checked: list[dict[str, Any]] = []

    objectives = program.get("objectives") or []
    if not isinstance(objectives, list):
        findings.append(
            {
                "severity": "reject",
                "code": "objectives_not_a_list",
                "reason": "program 'objectives' must be a list of objective strings.",
            }
        )
        objectives = []

    for obj in objectives:
        # Mechanism 2: forbidden-substring check runs BEFORE any enum/label match, so a
        # magnitude objective cannot be smuggled past the typed enum as free text.
        text = str(obj).strip().lower()
        matched = next((bad for bad in forbidden if bad in text), None)
        if matched is not None:
            findings.append(
                {
                    "severity": "reject",
                    "code": "magnitude_objective",
                    "objective": obj,
                    "matched_substring": matched,
                    "reason": (
                        f"objective {obj!r} optimizes a result magnitude ({matched!r}) — "
                        "forbidden. Optimizing effect size / novelty / significance / association "
                        "over a design space is automated garden-of-forking-paths. Objectives must "
                        "target validity, robustness, or coverage; magnitude is a constraint and a "
                        "reported quantity, never an optimization target."
                    ),
                }
            )
            checked.append(
                {"objective": obj, "verdict": "rejected", "matched_substring": matched}
            )
            continue

        # Mechanism 1 (PRIMARY): the typed enum is a CLOSED whitelist of exactly five members.
        # An objective outside it fails enum coercion server-side (NeuroObjectiveV1(name) raises
        # ValueError), so it is REJECTED there — and must be rejected here too, or a magnitude
        # objective that contains no blacklisted substring (e.g. "maximize_detection_power") would
        # slip past mechanism 2 (the substring blacklist) and defeat the whole gate. Reject-parity
        # with the server, not a warning.
        if text in allowed:
            checked.append(
                {
                    "objective": obj,
                    "verdict": "allowed",
                    "score_dimension": dimension_map.get(text),
                }
            )
        else:
            findings.append(
                {
                    "severity": "reject",
                    "code": "objective_not_in_allowlist",
                    "objective": obj,
                    "reason": (
                        "not one of the closed set of allowed validity/robustness/coverage "
                        f"objectives ({sorted(allowed)}); the typed NeuroObjectiveV1 enum REJECTS "
                        "it server-side (ValueError), so it is rejected here for parity — this "
                        "closes the substring-blacklist evasion hole (e.g. detection-power gaming)."
                    ),
                }
            )
            checked.append({"objective": obj, "verdict": "rejected"})

    # Weight validation (optimize_design_family): finite and non-negative. A negative weight
    # would invert a maximize-objective while still reporting the safe label.
    weights = program.get("weights") or {}
    if not isinstance(weights, dict):
        findings.append(
            {
                "severity": "reject",
                "code": "weights_not_a_mapping",
                "reason": "program 'weights' must be an object of objective -> number.",
            }
        )
        weights = {}
    for name, val in weights.items():
        if (
            not _is_number(val)
            or not math.isfinite(float(val))
            or float(val) < min_weight
        ):
            findings.append(
                {
                    "severity": "reject",
                    "code": "invalid_weight",
                    "weight": name,
                    "value": val,
                    "reason": (
                        f"objective weight {name}={val!r} must be a finite, non-negative number "
                        "(negative weights would invert a maximize-objective and are forbidden)."
                    ),
                }
            )

    # Mechanism 3 self-audit: the objective -> dimension map must never point at a magnitude
    # dimension. This validates the rule table itself, so a bad edit to the rules is caught.
    for obj_label, dim in dimension_map.items():
        if dim not in magnitude_free:
            findings.append(
                {
                    "severity": "reject",
                    "code": "map_reads_magnitude",
                    "objective": obj_label,
                    "dimension": dim,
                    "reason": (
                        f"objective->dimension map points {obj_label!r} at a magnitude dimension "
                        f"({dim!r}) — objective-safety is violated at the rule level."
                    ),
                }
            )

    rejects = [f for f in findings if f["severity"] == "reject"]
    warns = [f for f in findings if f["severity"] == "warn"]
    verdict = "rejected" if rejects else "objective_safe"

    return {
        "ok": not rejects,
        "verdict": verdict,
        "invariant": rules["invariant"],
        "n_objectives": len(objectives),
        "objectives": checked,
        "n_reject": len(rejects),
        "n_warn": len(warns),
        "findings": findings,
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    input_path = (
        Path(args[0]).expanduser().resolve()
        if args
        else (
            Path(__file__).resolve().parents[1] / "references" / "example_program.json"
        )
    )
    if not input_path.exists():
        print(
            json.dumps({"ok": False, "error": f"input not found: {input_path}"}),
            file=sys.stderr,
        )
        return 2
    program = json.loads(input_path.read_text(encoding="utf-8"))
    rules = _load_rules()
    result = check_objectives(program, rules)
    result["input"] = str(input_path)
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
