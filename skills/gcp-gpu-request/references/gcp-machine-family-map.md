# GCP GPU Family Map

Default mapping in this skill:

- `l4`
  - accelerator type: `nvidia-l4`
  - family: `g2-standard-*`

- `a100-40`
  - accelerator type: `nvidia-tesla-a100`
  - family: `a2-highgpu-*`

- `a100-80`
  - accelerator type: `nvidia-a100-80gb`
  - family: `a2-ultragpu-*`

- `h100`
  - accelerator type: `nvidia-h100-80gb`
  - family: `a3-highgpu-*`

## Notes

1. Exact availability depends on zone and quotas.
2. Use planner output as baseline, then verify with:

```bash
gcloud compute accelerator-types list --zones <zone>
gcloud compute machine-types list --zones <zone>
```

3. If requested GPU count does not match family constraints, round to the nearest supported configuration.
