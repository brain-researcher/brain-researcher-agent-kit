#!/usr/bin/env python3
"""Auditable-episode orchestration — seal FIRST, adjudicate offline, emit a redacted bundle.

The load-bearing ordering (a commit-before-observe institution):

    1. build the claim + its committed permutation_null battery (hash-locked),
    2. SEAL the commitment card (``lock_commitment``) and assert ``verify_hash()``
       BEFORE anything else is written — a card that does not verify never gets emitted,
    3. persist the sealed card to ``{run_dir}/society/commitment_card.json`` (the FIRST write),
    4. ONLY THEN run the two offline mechanisms:
         a. the deterministic permutation_null battery (``compute_permutation_null_probe`` +
            the real ``permutation_null`` gate) — the fully-offline, seeded, reproducible-anywhere
            adjudicator of *effect reality* (supported vs withheld),
         b. an offline ``neuroclaim_compile`` forced onto the NiMARE backend (never Neo4j) — a
            complementary *literature-convergence* verdict, recorded WITH its backend+profile
            provenance and the honest caveat that an offline nimare verdict != the online
            kg_verify verdict,
    5. write the claim card + a REDACTED evidence file, emit the audit bundle
       (``persist_audit_bundle``),
    6. ASSERT THE MECHANISM FIRED — re-open the emitted bundle and prove it actually contains
       the sealed card (hash unchanged) + the permutation_null verdict, and that no raw
       per-subject arrays / PII leaked. Fail loudly otherwise.

Standing rules honoured: NEVER backfill/rewrite a sealed commitment card (refuse if one already
exists); assert the mechanism engaged rather than trusting a happy-path log line (silent
degradation into a plausible-wrong "success" is this project's #1 trap).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Redaction — a real, tested scrub, not a claim. The permutation probe already
# fingerprints its inputs instead of storing raw arrays (redaction-by-construction);
# this denylist is the belt-and-suspenders scrub the audit evidence is routed through.
# --------------------------------------------------------------------------- #
_PII_DENYLIST: tuple[str, ...] = (
    "y_true",
    "y_pred",
    "raw_arrays",
    "arrays",
    "subject_id",
    "subject_ids",
    "subjects",
    "participant",
    "email",
    "password",
    "token",
    "secret",
    "api_key",
)


def _key_is_pii(key: str) -> bool:
    k = str(key).lower()
    return any(bad in k for bad in _PII_DENYLIST)


def _redact(obj: Any) -> Any:
    """Recursively drop denylisted keys and mask absolute /home/ paths in strings."""
    if isinstance(obj, dict):
        return {k: _redact(v) for k, v in obj.items() if not _key_is_pii(k)}
    if isinstance(obj, list):
        return [_redact(v) for v in obj]
    if isinstance(obj, str) and "/home/" in obj:
        # Mask a user home path so an exported bundle carries no local filesystem identity.
        return (
            obj.split("/home/")[0]
            + "/home/<redacted>/"
            + obj.split("/home/", 1)[1].split("/", 1)[-1]
        )
    return obj


def _find_pii_keys(obj: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if _key_is_pii(k):
                hits.append(str(k))
            hits.extend(_find_pii_keys(v))
    elif isinstance(obj, list):
        for v in obj:
            hits.extend(_find_pii_keys(v))
    return hits


def _redaction_self_test() -> None:
    """Prove the redactor actually strips — inject a canary and assert it is gone.

    (Do not trust that redaction 'ran'; assert it removes a known-bad value.)
    """
    canary = {"subject_ids": [1, 2, 3], "y_pred": [0.1], "keep": {"r": 0.5}}
    scrubbed = _redact(canary)
    if _find_pii_keys(scrubbed):
        raise AssertionError("redaction self-test FAILED: PII keys survived the scrub")
    if scrubbed != {"keep": {"r": 0.5}}:
        raise AssertionError(
            f"redaction self-test FAILED: unexpected residue {scrubbed}"
        )


# --------------------------------------------------------------------------- #
# The episode
# --------------------------------------------------------------------------- #
def run_auditable_episode(
    *,
    run_dir: Path | str,
    component: str,
    claim_id: str,
    claim_text: str,
    offline_claim: str,
    scope: dict[str, Any],
    corpus: Any,
    y_pred: Any,
    y_true: Any,
    fold_ids: Any,
    data_manifest: dict[str, Any] | None = None,
    n_permutations: int = 2000,
    perm_seed: int = 0,
) -> dict[str, Any]:
    """Run ONE sealed, offline, auditable research episode. Returns a JSON-safe verdict dict.

    ``corpus`` is a pre-built in-memory NiMARE Dataset (no network). ``y_pred``/``y_true``/
    ``fold_ids`` are the toy out-of-sample prediction arrays; they are passed in-memory only and
    are NEVER written to disk (the probe stores a fingerprint, not the arrays).
    """
    # Real enabling primitives (import here so a missing symbol is a loud ImportError, which the
    # preflight has already turned into a clear refusal before we ever reach this point).
    from brain_researcher.autoresearch.society import (
        HARD_STRATEGIES,
        ClaimCardV1,
        ClaimSpecV1,
        ClaimStatusV1,
        NimareBackend,
        ScopeBoundaryV1,
        compute_permutation_null_probe,
        derive_default_battery,
        lock_commitment,
        neuroclaim_compile,
    )
    from brain_researcher.autoresearch.society.falsifiers import DETERMINISTIC_GATES
    from brain_researcher.services.review.audit_bundle import persist_audit_bundle

    _redaction_self_test()  # mechanism-fired: the scrub works before we rely on it

    run_dir = Path(run_dir)
    society = run_dir / "society"
    commitment_path = society / "commitment_card.json"

    # NEVER backfill/rewrite a sealed commitment card. A fresh run_dir per episode is required.
    if commitment_path.exists():
        raise RuntimeError(
            f"REFUSING: a sealed commitment card already exists at {commitment_path}. "
            "Never backfill/rewrite a sealed card — use a fresh run_dir."
        )
    society.mkdir(parents=True, exist_ok=True)

    scope_obj = ScopeBoundaryV1(**scope)

    # ---- 1. claim + committed permutation_null battery (hash-locked into the seal) ----
    claim = ClaimSpecV1(
        claim_id=claim_id,
        claim_text=claim_text,
        scope_boundary=scope_obj,
        confirmatory=True,
    )
    battery = derive_default_battery(
        ["permutation_null"], claim, hard_axes=HARD_STRATEGIES
    )
    # Version-skew guard: on an older/toothless checkout this silently returns None and the
    # institution would seal an EMPTY battery. Refuse rather than seal a toothless card.
    if battery is None or [a.gate_name for a in battery.required_axes] != [
        "permutation_null"
    ]:
        raise RuntimeError(
            "derive_default_battery did not yield a permutation_null battery — the committed "
            "hard-axes institution is not engaged (checkout too old / permutation_null not a "
            f"HARD axis). Got: {battery!r}"
        )

    # ---- 2. SEAL and verify BEFORE emitting anything ----
    card = lock_commitment(
        claim,
        attack_strategies=["permutation_null"],
        rubric_refs={},
        falsifier_battery=battery,
    )
    if not card.verify_hash():
        raise RuntimeError(
            "commitment card failed verify_hash() — refusing to emit anything"
        )

    # ---- 3. persist the sealed card (the FIRST write) ----
    commitment_path.write_text(card.model_dump_json(indent=2), encoding="utf-8")

    # ---- 4a. deterministic permutation_null battery (fully offline, seeded) ----
    probe = compute_permutation_null_probe(
        y_pred, y_true, fold_ids, n_permutations=n_permutations, seed=perm_seed
    )
    scorer_payload = {"family_block_p": probe["family_block_p"]}
    refuted, probe_missing, gate_reason = DETERMINISTIC_GATES["permutation_null"](
        {"scorer_payload": scorer_payload}
    )

    # ---- 4b. offline neuroclaim compile forced onto NiMARE (never Neo4j) ----
    backend = NimareBackend(corpus=corpus, inference_mode="auto")
    # mechanism-fired: the offline backend must be usable, else compile would silently fall
    # back to the KG (Neo4j) backend — exactly the trap we refuse to hit.
    if not backend.available():
        raise RuntimeError(
            "NiMARE backend is not available (no corpus / nimare missing) — refusing to let "
            "neuroclaim_compile fall back to the online KG backend."
        )
    report = neuroclaim_compile(
        offline_claim,
        backend=backend,
        scope=ScopeBoundaryV1(modality=scope.get("modality", "fMRI")),
        run_sensitivity=True,
        on_evidence_unavailable="error",  # never launder an unreachable backend into a verdict
    )
    ev = report.evidence_verdict
    # mechanism-fired: prove it really used nimare (not kg_verify) — the backend+profile provenance.
    if ev is None or ev.backend != "nimare":
        raise RuntimeError(
            f"neuroclaim_compile did NOT run on the offline nimare backend "
            f"(evidence_verdict.backend={getattr(ev, 'backend', None)!r}) — refusing."
        )

    # ---- 5. claim card, survival-gated on the deterministic permutation battery ----
    if probe_missing:
        # A committed HARD axis with no verdict is a VB-1 completeness refusal, not a pass.
        status = ClaimStatusV1.needs_diagnosis
        survived, failed, banked = [], [], None
    elif refuted:
        status = ClaimStatusV1.rejected
        survived, failed, banked = [], ["permutation_null"], None  # score WITHHELD
    else:
        status = ClaimStatusV1.supported_within_scope
        survived, failed = ["permutation_null"], []
        banked = float(probe["observed_fold_mean_r"])  # score banked

    offline_provenance = {
        "backend": ev.backend,
        "profile": ev.profile,
        "inference": ev.inference,
        "status": report.status.value,
        "association_probability": ev.association_probability,
        "reproducible_query": ev.reproducible_query,
        "caveat": (
            "OFFLINE literature-convergence verdict via NiMARE over an in-memory synthetic "
            "corpus. This is NOT the online kg_verify verdict; it is complementary evidence "
            "only and does not survival-gate the score. Carry this backend+profile provenance "
            "with any downstream use."
        ),
    }
    local_data_provenance = copy.deepcopy(data_manifest) if data_manifest else None

    claim_card = ClaimCardV1(
        claim_id=claim.claim_id,
        claim_text=claim.claim_text,
        status=status,
        scope_boundary=scope_obj,
        commitment_card_ref=card.commitment_id,
        commitment_hash=card.commitment_hash,
        survived_checks=survived,
        failed_checks=failed,
        survival_gated_score=banked,
        falsification_budget_spent={
            "permutation_null": {
                "n_permutations": probe["n_permutations"],
                "n_subjects": probe["n_subjects"],
                "seed": perm_seed,
            }
        },
        pipeline_summary={
            "permutation_null": probe,
            "permutation_null_gate": {"refuted": refuted, "reason": gate_reason},
            "offline_neuroclaim": offline_provenance,
            "local_data": local_data_provenance,
            "survival_gate": {
                "authority": "permutation_null (committed HARD axis)",
                "score_banked": banked is not None,
            },
        },
        probe_provenance={"permutation_null": "commissioned"},
    )
    (society / "claim_card.json").write_text(
        claim_card.model_dump_json(indent=2), encoding="utf-8"
    )

    # ---- redacted evidence file (picked up into audit/evidence/ by the bundler) ----
    evidence = {
        "component": component,
        "commitment_hash": card.commitment_hash,
        "permutation_null": probe,  # fingerprint + aggregates only; NO raw per-subject arrays
        "permutation_null_gate": {
            "refuted": refuted,
            "probe_missing": probe_missing,
            "reason": gate_reason,
        },
        "offline_neuroclaim": offline_provenance,
        "local_data": local_data_provenance,
        "honest_scope": (
            "The fully-offline / reproducible-anywhere guarantee covers ONLY the deterministic "
            "permutation_null battery (seeded numpy). The nimare verdict is offline but "
            "version-sensitive and is NOT the authoritative online kg_verify verdict."
        ),
        "redaction": {
            "applied": True,
            "denylist": list(_PII_DENYLIST),
            "raw_per_subject_arrays_excluded": True,
        },
    }
    evidence = _redact(copy.deepcopy(evidence))
    leaked = _find_pii_keys(evidence)
    if leaked:
        raise RuntimeError(f"redaction failed — PII keys present in evidence: {leaked}")
    (run_dir / "evidence_verdicts.json").write_text(
        json.dumps(evidence, indent=2), encoding="utf-8"
    )

    # ---- 6. emit the audit bundle ----
    audit_dir = persist_audit_bundle(run_dir, provenance="live")
    if audit_dir is None:
        raise RuntimeError(
            "persist_audit_bundle returned None (BR_AUDIT_PERSIST disabled?)"
        )

    _assert_bundle_fired(audit_dir, card.commitment_hash)

    return {
        "component": component,
        "claim_id": claim.claim_id,
        "status": status.value,
        "refuted": refuted,
        "survival_gated_score": banked,
        "permutation_r": float(probe["observed_fold_mean_r"]),
        "permutation_p": float(probe["family_block_p"]),
        "offline_nimare_status": report.status.value,
        "offline_nimare_backend": ev.backend,
        "offline_nimare_profile": ev.profile,
        "commitment_hash": card.commitment_hash,
        "local_data_manifest": bool(local_data_provenance),
        "audit_dir": str(audit_dir),
        "run_dir": str(run_dir),
    }


def _assert_bundle_fired(audit_dir: Path, sealed_hash: str) -> None:
    """Re-open the emitted bundle and prove the mechanism actually fired.

    Not a happy-path log line: this reads the persisted files back and fails loudly unless the
    sealed card (hash unchanged) AND the permutation_null verdict AND the redacted evidence are
    all present.
    """
    manifest_path = audit_dir / "manifest.json"
    if not manifest_path.exists():
        raise AssertionError(f"audit bundle has no manifest.json at {audit_dir}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "complete":
        raise AssertionError(
            f"audit manifest status={manifest.get('status')!r} (expected 'complete' — "
            "commitment + claim_card must both be present)"
        )

    commitment = audit_dir / "commitment.json"
    if not commitment.exists():
        raise AssertionError("audit bundle is missing the sealed commitment.json")
    sealed = json.loads(commitment.read_text(encoding="utf-8"))
    if sealed.get("commitment_hash") != sealed_hash:
        raise AssertionError(
            "sealed commitment hash in the bundle does not match the card we sealed "
            f"({sealed.get('commitment_hash')} != {sealed_hash}) — the card was altered"
        )
    if manifest.get("commitment_hash") != sealed_hash:
        raise AssertionError("manifest commitment_hash != sealed hash")

    claim_card_path = audit_dir / "claim_card.json"
    if not claim_card_path.exists():
        raise AssertionError("audit bundle is missing claim_card.json")
    card = json.loads(claim_card_path.read_text(encoding="utf-8"))
    if "permutation_null" not in (
        card.get("survived_checks", []) + card.get("failed_checks", [])
    ):
        raise AssertionError(
            "claim_card in the bundle carries no permutation_null verdict (survived/failed) — "
            "the deterministic battery did not adjudicate"
        )

    ev_files = list((audit_dir / "evidence").glob("*.json"))
    if not ev_files:
        raise AssertionError("audit bundle carries no evidence file")
    ev_texts = [p.read_text(encoding="utf-8") for p in ev_files]
    if not any("permutation_null" in t and "family_block_p" in t for t in ev_texts):
        raise AssertionError(
            "audit evidence does not contain the permutation_null probe"
        )
    # redaction check ON the persisted bytes: no denylisted key survived into the bundle.
    for p, t in zip(ev_files, ev_texts, strict=False):
        found = _find_pii_keys(json.loads(t))
        if found:
            raise AssertionError(f"PII keys leaked into {p}: {found}")
