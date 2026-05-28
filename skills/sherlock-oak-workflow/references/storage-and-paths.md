# Storage And Paths

Use environment variables over hardcoded paths where possible.

## Filesystem Routing

- `$HOME`
  - Typical path: `/home/users/<sunet>`
  - Use for: small code, configs, personal tools
  - Avoid for: large datasets

- `$PI_HOME`
  - Typical path: `/home/groups/<pi_group>`
  - Use for: shared lab software and shared non-purged project assets

- `$SCRATCH`
  - Typical path: `/scratch/users/<sunet>`
  - Use for: large temporary working files
  - Caveat: purgeable

- `$PI_SCRATCH`
  - Typical path: `/scratch/PI/<pi_group>`
  - Use for: group temporary working area
  - Caveat: purgeable

- `$LOCAL_SCRATCH`
  - Node-local temporary storage during jobs
  - Caveat: deleted after job completes

- `$OAK`
  - Use for durable group datasets, for example `$OAK/data/...`
  - Preferred for long-term data retention

## Quota And Usage Checks

```bash
df -h $HOME
df -h $SCRATCH
lfs quota -u <sunetid> -h /scratch/
lfs quota -g <pi_group> -h /scratch/
find . -type f | wc -l
```

## Ownership Reminder

User-owned files count toward user quota; group-owned files count toward group quota; dual ownership can impact both.
