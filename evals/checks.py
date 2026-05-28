"""Per-demo deterministic checks.

Each function takes the demo's `expected_output/` Path and returns a list of
{id, passed, detail} dicts. Functions never raise — missing or unparseable
files become `passed=False` with detail.

These mirror the `demo_specific` bullet lists in each demo's rubric.yaml,
upgraded to actual assertions.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> tuple[Any, str | None]:
    if not path.is_file():
        return None, f"missing file: {path.name}"
    try:
        return json.loads(path.read_text()), None
    except json.JSONDecodeError as e:
        return None, f"invalid JSON in {path.name}: {e}"


def _read_text(path: Path) -> tuple[str | None, str | None]:
    if not path.is_file():
        return None, f"missing file: {path.name}"
    return path.read_text(), None


def _walk(obj: Any):
    """Yield every dict/list/leaf encountered in a JSON tree."""
    yield obj
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def _find_field(obj: Any, key: str) -> Any:
    """Return the first value for `key` found anywhere in the JSON tree."""
    for node in _walk(obj):
        if isinstance(node, dict) and key in node:
            return node[key]
    return None


def check_cross_tool_handoff(out: Path) -> list[dict]:
    results: list[dict] = []
    chain, err = _read_json(out / "handoff_chain.json")
    if err:
        results.append({"id": "handoff_chain_present", "passed": False, "detail": err})
        return results

    # ≥4 rows with output_artifact_sha256 — accept the chain as a top-level
    # list, or nested under common keys.
    rows = chain if isinstance(chain, list) else None
    for key in ("chain", "steps", "rows"):
        if rows is None:
            rows = _find_field(chain, key)
    if not isinstance(rows, list):
        rows = []
    sha_rows = [r for r in rows if isinstance(r, dict) and r.get("output_artifact_sha256")]
    results.append({
        "id": "handoff_chain_min_4_sha_rows",
        "passed": len(sha_rows) >= 4,
        "detail": f"{len(sha_rows)} rows have output_artifact_sha256 (need ≥4)",
    })

    # report.md exists and provenance block lists run_id + scorecard profile_id
    report, err = _read_text(out / "report.md")
    if err:
        results.append({"id": "report_present", "passed": False, "detail": err})
        return results
    has_run_id = bool(re.search(r"\brun_id\b", report))
    has_profile = bool(re.search(r"\b(scorecard.*profile_id|profile_id)\b", report))
    results.append({
        "id": "report_provenance_run_id_and_profile_id",
        "passed": has_run_id and has_profile,
        "detail": f"run_id={has_run_id}, profile_id={has_profile}",
    })

    # every sha appearing in report.md must come from chain (informational —
    # we only verify the inverse direction is non-empty).
    sha_values = {r["output_artifact_sha256"] for r in sha_rows}
    cited = set(re.findall(r"[0-9a-f]{64}", report))
    unknown = cited - sha_values
    results.append({
        "id": "report_claims_trace_to_chain",
        "passed": not unknown,
        "detail": (
            f"{len(cited)} sha citations in report, {len(unknown)} not in chain"
        ),
    })
    return results


def check_literature_grounding(out: Path) -> list[dict]:
    results: list[dict] = []
    answer, err = _read_text(out / "answer.md")
    if err:
        results.append({"id": "answer_present", "passed": False, "detail": err})
        return results
    gate, err = _read_json(out / "scorecard.json")
    if err:
        # fallback file name
        gate, err = _read_json(out / "gate_result.json")
    if err:
        results.append({"id": "gate_result_present", "passed": False, "detail": err})
        return results

    resolved = _find_field(gate, "resolved") or []
    unresolved = _find_field(gate, "unresolved") or _find_field(gate, "downgraded") or []
    resolved_ids = {
        r.get("claim_id") or r.get("id") or r.get("anchor_id")
        for r in resolved if isinstance(r, dict)
    }
    unresolved_ids = {
        r.get("claim_id") or r.get("id") or r.get("anchor_id")
        for r in unresolved if isinstance(r, dict)
    }

    # every cited claim_id in answer.md must be in resolved_ids
    cited = set(re.findall(r"\b(c\d+|claim[_-]?\d+)\b", answer, re.IGNORECASE))
    bad = {c for c in cited if c not in resolved_ids and resolved_ids}
    results.append({
        "id": "answer_cites_only_resolved",
        "passed": not bad,
        "detail": (
            f"{len(cited)} claim ids cited; {len(bad)} not in resolved[] "
            f"(resolved has {len(resolved_ids)} ids)"
        ),
    })

    # any unresolved id appearing in answer must be hedged with the prefix
    hedge_pattern = re.compile(r"evidence not resolved", re.IGNORECASE)
    hedged_lines = [ln for ln in answer.splitlines() if hedge_pattern.search(ln)]
    unhedged_unresolved = [
        u for u in unresolved_ids
        if u and re.search(rf"\b{re.escape(u)}\b", answer)
        and not any(u in ln for ln in hedged_lines)
    ]
    results.append({
        "id": "unresolved_claims_hedged_or_dropped",
        "passed": not unhedged_unresolved,
        "detail": (
            f"{len(unresolved_ids)} unresolved ids; "
            f"{len(unhedged_unresolved)} appear in answer without hedge"
        ),
    })
    return results


def check_null_result_self_critique(out: Path) -> list[dict]:
    results: list[dict] = []
    critique, err = _read_text(out / "critique.md")
    if err:
        results.append({"id": "critique_present", "passed": False, "detail": err})
        return results

    diag_keywords = ["granularity", "confounder", "weak label", "placeholder",
                     "filter", "outcome definition", "range restriction", "provenance"]
    hits = [k for k in diag_keywords if re.search(k, critique, re.IGNORECASE)]
    results.append({
        "id": "critique_has_two_diagnoses",
        "passed": len(hits) >= 2,
        "detail": f"{len(hits)} null-result diagnoses matched: {hits}",
    })

    # exactly one exploratory follow-up — accept bullet, numbered, or heading style
    proposals = re.findall(
        r"^\s*(?:[-*]|\d+\.|#+)\s+.*exploratory.*(?:follow[- ]?up|subgroup|analysis|proposal)?.*$",
        critique, re.IGNORECASE | re.MULTILINE,
    )
    # de-dup near-duplicates (a heading + its bullet shouldn't count twice)
    seen, dedup = set(), []
    for p in proposals:
        key = re.sub(r"\s+", " ", p.lower()).strip()[:60]
        if key not in seen:
            seen.add(key)
            dedup.append(p)
    results.append({
        "id": "critique_exactly_one_exploratory_followup",
        "passed": len(dedup) == 1,
        "detail": f"found {len(dedup)} exploratory follow-up proposal(s)",
    })

    report, err = _read_text(out / "report.md")
    if err:
        results.append({"id": "report_present", "passed": False, "detail": err})
        return results
    has_conf = bool(re.search(r"^\s*#+\s*confirmatory|confirmatory\s*:", report,
                              re.IGNORECASE | re.MULTILINE))
    has_expl = bool(re.search(r"^\s*#+\s*exploratory|exploratory\s*:", report,
                              re.IGNORECASE | re.MULTILINE))
    results.append({
        "id": "report_has_both_section_markers",
        "passed": has_conf and has_expl,
        "detail": f"confirmatory={has_conf}, exploratory={has_expl}",
    })

    # exploratory finding not promoted: the "exploratory" section's content
    # must not include the words "confirmed", "primary result", or "main finding"
    expl_block_match = re.search(
        r"(?:^|\n)\s*(?:#+\s*exploratory|exploratory\s*:)(.+?)(?=\n\s*#+\s|\Z)",
        report, re.IGNORECASE | re.DOTALL,
    )
    if expl_block_match:
        expl_text = expl_block_match.group(1)
        leaks = re.findall(r"\b(confirmed|primary result|main finding)\b",
                           expl_text, re.IGNORECASE)
        results.append({
            "id": "exploratory_not_promoted_to_confirmed",
            "passed": not leaks,
            "detail": f"promotion-leak terms in exploratory block: {leaks}",
        })
    return results


def check_plan_validate_and_execute(out: Path) -> list[dict]:
    results: list[dict] = []
    validate, err = _read_json(out / "validate.json")
    if err:
        results.append({"id": "validate_present", "passed": False, "detail": err})
        return results

    steps = _find_field(validate, "normalized_plan")
    if isinstance(steps, dict):
        steps = steps.get("steps")
    if steps is None:
        # try direct path
        steps = _find_field(validate, "steps")
    steps_len = len(steps) if isinstance(steps, list) else 0
    results.append({
        "id": "normalized_plan_steps_length_eq_3",
        "passed": steps_len == 3,
        "detail": f"normalized_plan.steps length = {steps_len} (need 3)",
    })

    recipe, err = _read_json(out / "recipe.json")
    if err:
        results.append({"id": "recipe_present", "passed": False, "detail": err})
        return results
    has_commands_create = bool(_find_field(recipe, "create"))
    has_python_script = bool(_find_field(recipe, "python_script"))
    results.append({
        "id": "recipe_has_commands_create_or_python_script",
        "passed": has_commands_create or has_python_script,
        "detail": f"commands.create={has_commands_create}, python_script={has_python_script}",
    })

    # determinism: this would require a re-run with live MCP. Mark as
    # informational/skipped so CI without MCP doesn't fail.
    results.append({
        "id": "rerun_yields_identical_steps",
        "passed": True,
        "detail": "skipped: requires live BR MCP — verify manually on capture",
        "skipped": True,
    })
    return results


def check_report_gate_rejection(out: Path) -> list[dict]:
    results: list[dict] = []
    gate, err = _read_json(out / "gate_result.json")
    if err:
        results.append({"id": "gate_result_present", "passed": False, "detail": err})
        return results

    # accept either BR-native resolved/unresolved or kit_derived_partition
    resolved = (_find_field(gate, "kit_derived_partition") or {}).get("resolved") \
        if isinstance(_find_field(gate, "kit_derived_partition"), dict) else None
    if resolved is None:
        resolved = _find_field(gate, "resolved") or _find_field(gate, "kept") or []
    unresolved = (_find_field(gate, "kit_derived_partition") or {}).get("unresolved") \
        if isinstance(_find_field(gate, "kit_derived_partition"), dict) else None
    if unresolved is None:
        unresolved = _find_field(gate, "unresolved") or []

    def _ids(rows):
        out_ids = set()
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, str):
                    out_ids.add(r)
                elif isinstance(r, dict):
                    out_ids.add(r.get("claim_id") or r.get("id") or r.get("anchor_id"))
        return out_ids

    resolved_ids = _ids(resolved)
    unresolved_ids = _ids(unresolved)

    results.append({
        "id": "c2_c3_in_unresolved",
        "passed": {"c2", "c3"}.issubset(unresolved_ids),
        "detail": f"unresolved ids: {sorted(x for x in unresolved_ids if x)}",
    })
    results.append({
        "id": "c1_c4_in_resolved",
        "passed": {"c1", "c4"}.issubset(resolved_ids),
        "detail": f"resolved ids: {sorted(x for x in resolved_ids if x)}",
    })

    log, err = _read_text(out / "report_attempt.log")
    if err:
        results.append({"id": "report_attempt_log_present", "passed": False, "detail": err})
    else:
        results.append({
            "id": "report_attempt_log_has_review_blocked",
            "passed": "review_blocked" in log,
            "detail": "review_blocked literal " + ("found" if "review_blocked" in log else "missing"),
        })

    handoff, err = _read_text(out / "agent_handoff.md")
    if err:
        results.append({"id": "agent_handoff_present", "passed": False, "detail": err})
    else:
        first_line = handoff.lstrip().splitlines()[0] if handoff.strip() else ""
        results.append({
            "id": "agent_handoff_starts_with_degraded",
            "passed": first_line.startswith("degraded:"),
            "detail": f"first line: {first_line[:80]!r}",
        })
    return results


REGISTRY = {
    "cross-tool-handoff": check_cross_tool_handoff,
    "literature-grounding": check_literature_grounding,
    "null-result-self-critique": check_null_result_self_critique,
    "plan-validate-and-execute": check_plan_validate_and_execute,
    "report-gate-rejection": check_report_gate_rejection,
}


def run_demo_checks(demo: str, expected_output: Path) -> list[dict]:
    fn = REGISTRY.get(demo)
    if fn is None:
        return [{"id": "no_checks_for_demo", "passed": False,
                 "detail": f"no demo-specific check function registered for {demo}"}]
    return fn(expected_output)
