#!/usr/bin/env python3
"""Route an idea to a journal, then return writing guide and figure plan in one JSON."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception as exc:  # pragma: no cover - runtime dependency guard
    raise SystemExit(f"PyYAML is required to run this script: {exc}") from exc


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _normalize_text(text: str) -> str:
    lowered = text.lower()
    return re.sub(r"\s+", " ", lowered).strip()


def _count_hits(text: str, keywords: list[str]) -> int:
    return sum(1 for kw in keywords if kw in text)


def _level(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _clamp_score(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _default_profiles_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_profiles.yaml"


def _default_constraints_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_constraints.yaml"


def _default_guides_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_writing_guides.yaml"


def _default_examples_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "journal_example_bank.yaml"


def _resolve_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _journal_weights() -> dict[str, dict[str, float]]:
    return {
        "nature_neuroscience": {
            "bio": 0.42,
            "method": 0.20,
            "clinical": 0.08,
            "open": 0.10,
            "aud": 0.20,
        },
        "neuron": {
            "bio": 0.40,
            "method": 0.22,
            "clinical": 0.08,
            "open": 0.08,
            "aud": 0.22,
        },
        "imaging_neuroscience": {
            "bio": 0.15,
            "method": 0.38,
            "clinical": 0.10,
            "open": 0.22,
            "aud": 0.15,
        },
        "neuroimage": {
            "bio": 0.20,
            "method": 0.30,
            "clinical": 0.15,
            "open": 0.15,
            "aud": 0.20,
        },
        "human_brain_mapping": {
            "bio": 0.25,
            "method": 0.26,
            "clinical": 0.14,
            "open": 0.13,
            "aud": 0.22,
        },
        "cerebral_cortex": {
            "bio": 0.38,
            "method": 0.22,
            "clinical": 0.08,
            "open": 0.10,
            "aud": 0.22,
        },
        "journal_of_neuroscience": {
            "bio": 0.30,
            "method": 0.25,
            "clinical": 0.12,
            "open": 0.15,
            "aud": 0.18,
        },
        "medical_image_analysis": {
            "bio": 0.10,
            "method": 0.45,
            "clinical": 0.15,
            "open": 0.10,
            "aud": 0.20,
        },
        "ieee_tmi": {
            "bio": 0.10,
            "method": 0.43,
            "clinical": 0.18,
            "open": 0.09,
            "aud": 0.20,
        },
    }


def evaluate_idea_fit(idea_text: str, profiles_payload: dict[str, Any], top_k: int) -> dict[str, Any]:
    journals = profiles_payload.get("journals", {})
    if not isinstance(journals, dict):
        raise ValueError("Invalid profile payload: journals must be an object.")

    text = _normalize_text(idea_text)
    words = text.split()

    mechanistic_keywords = [
        "mechanism",
        "mechanistic",
        "representation",
        "hierarchical",
        "cortical",
        "dmn",
        "neural code",
        "neural mechanism",
    ]
    method_keywords = [
        "algorithm",
        "pipeline",
        "transformer",
        "diffusion",
        "pretrain",
        "self-supervised",
        "contrastive",
        "alignment",
        "architecture",
        "model",
    ]
    clinical_keywords = ["clinical", "patient", "diagnosis", "hospital", "treatment", "translation"]
    open_keywords = ["open source", "code", "data availability", "bids", "reproduc", "github"]
    neuroimaging_keywords = ["fmri", "bold", "mri", "meg", "eeg", "roi", "neuroimaging", "brain"]
    rigor_keywords = [
        "ablation",
        "baseline",
        "cross-site",
        "cross subject",
        "cross-subject",
        "fdr",
        "fwe",
        "confound",
        "robust",
        "replication",
    ]
    broad_keywords = ["general", "broad", "theory", "framework", "field", "mechanism"]
    incremental_cues = ["5%", "3%", "accuracy", "benchmark only", "incremental"]

    mech_hits = _count_hits(text, mechanistic_keywords)
    method_hits = _count_hits(text, method_keywords)
    clinical_hits = _count_hits(text, clinical_keywords)
    open_hits = _count_hits(text, open_keywords)
    imaging_hits = _count_hits(text, neuroimaging_keywords)
    rigor_hits = _count_hits(text, rigor_keywords)
    broad_hits = _count_hits(text, broad_keywords)
    incremental_hits = _count_hits(text, incremental_cues)

    biological_score = _clamp_score(25 + mech_hits * 14 + broad_hits * 5 - max(incremental_hits - mech_hits, 0) * 8)
    method_score = _clamp_score(25 + method_hits * 9 + rigor_hits * 8)
    clinical_score = _clamp_score(15 + clinical_hits * 18)
    open_score = _clamp_score(15 + open_hits * 20 + (4 if "reproduc" in text else 0))
    audience_score = _clamp_score(25 + broad_hits * 10 + imaging_hits * 6 + (6 if len(words) > 80 else 0))

    analysis = {
        "biological_insight_level": _level(biological_score),
        "methodological_innovation_level": _level(method_score),
        "clinical_translation_level": _level(clinical_score),
        "open_science_readiness_level": _level(open_score),
        "target_audience_fit_level": _level(audience_score),
    }

    weights = _journal_weights()
    matches: list[dict[str, Any]] = []

    for journal_id, profile in journals.items():
        name = str(profile.get("name", journal_id))
        w = weights.get(journal_id, {"bio": 0.25, "method": 0.25, "clinical": 0.15, "open": 0.15, "aud": 0.20})
        base = (
            biological_score * w["bio"]
            + method_score * w["method"]
            + clinical_score * w["clinical"]
            + open_score * w["open"]
            + audience_score * w["aud"]
        )

        adjust = 0.0
        if journal_id in {"imaging_neuroscience", "neuroimage", "human_brain_mapping", "cerebral_cortex", "journal_of_neuroscience"}:
            adjust += 10 if imaging_hits > 0 else -12
        if journal_id in {"medical_image_analysis", "ieee_tmi"}:
            adjust += 12 if method_hits >= 2 else -10
            adjust += 6 if rigor_hits > 0 else -4
        if journal_id in {"nature_neuroscience", "neuron", "cerebral_cortex"}:
            adjust += 10 if mech_hits > 0 else -12
            adjust -= 10 if incremental_hits > 0 and mech_hits == 0 else 0

        score = _clamp_score(base + adjust)

        pros: list[str] = []
        cons: list[str] = []
        gating_risks: list[str] = []
        actions: list[str] = []

        if mech_hits > 0:
            pros.append("Includes mechanism-oriented language and biological interpretation signals.")
        if method_hits > 0:
            pros.append("Contains a concrete methodological contribution.")
        if rigor_hits > 0:
            pros.append("Mentions rigor signals (ablations/baselines/confound controls).")
        if open_hits > 0:
            pros.append("Includes reproducibility/open-science cues.")
        if imaging_hits > 0:
            pros.append("Clearly grounded in neuroimaging context.")

        if biological_score < 45:
            cons.append("Biological insight signal is currently weak.")
            gating_risks.append("Risk of being judged as engineering-only contribution.")
            actions.append("Add a mechanism-focused hypothesis and explicit biological interpretation tests.")
        if method_score < 45:
            cons.append("Method innovation signal is limited.")
            gating_risks.append("Risk of insufficient novelty versus existing pipelines.")
            actions.append("Clarify the exact algorithmic novelty and include ablation plans.")
        if rigor_hits == 0:
            cons.append("No explicit robustness/ablation/confound controls detected.")
            gating_risks.append("Reviewer concern about methodological rigor.")
            actions.append("Add baseline, ablation, and robustness checks to the core evaluation plan.")
        if imaging_hits == 0 and journal_id in {"imaging_neuroscience", "neuroimage", "human_brain_mapping"}:
            cons.append("Neuroimaging signal is unclear for an imaging-focused venue.")
            gating_risks.append("Scope mismatch risk for imaging journals.")
            actions.append("Make imaging modality, acquisition context, and analysis target explicit.")
        if journal_id in {"nature_neuroscience", "neuron"} and mech_hits == 0:
            cons.append("Conceptual/mechanistic advance is not explicit for generalist top-tier journals.")
            gating_risks.append("High desk-reject risk due to limited conceptual advance.")
            actions.append("Reframe contribution around a falsifiable neuroscience mechanism.")

        if not actions:
            actions.append("Strengthen narrative by aligning each main figure to one core claim.")
        if not gating_risks:
            gating_risks.append("No critical gating risk detected from the idea text alone; confirm with full draft.")

        fit_rationale = f"Score derived from biological ({biological_score}), methodological ({method_score}), clinical ({clinical_score}), open-science ({open_score}), and audience ({audience_score}) signals with {name}-specific weighting."

        matches.append(
            {
                "journal_id": journal_id,
                "journal": name,
                "match_score": score,
                "fit_rationale": fit_rationale,
                "pros": pros[:4],
                "cons": cons[:4],
                "gating_risks": gating_risks[:4],
                "priority_actions": actions[:4],
            }
        )

    matches.sort(key=lambda item: item["match_score"], reverse=True)
    if top_k > 0:
        matches = matches[:top_k]

    top = matches[0]
    second_score = matches[1]["match_score"] if len(matches) > 1 else max(top["match_score"] - 5, 0)
    gap = top["match_score"] - second_score
    if top["match_score"] >= 80 and gap >= 12:
        confidence = "high"
    elif top["match_score"] >= 65 and gap >= 6:
        confidence = "medium"
    else:
        confidence = "low"

    gap_to_next_tier = [
        "Increase evidence depth with stronger ablations and external validation.",
        "Tighten claim language to match statistical support and robustness scope.",
        "Map each claimed contribution to one dedicated figure and one control analysis.",
    ]

    assumptions: list[str] = []
    if len(words) < 40:
        assumptions.append("Idea description is short; scoring confidence is limited by missing implementation details.")
    if imaging_hits == 0:
        assumptions.append("Imaging modality was inferred weakly; venue routing may shift once data modality is explicit.")

    recommendation_summary = (
        f"Best current fit is {top['journal']} ({top['match_score']}/100). "
        f"Prioritize: {top['priority_actions'][0]}"
    )

    return {
        "analysis": analysis,
        "journal_matches": matches,
        "top_journal": {
            "journal_id": top["journal_id"],
            "journal": top["journal"],
            "confidence": confidence,
        },
        "gap_to_next_tier": gap_to_next_tier,
        "recommendation_summary": recommendation_summary,
        "assumptions": assumptions,
    }


def build_route_and_guide(
    idea_text: str,
    profiles_payload: dict[str, Any],
    guides_payload: dict[str, Any],
    examples_payload: dict[str, Any],
    constraints_payload: dict[str, Any],
    top_k: int,
    article_type: str,
    section: str | None,
    manuscript_text: str | None,
) -> dict[str, Any]:
    fit_result = evaluate_idea_fit(idea_text=idea_text, profiles_payload=profiles_payload, top_k=top_k)
    top_journal_id = fit_result["top_journal"]["journal_id"]

    scripts_dir = Path(__file__).resolve().parent
    writing_module = _resolve_module(scripts_dir / "get_writing_guide.py", "get_writing_guide_mod")
    figure_module = _resolve_module(scripts_dir / "plan_figure_strategy.py", "plan_figure_strategy_mod")

    guide_result = writing_module.build_writing_guide(
        guides_payload=guides_payload,
        examples_payload=examples_payload,
        journal=top_journal_id,
        section=section,
    )

    figure_result = figure_module.build_figure_plan(
        guides_payload=guides_payload,
        constraints_payload=constraints_payload,
        journal=top_journal_id,
        article_type=article_type,
        manuscript_text=manuscript_text,
    )

    top_match = fit_result["journal_matches"][0]
    first_actions: list[str] = []
    first_actions.extend(top_match.get("priority_actions", []))
    if figure_result.get("compliance_check", {}).get("suggestion"):
        first_actions.append(figure_result["compliance_check"]["suggestion"])
    if not first_actions:
        first_actions.append("Draft a claim-to-figure map before section rewriting.")

    summary = (
        f"Top venue: {fit_result['top_journal']['journal']} "
        f"(score {top_match['match_score']}, confidence {fit_result['top_journal']['confidence']})."
    )

    return {
        "top_journal_id": top_journal_id,
        "top_journal": fit_result["top_journal"]["journal"],
        "fit_summary": summary,
        "writing_guide_snapshot": {
            "core_message": guide_result.get("core_message", {}),
            "narrative_goals": guide_result.get("narrative_goals", {}),
            "figure_strategy": guide_result.get("figure_strategy", {}),
        },
        "first_actions": first_actions[:5],
        "idea_fit_result": fit_result,
        "writing_guide_result": guide_result,
        "figure_plan_result": figure_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--idea", help="Idea text to route.")
    parser.add_argument("--idea-file", help="Path to a text/markdown file containing the idea.")
    parser.add_argument("--top-k", type=int, default=5, help="How many journal matches to return.")
    parser.add_argument(
        "--article-type",
        default="research_article",
        help="Article type used for figure planning.",
    )
    parser.add_argument(
        "--section",
        help="Optional section focus for writing guide (abstract|introduction|methods|results|discussion).",
    )
    parser.add_argument(
        "--manuscript",
        help="Optional manuscript markdown path for figure-count compliance check.",
    )
    parser.add_argument(
        "--profiles",
        default=str(_default_profiles_path()),
        help="Path to journal_profiles.yaml.",
    )
    parser.add_argument(
        "--guides",
        default=str(_default_guides_path()),
        help="Path to journal_writing_guides.yaml.",
    )
    parser.add_argument(
        "--examples",
        default=str(_default_examples_path()),
        help="Path to journal_example_bank.yaml.",
    )
    parser.add_argument(
        "--constraints",
        default=str(_default_constraints_path()),
        help="Path to journal_constraints.yaml.",
    )
    parser.add_argument("--output", help="Optional output JSON path.")
    args = parser.parse_args()

    if not args.idea and not args.idea_file:
        raise SystemExit("Provide either --idea or --idea-file.")

    idea_text = args.idea or ""
    if args.idea_file:
        idea_path = Path(args.idea_file).expanduser().resolve()
        if not idea_path.exists():
            raise SystemExit(f"Idea file not found: {idea_path}")
        idea_text = idea_path.read_text(encoding="utf-8")

    manuscript_text = None
    if args.manuscript:
        manuscript_path = Path(args.manuscript).expanduser().resolve()
        if not manuscript_path.exists():
            raise SystemExit(f"Manuscript file not found: {manuscript_path}")
        manuscript_text = manuscript_path.read_text(encoding="utf-8")

    profiles_payload = yaml.safe_load(Path(args.profiles).expanduser().resolve().read_text(encoding="utf-8")) or {}
    guides_payload = yaml.safe_load(Path(args.guides).expanduser().resolve().read_text(encoding="utf-8")) or {}
    examples_payload = yaml.safe_load(Path(args.examples).expanduser().resolve().read_text(encoding="utf-8")) or {}
    constraints_payload = yaml.safe_load(Path(args.constraints).expanduser().resolve().read_text(encoding="utf-8")) or {}

    result = build_route_and_guide(
        idea_text=idea_text,
        profiles_payload=profiles_payload,
        guides_payload=guides_payload,
        examples_payload=examples_payload,
        constraints_payload=constraints_payload,
        top_k=max(args.top_k, 1),
        article_type=args.article_type,
        section=args.section,
        manuscript_text=manuscript_text,
    )

    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).expanduser().resolve().write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
