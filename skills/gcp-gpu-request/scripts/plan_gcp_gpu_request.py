#!/usr/bin/env python3
"""Estimate GPU request size and generate on-demand GCP commands."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

BYTES_PER_PARAM = {
    "fp32": 4,
    "fp16": 2,
    "bf16": 2,
    "int8": 1,
    "int4": 0.5,
}

MODE_MULTIPLIER = {
    "infer": 1.3,
    "finetune": 2.6,
    "train": 6.0,
}

GPU_VRAM_GB = {
    "l4": 24,
    "a100-40": 40,
    "a100-80": 80,
    "h100": 80,
}

ALLOWED_GPU_COUNTS = {
    "l4": [1, 2, 4, 8],
    "a100-40": [1, 2, 4, 8],
    "a100-80": [1, 2, 4, 8],
    "h100": [8],
}

ACCELERATOR_TYPE = {
    "l4": "nvidia-l4",
    "a100-40": "nvidia-tesla-a100",
    "a100-80": "nvidia-a100-80gb",
    "h100": "nvidia-h100-80gb",
}

MACHINE_TYPE_BY_COUNT: dict[str, dict[int, str]] = {
    "l4": {
        1: "g2-standard-8",
        2: "g2-standard-24",
        4: "g2-standard-48",
        8: "g2-standard-96",
    },
    "a100-40": {
        1: "a2-highgpu-1g",
        2: "a2-highgpu-2g",
        4: "a2-highgpu-4g",
        8: "a2-highgpu-8g",
    },
    "a100-80": {
        1: "a2-ultragpu-1g",
        2: "a2-ultragpu-2g",
        4: "a2-ultragpu-4g",
        8: "a2-ultragpu-8g",
    },
    "h100": {
        8: "a3-highgpu-8g",
    },
}

DEFAULT_GPU_HOURLY_USD = {
    "l4": 0.71,
    "a100-40": 2.93,
    "a100-80": 3.67,
    "h100": 8.0,
}

DEFAULT_VM_HOURLY_USD = {
    "g2-standard-8": 0.38,
    "g2-standard-24": 1.15,
    "g2-standard-48": 2.3,
    "g2-standard-96": 4.6,
    "a2-highgpu-1g": 1.6,
    "a2-highgpu-2g": 3.2,
    "a2-highgpu-4g": 6.4,
    "a2-highgpu-8g": 12.8,
    "a2-ultragpu-1g": 2.3,
    "a2-ultragpu-2g": 4.6,
    "a2-ultragpu-4g": 9.2,
    "a2-ultragpu-8g": 18.4,
    "a3-highgpu-8g": 32.0,
}

DEFAULT_DISK_HOURLY_USD_PER_GB = 0.00023


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def activation_factor(seq_len: int, batch_size: int) -> float:
    raw = (seq_len / 4096.0) * (batch_size / 8.0) * 0.2
    return 1.0 + min(2.0, raw)


def round_to_allowed(gpu_type: str, count: int) -> int:
    allowed = ALLOWED_GPU_COUNTS[gpu_type]
    for candidate in allowed:
        if count <= candidate:
            return candidate
    return allowed[-1]


def estimate_duration_hours(
    total_tokens: float | None,
    throughput_tps_per_gpu: float | None,
    total_steps: float | None,
    sec_per_step_per_gpu: float | None,
    num_gpus: int,
    utilization: float,
) -> tuple[float | None, list[str]]:
    warnings: list[str] = []
    util = clamp(utilization, 0.1, 0.99)

    token_hours = None
    if total_tokens and throughput_tps_per_gpu and throughput_tps_per_gpu > 0:
        token_hours = total_tokens / (throughput_tps_per_gpu * num_gpus * util) / 3600.0

    step_hours = None
    if total_steps and sec_per_step_per_gpu and sec_per_step_per_gpu > 0:
        step_hours = (total_steps * sec_per_step_per_gpu) / (num_gpus * util) / 3600.0

    if token_hours is not None and step_hours is not None:
        return max(token_hours, step_hours), warnings
    if token_hours is not None:
        return token_hours, warnings
    if step_hours is not None:
        return step_hours, warnings

    warnings.append(
        "Runtime estimate missing: provide token or step throughput inputs for better duration planning."
    )
    return None, warnings


def detect_accelerator_type(zone: str, gpu_type: str, fallback: str) -> tuple[str, str | None]:
    if shutil.which("gcloud") is None:
        return fallback, "gcloud not found locally; accelerator type not probed."

    try:
        cmd = [
            "gcloud",
            "compute",
            "accelerator-types",
            "list",
            f"--zones={zone}",
            "--format=value(name)",
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        names = [line.strip() for line in out.splitlines() if line.strip()]
    except Exception:
        return fallback, "Could not query accelerator types; using default mapping."

    if fallback in names:
        return fallback, None

    keyword = {
        "l4": r"l4",
        "a100-40": r"a100",
        "a100-80": r"a100.*80",
        "h100": r"h100",
    }[gpu_type]

    for name in names:
        if re.search(keyword, name, flags=re.IGNORECASE):
            return name, f"Using detected accelerator type '{name}' in zone {zone}."

    return fallback, "No matching accelerator found in zone listing; keeping default mapping."


def build_commands(
    *,
    project: str,
    zone: str,
    instance_name: str,
    machine_type: str,
    accelerator_type: str,
    gpus_per_node: int,
    nodes: int,
    disk_gb: int,
    spot: bool,
) -> dict[str, str]:
    spot_flags = ""
    if spot:
        spot_flags = " --provisioning-model=SPOT --instance-termination-action=DELETE"

    common = (
        f"--project {project} --zone {zone} --machine-type {machine_type} "
        f"--accelerator type={accelerator_type},count={gpus_per_node} "
        f"--maintenance-policy TERMINATE --boot-disk-size {disk_gb}GB --boot-disk-type pd-ssd"
    )

    if nodes == 1:
        create = f"gcloud compute instances create {instance_name} {common}{spot_flags}"
        start = f"gcloud compute instances start {instance_name} --project {project} --zone {zone}"
        stop = f"gcloud compute instances stop {instance_name} --project {project} --zone {zone}"
        delete = f"gcloud compute instances delete {instance_name} --project {project} --zone {zone} --quiet"
        watch = f"gcloud compute instances describe {instance_name} --project {project} --zone {zone}"
    else:
        create = (
            f"for i in $(seq 1 {nodes}); do "
            f"gcloud compute instances create {instance_name}-$i {common}{spot_flags}; "
            "done"
        )
        start = (
            f"for i in $(seq 1 {nodes}); do "
            f"gcloud compute instances start {instance_name}-$i --project {project} --zone {zone}; "
            "done"
        )
        stop = (
            f"for i in $(seq 1 {nodes}); do "
            f"gcloud compute instances stop {instance_name}-$i --project {project} --zone {zone}; "
            "done"
        )
        delete = (
            f"for i in $(seq 1 {nodes}); do "
            f"gcloud compute instances delete {instance_name}-$i --project {project} --zone {zone} --quiet; "
            "done"
        )
        watch = (
            f"for i in $(seq 1 {nodes}); do "
            f"gcloud compute instances describe {instance_name}-$i --project {project} --zone {zone}; "
            "done"
        )

    return {
        "create": create,
        "start": start,
        "stop": stop,
        "delete": delete,
        "inspect": watch,
    }


def estimate_costs(
    *,
    estimated_hours: float | None,
    ttl_hours: int,
    fallback_ttl_hours: int,
    nodes: int,
    gpus_per_node: int,
    disk_gb: int,
    gpu_hourly_usd_per_device: float,
    vm_hourly_usd_per_node: float,
    disk_hourly_usd_per_gb: float,
    spot: bool,
    spot_discount_fraction: float,
) -> dict[str, Any]:
    discount = clamp(spot_discount_fraction, 0.0, 0.95) if spot else 0.0
    discount_multiplier = 1.0 - discount

    gpu_hourly_total = nodes * gpus_per_node * gpu_hourly_usd_per_device * discount_multiplier
    vm_hourly_total = nodes * vm_hourly_usd_per_node * discount_multiplier
    disk_hourly_total = nodes * disk_gb * disk_hourly_usd_per_gb

    total_hourly = gpu_hourly_total + vm_hourly_total + disk_hourly_total
    run_window_hours = estimated_hours if estimated_hours is not None else float(fallback_ttl_hours)

    return {
        "run_window_hours": round(run_window_hours, 2),
        "ttl_window_hours": int(ttl_hours),
        "hourly_cost_usd": round(total_hourly, 2),
        "hourly_components_usd": {
            "gpu": round(gpu_hourly_total, 2),
            "vm": round(vm_hourly_total, 2),
            "disk": round(disk_hourly_total, 2),
        },
        "estimated_run_cost_usd": round(total_hourly * run_window_hours, 2),
        "estimated_ttl_cost_usd": round(total_hourly * float(ttl_hours), 2),
        "pricing_assumptions": {
            "gpu_hourly_usd_per_device": round(gpu_hourly_usd_per_device, 4),
            "vm_hourly_usd_per_node": round(vm_hourly_usd_per_node, 4),
            "disk_hourly_usd_per_gb": round(disk_hourly_usd_per_gb, 6),
            "spot": spot,
            "spot_discount_fraction": round(discount, 3),
        },
    }


def build_request_markdown(result: dict[str, Any]) -> str:
    est = result["estimate"]
    gcp = result["gcp"]
    cost = result["cost_estimate"]
    return (
        "## GPU Resource Request\n\n"
        f"- Project: {gcp['project']}\n"
        f"- Zone: {gcp['zone']}\n"
        f"- Workload mode: {result['input']['mode']}\n"
        f"- Model size: {result['input']['model_params_b']}B params ({result['input']['precision']})\n"
        f"- Estimated VRAM required: {est['required_vram_gb']} GB\n"
        f"- Proposed GPU: {gcp['gpu_type']} x {est['recommended_gpus_total']}\n"
        f"- Proposed nodes: {est['nodes']} (gpus/node: {est['gpus_per_node']})\n"
        f"- Estimated runtime: {est['estimated_hours']} hours\n"
        f"- Proposed TTL window: {est['recommended_ttl_hours']} hours\n"
        f"- Proposed disk size: {est['recommended_disk_gb']} GB\n"
        f"- Estimated hourly cost: ${cost['hourly_cost_usd']}\n"
        f"- Estimated run cost: ${cost['estimated_run_cost_usd']}\n"
        f"- Estimated TTL-window cost: ${cost['estimated_ttl_cost_usd']}\n"
        "- Deprovision plan: stop when done, then delete instance(s) using generated commands.\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["infer", "finetune", "train"], required=True)
    parser.add_argument("--model-params-b", type=float, required=True)
    parser.add_argument("--precision", choices=sorted(BYTES_PER_PARAM.keys()), default="bf16")
    parser.add_argument("--seq-len", type=int, default=4096)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--safety-factor", type=float, default=1.2)
    parser.add_argument("--utilization", type=float, default=0.75)

    parser.add_argument("--gpu-type", choices=sorted(GPU_VRAM_GB.keys()), default="l4")

    parser.add_argument("--total-tokens", type=float)
    parser.add_argument("--throughput-tokens-per-sec-per-gpu", type=float)
    parser.add_argument("--total-steps", type=float)
    parser.add_argument("--seconds-per-step-per-gpu", type=float)

    parser.add_argument("--dataset-size-gb", type=float, default=0.0)
    parser.add_argument("--checkpoint-count", type=int, default=2)

    parser.add_argument("--project", default="hai-gcp-dialogue-brain")
    parser.add_argument("--zone", default="us-west1-b")
    parser.add_argument("--instance-name", default="br-gpu-job")
    parser.add_argument("--spot", action="store_true")
    parser.add_argument(
        "--spot-discount-fraction",
        type=float,
        default=0.7,
        help="Applied only when --spot is set. Example: 0.7 means 70%% discount.",
    )
    parser.add_argument("--fallback-ttl-hours", type=int, default=8)
    parser.add_argument("--gpu-hourly-usd-per-device", type=float)
    parser.add_argument("--vm-hourly-usd-per-node", type=float)
    parser.add_argument("--disk-hourly-usd-per-gb", type=float)
    parser.add_argument("--output", choices=["json", "markdown"], default="json")

    args = parser.parse_args()

    warnings: list[str] = []

    bytes_per_param = BYTES_PER_PARAM[args.precision]
    mode_multiplier = MODE_MULTIPLIER[args.mode]

    model_gb = args.model_params_b * 1e9 * bytes_per_param / (1024.0**3)
    act_factor = activation_factor(args.seq_len, args.batch_size)
    required_vram = model_gb * mode_multiplier * act_factor * max(args.safety_factor, 1.0)

    gpu_vram = GPU_VRAM_GB[args.gpu_type]
    min_gpus_by_memory = max(1, math.ceil(required_vram / gpu_vram))

    supported_count = round_to_allowed(args.gpu_type, min_gpus_by_memory)
    if supported_count != min_gpus_by_memory:
        warnings.append(
            f"Rounded GPU count from {min_gpus_by_memory} to supported count {supported_count} for {args.gpu_type}."
        )

    max_per_node = max(ALLOWED_GPU_COUNTS[args.gpu_type])
    if supported_count > max_per_node:
        nodes = math.ceil(supported_count / max_per_node)
        gpus_per_node = max_per_node
        total_gpus = nodes * gpus_per_node
    else:
        nodes = 1
        gpus_per_node = supported_count
        total_gpus = supported_count

    estimated_hours, duration_warnings = estimate_duration_hours(
        total_tokens=args.total_tokens,
        throughput_tps_per_gpu=args.throughput_tokens_per_sec_per_gpu,
        total_steps=args.total_steps,
        sec_per_step_per_gpu=args.seconds_per_step_per_gpu,
        num_gpus=total_gpus,
        utilization=args.utilization,
    )
    warnings.extend(duration_warnings)

    ttl_hours = (
        math.ceil(estimated_hours * 1.3)
        if estimated_hours is not None
        else max(1, int(args.fallback_ttl_hours))
    )

    checkpoint_bytes_per_param = max(2.0, bytes_per_param)
    checkpoint_gb = (
        args.model_params_b * 1e9 * checkpoint_bytes_per_param / (1024.0**3) * max(1, args.checkpoint_count)
    )
    disk_gb = max(100, math.ceil(args.dataset_size_gb * 1.5 + checkpoint_gb + 30.0))

    machine_type = MACHINE_TYPE_BY_COUNT[args.gpu_type].get(gpus_per_node)
    if machine_type is None:
        machine_type = f"<select-{args.gpu_type}-machine-type-for-{gpus_per_node}gpus>"
        warnings.append("Machine type could not be resolved from static map; set it manually.")

    accelerator_type, acc_note = detect_accelerator_type(
        zone=args.zone,
        gpu_type=args.gpu_type,
        fallback=ACCELERATOR_TYPE[args.gpu_type],
    )
    if acc_note:
        warnings.append(acc_note)

    commands = build_commands(
        project=args.project,
        zone=args.zone,
        instance_name=args.instance_name,
        machine_type=machine_type,
        accelerator_type=accelerator_type,
        gpus_per_node=gpus_per_node,
        nodes=nodes,
        disk_gb=disk_gb,
        spot=args.spot,
    )

    gpu_hourly_usd_per_device = args.gpu_hourly_usd_per_device
    if gpu_hourly_usd_per_device is None:
        gpu_hourly_usd_per_device = DEFAULT_GPU_HOURLY_USD.get(args.gpu_type)
        if gpu_hourly_usd_per_device is None:
            gpu_hourly_usd_per_device = 0.0
            warnings.append(
                "Missing default GPU hourly price for selected GPU type; set --gpu-hourly-usd-per-device."
            )

    vm_hourly_usd_per_node = args.vm_hourly_usd_per_node
    if vm_hourly_usd_per_node is None:
        vm_hourly_usd_per_node = DEFAULT_VM_HOURLY_USD.get(machine_type)
        if vm_hourly_usd_per_node is None:
            vm_hourly_usd_per_node = 0.0
            warnings.append(
                "Missing default VM hourly price for selected machine type; set --vm-hourly-usd-per-node."
            )

    disk_hourly_usd_per_gb = args.disk_hourly_usd_per_gb
    if disk_hourly_usd_per_gb is None:
        disk_hourly_usd_per_gb = DEFAULT_DISK_HOURLY_USD_PER_GB

    cost_estimate = estimate_costs(
        estimated_hours=estimated_hours,
        ttl_hours=ttl_hours,
        fallback_ttl_hours=args.fallback_ttl_hours,
        nodes=nodes,
        gpus_per_node=gpus_per_node,
        disk_gb=disk_gb,
        gpu_hourly_usd_per_device=gpu_hourly_usd_per_device,
        vm_hourly_usd_per_node=vm_hourly_usd_per_node,
        disk_hourly_usd_per_gb=disk_hourly_usd_per_gb,
        spot=args.spot,
        spot_discount_fraction=args.spot_discount_fraction,
    )

    result: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "mode": args.mode,
            "model_params_b": args.model_params_b,
            "precision": args.precision,
            "seq_len": args.seq_len,
            "batch_size": args.batch_size,
            "gpu_type": args.gpu_type,
            "total_tokens": args.total_tokens,
            "throughput_tokens_per_sec_per_gpu": args.throughput_tokens_per_sec_per_gpu,
            "total_steps": args.total_steps,
            "seconds_per_step_per_gpu": args.seconds_per_step_per_gpu,
            "dataset_size_gb": args.dataset_size_gb,
            "spot": args.spot,
            "spot_discount_fraction": args.spot_discount_fraction,
            "gpu_hourly_usd_per_device": args.gpu_hourly_usd_per_device,
            "vm_hourly_usd_per_node": args.vm_hourly_usd_per_node,
            "disk_hourly_usd_per_gb": args.disk_hourly_usd_per_gb,
        },
        "estimate": {
            "model_weights_gb": round(model_gb, 2),
            "activation_factor": round(act_factor, 3),
            "required_vram_gb": round(required_vram, 2),
            "gpu_vram_per_device_gb": gpu_vram,
            "min_gpus_by_memory": min_gpus_by_memory,
            "recommended_gpus_total": total_gpus,
            "nodes": nodes,
            "gpus_per_node": gpus_per_node,
            "estimated_hours": round(estimated_hours, 2) if estimated_hours is not None else None,
            "recommended_ttl_hours": ttl_hours,
            "recommended_disk_gb": disk_gb,
        },
        "gcp": {
            "project": args.project,
            "zone": args.zone,
            "gpu_type": args.gpu_type,
            "accelerator_type": accelerator_type,
            "machine_type": machine_type,
        },
        "commands": commands,
        "cost_estimate": cost_estimate,
        "warnings": warnings,
    }

    result["request_markdown"] = build_request_markdown(result)

    if args.output == "markdown":
        print(result["request_markdown"])
        print("\n### Commands")
        for key in ["create", "start", "stop", "delete", "inspect"]:
            print(f"- {key}: `{result['commands'][key]}`")
        if warnings:
            print("\n### Warnings")
            for w in warnings:
                print(f"- {w}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
