#!/usr/bin/env python3
"""Generate genuinely different fitlins BIDS Stats Models from a base spec."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


VARIANTS = {
    "mv01": {
        "convolve": {"Model": "spm", "Derivative": False, "Dispersion": False},
        "X": [1, "trial_type.*", "trans_*", "rot_*", "cosine*"],
    },
    "mvB": {
        "convolve": {"Model": "spm", "Derivative": True, "Dispersion": True},
        "X": [1, "trial_type.*", "trans_*", "rot_*", "cosine*"],
    },
    "mvC": {
        "convolve": {"Model": "spm", "Derivative": False, "Dispersion": False},
        "X": [
            1,
            "trial_type.*",
            "trans_x",
            "trans_y",
            "trans_z",
            "rot_x",
            "rot_y",
            "rot_z",
            "cosine*",
        ],
    },
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("base_spec")
    parser.add_argument("out_dir")
    parser.add_argument("--subjects", nargs="+", required=True)
    parser.add_argument("--task")
    parser.add_argument("--session")
    args = parser.parse_args()

    with open(args.base_spec, encoding="utf-8") as handle:
        base = json.load(handle)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    input_filter: dict[str, list[str]] = {"subject": list(args.subjects)}
    if args.task:
        input_filter["task"] = [args.task]
    if args.session:
        input_filter["session"] = [args.session]

    for variant_id, cfg in VARIANTS.items():
        spec = copy.deepcopy(base)
        spec["Name"] = f"{base.get('Name', 'model')}-{variant_id}"
        spec["Input"] = input_filter
        run_node = spec["Nodes"][0]
        for instr in run_node.get("Transformations", {}).get("Instructions", []):
            if instr.get("Name") == "Convolve":
                instr.update(cfg["convolve"])
        run_node["Model"]["X"] = cfg["X"]
        path = out / f"model-{variant_id}.json"
        path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")

    print(f"{len(VARIANTS)} genuinely different variants written to {out}")


if __name__ == "__main__":
    main()
