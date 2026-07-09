#!/usr/bin/env python3
"""Run the offline, deterministic, PII-free auditable episode end to end.

  conda activate brain_researcher
  PYTHONPATH=/path/to/br/src python scripts/run_episode.py                 # both fixtures
  PYTHONPATH=/path/to/br/src python scripts/run_episode.py --component true # just the true signal
  python scripts/run_episode.py --br-src /path/to/br@master                # adds <root>/src for you
  python scripts/run_episode.py --data-dir data/auditable-episode-hcp-a1

By default this uses two tiny in-memory fixtures (no bundled data, PII-free by construction):

  true : a real out-of-sample effect (fold-mean r high) whose region/term pair the offline NiMARE
         corpus supports  -> permutation_null SURVIVES  -> supported_within_scope, score BANKED.
  null : a null out-of-sample effect (r ~ 0) whose region/term pair the corpus does NOT support
         -> permutation_null REFUTES -> rejected, score WITHHELD.

Everything is forced offline: the NiMARE backend is passed as an instance (never resolves to the
online KG backend) and USE_GEMINI_CLI=false. Only the deterministic permutation_null battery is
bit-reproducible anywhere; the nimare verdict is offline-but-version-sensitive (see the honest
scope in SKILL.md and each episode's evidence file).

If ``--data-dir`` is supplied, the runner consumes local files prepared by a dataset-specific
staging script, such as ``prepare_hcp_a1_local_inputs.py``. That mode demonstrates the
user-local data path: restricted/public data are obtained by the user under the dataset's terms,
converted into a small checksum-bound local input contract, then the seal/adjudicate/audit chain
reads only that local directory.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import warnings
from pathlib import Path

_HERE = Path(__file__).resolve().parent

# Fixtures: component -> (claim_text, offline region/term claim for nimare, effect, seed).
# The "effect" is the true correlation planted between y_pred and y_true.
_FIXTURES: dict[str, dict] = {
    "true": {
        "claim_id": "ae_dlpfc_wm",
        "claim_text": "Working-memory engagement of dlPFC reproduces out-of-sample (fold-mean r>0)",
        "offline_claim": "dlPFC engages working memory",
        "effect": 0.6,
        "seed": 0,
    },
    "null": {
        "claim_id": "ae_v1_wm_null",
        "claim_text": "Working-memory engagement of V1 reproduces out-of-sample (fold-mean r>0)",
        "offline_claim": "V1 engages working memory",  # WM is not specific to V1 -> not supported
        "effect": 0.0,
        "seed": 1,
    },
}

# The expected verdict for the reference self-check (true -> supported+banked, null -> rejected+withheld).
_EXPECTED = {
    "true": {"status": "supported_within_scope", "banked": True},
    "null": {"status": "rejected", "banked": False},
}


def _load_local_data(data_dir: str | Path):
    import numpy as np

    root = Path(data_dir).expanduser().resolve()
    manifest_path = root / "auditable_episode_manifest.json"
    arrays_path = root / "auditable_episode_inputs.npz"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing local data manifest: {manifest_path}")
    if not arrays_path.exists():
        raise FileNotFoundError(f"missing local data arrays: {arrays_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    arrays = np.load(arrays_path)
    out: dict[str, dict] = {}
    for comp in ("true", "null"):
        out[comp] = {
            "y_true": arrays[f"{comp}_y_true"],
            "y_pred": arrays[f"{comp}_y_pred"],
            "fold_ids": arrays[f"{comp}_fold_ids"],
        }
    return root, manifest, out


def _make_signal(effect: float, seed: int, n: int = 120, folds: int = 5):
    import numpy as np

    rng = np.random.default_rng(seed)
    y_true = rng.standard_normal(n)
    noise = rng.standard_normal(n)
    # Proper unit-variance mixture so `effect` is (approximately) the population correlation.
    y_pred = effect * y_true + (1.0 - effect**2) ** 0.5 * noise
    fold_ids = np.tile(np.arange(folds), n // folds + 1)[:n]
    return y_pred, y_true, fold_ids


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--component", choices=["true", "null", "both"], default="both")
    ap.add_argument(
        "--br-src",
        default=os.environ.get("BR_SRC"),
        help="BR checkout root; adds <root>/src to sys.path",
    )
    ap.add_argument(
        "--workdir",
        default=None,
        help="parent work dir (default: /tmp/auditable-episode)",
    )
    ap.add_argument(
        "--data-dir",
        default=None,
        help=(
            "local data directory prepared by a dataset-specific staging script; "
            "uses staged local inputs instead of the in-memory fixture"
        ),
    )
    ap.add_argument("--n-permutations", type=int, default=2000)
    ap.add_argument(
        "--no-assert",
        action="store_true",
        help="do not fail if a verdict differs from the reference expectation",
    )
    args = ap.parse_args()

    # Force offline + no CLI-authed LLM, everywhere a downstream might look.
    os.environ["USE_GEMINI_CLI"] = "false"
    os.environ["BR_NEUROCLAIM_BACKEND"] = "nimare"
    os.environ.setdefault("BR_AUDIT_PERSIST", "true")

    # Preflight FIRST (refuses on version skew / missing offline backend). It also wires --br-src
    # onto sys.path so the controller import below resolves.
    sys.path.insert(0, str(_HERE))
    from preflight import assert_preflight

    assert_preflight(args.br_src, verbose=True)

    import controller  # noqa: E402  (imported after preflight has vetted the checkout)

    from brain_researcher.autoresearch.society import (  # noqa: E402
        build_synthetic_annotated_corpus,
        resolve_region,
    )

    warnings.filterwarnings("ignore")  # quiet benign nimare/nilearn divide warnings

    # One shared in-memory synthetic corpus (no network): WM -> dlPFC, vision -> V1.
    dlpfc = resolve_region("dlPFC").xyz
    v1 = resolve_region("V1").xyz
    corpus = build_synthetic_annotated_corpus(
        {"working_memory": dlpfc, "vision": v1}, per_term=12, jitter=5
    )

    workroot = (
        Path(args.workdir).expanduser()
        if args.workdir
        else Path("/tmp/auditable-episode")
    )
    components = ["true", "null"] if args.component == "both" else [args.component]
    local_root = None
    local_manifest = None
    local_arrays = None
    if args.data_dir:
        local_root, local_manifest, local_arrays = _load_local_data(args.data_dir)
        print(f"\n[auditable-episode] using staged local data: {local_root}")

    results = []
    mismatches = []
    for comp in components:
        fx = _FIXTURES[comp]
        run_dir = workroot / comp
        if run_dir.exists():
            shutil.rmtree(run_dir)  # fresh run_dir (never backfill a sealed card)
        run_dir.mkdir(parents=True)
        data_manifest = None
        claim_text = fx["claim_text"]
        if local_arrays is not None and local_manifest is not None:
            arrs = local_arrays[comp]
            y_pred, y_true, fold_ids = arrs["y_pred"], arrs["y_true"], arrs["fold_ids"]
            data_manifest = local_manifest
            claim_text = (
                local_manifest.get("components", {})
                .get(comp, {})
                .get("claim_text", claim_text)
            )
        else:
            y_pred, y_true, fold_ids = _make_signal(
                fx["effect"], fx["seed"], n=120, folds=5
            )
        res = controller.run_auditable_episode(
            run_dir=run_dir,
            component=comp,
            claim_id=fx["claim_id"],
            claim_text=claim_text,
            offline_claim=fx["offline_claim"],
            scope={"modality": "fMRI", "workflow_family": "fc"},
            corpus=corpus,
            y_pred=y_pred,
            y_true=y_true,
            fold_ids=fold_ids,
            data_manifest=data_manifest,
            n_permutations=args.n_permutations,
            perm_seed=0,
        )
        results.append(res)
        score = (
            "banked=%.3f" % res["survival_gated_score"]
            if res["survival_gated_score"] is not None
            else "WITHHELD"
        )
        print(
            f"\n[auditable-episode] component={comp} status={res['status']} {score} "
            f"perm(r={res['permutation_r']:.3f} p={res['permutation_p']:.4g} refuted={res['refuted']}) "
            f"offline_nimare={res['offline_nimare_status']}({res['offline_nimare_backend']}) "
            f"hash={res['commitment_hash'][:12]}"
        )
        if res.get("local_data_manifest"):
            print("  local data manifest: included in claim_card/evidence")
        print(f"  audit bundle: {res['audit_dir']}")

        exp = _EXPECTED[comp]
        banked = res["survival_gated_score"] is not None
        if res["status"] != exp["status"] or banked != exp["banked"]:
            mismatches.append(
                f"{comp}: got status={res['status']} banked={banked}, "
                f"expected status={exp['status']} banked={exp['banked']}"
            )

    print("\n" + "=" * 72)
    for res in results:
        print(
            f"  {res['component']:>4}: {res['status']:<24} "
            f"score={'WITHHELD' if res['survival_gated_score'] is None else round(res['survival_gated_score'], 3)}"
        )
    if mismatches and not args.no_assert:
        print(
            "\nREFERENCE SELF-CHECK FAILED (mechanism did not fire as expected):",
            file=sys.stderr,
        )
        for m in mismatches:
            print(f"  - {m}", file=sys.stderr)
        return 1
    print(
        "\nreference self-check OK — true=supported+banked, null=rejected+withheld"
        if args.component == "both"
        else "\nepisode complete"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
