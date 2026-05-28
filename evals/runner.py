"""Small CLI that scores a demo's expected_output against its rubric.

Usage:
    python -m evals.runner --all
    python -m evals.runner --demo plan-validate-and-execute

The runner is intentionally minimal: it loads each rubric YAML, runs the
deterministic-check subset (presence + regex + JSON-field assertions),
and emits a per-demo scorecard. LLM-judge checks are out of scope at
v0.1.0 — they live in evals/autorater/ as a stub.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

from evals.checks import run_demo_checks

KIT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = KIT_ROOT / "examples"
RUBRICS_DIR = KIT_ROOT / "evals" / "rubrics"


def list_demos() -> list[str]:
    return sorted(
        p.name for p in EXAMPLES_DIR.iterdir() if (p / "rubric.yaml").is_file()
    )


def load_rubric(name: str) -> dict:
    path = RUBRICS_DIR / f"research-{name}.yaml"
    with path.open() as fh:
        return yaml.safe_load(fh)


def load_demo_rubric(demo: str) -> dict:
    path = EXAMPLES_DIR / demo / "rubric.yaml"
    with path.open() as fh:
        return yaml.safe_load(fh)


def expected_outputs_exist(demo: str) -> tuple[bool, list[str]]:
    out_dir = EXAMPLES_DIR / demo / "expected_output"
    if not out_dir.exists():
        return False, ["expected_output/ directory missing"]
    files = [p for p in out_dir.iterdir() if p.is_file()]
    if not files:
        return False, ["expected_output/ is empty — TODO: capture from BR MCP run"]
    return True, [p.name for p in files]


def score_demo(demo: str) -> dict:
    demo_rubric = load_demo_rubric(demo)
    captured, files_or_reasons = expected_outputs_exist(demo)
    result: dict = {
        "demo": demo,
        "captured": captured,
        "applied_rubrics": demo_rubric.get("apply", []),
        "demo_specific": demo_rubric.get("demo_specific", []),
    }
    if not captured:
        result["status"] = "not_captured"
        result["blocked_reasons"] = files_or_reasons
        return result

    result["expected_output_files"] = files_or_reasons
    rubric_load_failures: list[dict] = []
    for rubric_name in demo_rubric.get("apply", []):
        try:
            rubric = load_rubric(rubric_name)
        except FileNotFoundError:
            rubric_load_failures.append({"rubric": rubric_name, "error": "rubric_not_found"})
            continue
        result.setdefault("rubric_check_inventory", {})[rubric_name] = [
            {"id": chk["id"], "severity": chk["severity"]}
            for chk in rubric.get("checks", [])
        ]
    if rubric_load_failures:
        result["rubric_load_failures"] = rubric_load_failures

    # Run demo-specific deterministic checks.
    out_dir = EXAMPLES_DIR / demo / "expected_output"
    check_results = run_demo_checks(demo, out_dir)
    result["checks"] = check_results
    enforced = [c for c in check_results if not c.get("skipped")]
    failed = [c for c in enforced if not c["passed"]]
    if failed:
        result["status"] = "checks_failed"
        result["failed_check_ids"] = [c["id"] for c in failed]
    elif not enforced:
        result["status"] = "captured_no_checks_wired"
    else:
        result["status"] = "passed"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Score every demo.")
    group.add_argument("--demo", help="Score one demo by name.")
    args = parser.parse_args()

    demos = list_demos() if args.all else [args.demo]
    results = [score_demo(d) for d in demos]

    print(json.dumps({"results": results}, indent=2))

    blocked = [r for r in results if r["status"] == "not_captured"]
    failed = [r for r in results if r["status"] == "checks_failed"]
    if blocked:
        print(
            f"\n{len(blocked)} of {len(results)} demos have no captured expected_output;",
            "see TODO in each demo's README.",
            file=sys.stderr,
        )
        return 2
    if failed:
        ids = ", ".join(r["demo"] for r in failed)
        print(
            f"\n{len(failed)} of {len(results)} demos failed demo-specific checks: {ids}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
