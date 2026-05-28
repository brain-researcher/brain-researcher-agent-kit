# GPU Sizing Heuristics

These are planning heuristics, not exact profiler outputs.

## VRAM Estimate

1. Base model memory:

```text
model_gb = params * bytes_per_param / 1024^3
```

2. Mode multiplier:
- infer: `1.3`
- finetune: `2.6`
- train: `6.0`

3. Activation overhead (from seq_len and batch):

```text
activation_factor = 1 + min(2.0, (seq_len / 4096) * (batch_size / 8) * 0.2)
```

4. Safety factor: default `1.2`

Final:

```text
required_vram_gb = model_gb * mode_multiplier * activation_factor * safety_factor
```

## Runtime Estimate

Use one of:

- Token-based:

```text
hours = total_tokens / (tokens_per_sec_per_gpu * num_gpus * utilization) / 3600
```

- Step-based:

```text
hours = total_steps * sec_per_step_per_gpu / (num_gpus * utilization) / 3600
```

Where `utilization` defaults to `0.75`.

## Disk Estimate

```text
recommended_disk_gb = max(100, ceil(dataset_gb * 1.5 + checkpoint_gb + 30))
```

`checkpoint_gb` is estimated from model size and number of checkpoints.

## Cost Estimate

Hourly estimate:

```text
hourly_cost_usd =
  nodes * gpus_per_node * gpu_hourly_usd_per_device * spot_multiplier
  + nodes * vm_hourly_usd_per_node * spot_multiplier
  + nodes * disk_gb * disk_hourly_usd_per_gb
```

Where:
- `spot_multiplier = 1 - spot_discount_fraction` when using spot, else `1`.
- `run_cost_usd = hourly_cost_usd * run_window_hours`
- `ttl_cost_usd = hourly_cost_usd * ttl_hours`
