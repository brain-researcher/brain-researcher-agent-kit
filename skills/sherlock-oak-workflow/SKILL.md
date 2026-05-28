---
name: sherlock-oak-workflow
description: Guide Stanford Sherlock cluster access, OAK-oriented storage decisions, and SLURM execution patterns for interactive and batch workloads. Use when a user needs Sherlock login setup, SSH/2FA troubleshooting, filesystem path selection (HOME/PI_HOME/SCRATCH/PI_SCRATCH/OAK), data transfer commands, module setup, or safe srun/sbatch/job-array templates.
---

# Sherlock OAK Workflow

## Overview

Use this skill to provide operational guidance for Sherlock and OAK with minimal risk.
Default to Sherlock 2 login and current paths. Treat Sherlock 1 instructions as legacy only.

## Workflow

1. Confirm access preconditions:
   - SUNet account enabled for Sherlock
   - Duo/2FA configured
   - PI group access (for example, OAK group path)
2. Provide correct login command and quick verification.
3. Route storage choices to the right filesystem.
4. Choose execution mode:
   - Interactive `srun`/`sdev`
   - Batch `sbatch`
   - Job arrays for many independent tasks
5. Include data movement commands (`rsync`, optional `sshfs`) and quota checks.

## Login Rules

1. Prefer Sherlock 2:

```bash
ssh <sunet>@login.sherlock.stanford.edu
```

2. If first-time access fails, instruct user to request PI/admin enablement and group filesystem permissions.
3. Do not suggest doing compute-heavy work on login nodes.

For details and legacy notes, read `references/login-and-access.md`.

## Storage Routing Rules

1. Use `$HOME` for small code/config only.
2. Use `$PI_HOME` for shared, non-purged group resources.
3. Treat `$SCRATCH` and `$PI_SCRATCH` as purgeable.
4. Use `$LOCAL_SCRATCH` only for per-job temporary files.
5. Store durable datasets under `$OAK/data/...`.
6. For restricted datasets, apply ACL-based access control and document DUA access rules.
7. For finalized shared datasets, set read-only permissions (`550` dirs, `440` files).

Read `references/storage-and-paths.md` before giving path advice.

## Execution Rules

1. Interactive debugging:

```bash
sdev
# or
srun --mem=32G --pty bash
```

2. Batch jobs:

```bash
sbatch -o out.%j -e err.%j yourScript.sh arg1 arg2
```

3. Job arrays for many independent tasks; include `%N` concurrency cap.
4. For group partition usage, include explicit partition/qos in examples.

Read `references/slurm-recipes.md` for templates.

## Data Transfer Rules

1. Prefer `rsync` for large transfers and resumable copies.
2. Offer `sshfs` as optional local mount when user explicitly requests local editing workflow.
3. Always include an unmount command when giving mount instructions.

## Safety and Accuracy

1. Mark legacy Sherlock 1 content as outdated.
2. Do not claim quota values unless user provides current outputs.
3. Prefer environment variables (`$HOME`, `$PI_HOME`, `$OAK`) over hardcoded absolute paths.
4. For security, avoid suggesting plaintext credential storage.

## Quick Commands

Use local preflight helper:

```bash
bash skills/sherlock-oak-workflow/scripts/sherlock_preflight.sh --sunet <sunetid> --pi-group <pi_group>
```

Restrict DUA dataset access (dry-run by default):

```bash
bash skills/sherlock-oak-workflow/scripts/restrict_acl.sh \
  --dir /oak/stanford/groups/<pi_group>/data/<dataset> \
  --user <sunetid> \
  --group oak_<pi_group>
```

Freeze finalized dataset permissions (dry-run by default):

```bash
bash skills/sherlock-oak-workflow/scripts/lock_dataset_readonly.sh \
  --dir /oak/stanford/groups/<pi_group>/data/<dataset>
```

Initialize required dataset README:

```bash
bash skills/sherlock-oak-workflow/scripts/init_dataset_readme.sh \
  --dataset "<dataset>" \
  --owners "<owner1>, <owner2>" \
  --description "<description>" \
  --provenance "<source and date>" \
  --access "<who can access and procedure>" \
  --out /oak/stanford/groups/<pi_group>/data/<dataset>/README.md
```

## Resources

### references/

- `login-and-access.md`: Sherlock login, first-time onboarding, and legacy notes.
- `storage-and-paths.md`: Filesystem decision table and quota checks.
- `slurm-recipes.md`: Interactive, batch, and job-array templates.

### scripts/

- `sherlock_preflight.sh`: Local readiness checks and command hints.
- `restrict_acl.sh`: Apply ACL restrictions for DUA-limited dataset access.
- `lock_dataset_readonly.sh`: Apply read-only permissions to finalized datasets.
- `init_dataset_readme.sh`: Generate required dataset README metadata file.
