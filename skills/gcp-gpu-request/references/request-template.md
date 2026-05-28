# GCP GPU Request Template

Use this template when requesting temporary GPU resources.

```markdown
## GPU Resource Request

- Project:
- Zone:
- Workload:
- Mode (infer/finetune/train):
- Model size:
- Precision:
- Estimated VRAM required (GB):
- Proposed GPU type and count:
- Estimated runtime (hours):
- Proposed TTL window (hours):
- Proposed disk size (GB):
- Estimated hourly cost (USD):
- Estimated run cost (USD):
- Estimated TTL-window cost (USD):
- Why current resources are insufficient:
- Deprovision plan (stop/delete timing):
```

Always include explicit cleanup steps.
