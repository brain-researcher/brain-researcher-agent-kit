# SLURM Recipes

## Interactive Jobs

Do not run heavy computation on login nodes.

```bash
sdev
```

or

```bash
srun --mem=32G --pty bash
```

Exclusive interactive node example:

```bash
srun --exclusive --time 8:0:0 --pty bash
```

## Group Partition Example

```bash
srun -p <pi_group> --qos=<pi_group>_interactive --exclusive --time=48:00:00 --pty bash
```

## Batch Job Submission

```bash
sbatch -o out.%j -e err.%j yourScript.sh arg1 arg2
```

## Job Array Template

```bash
#!/bin/bash
#SBATCH -J firstlevel
#SBATCH --array=1-250%10
#SBATCH --time=02:30:00
#SBATCH -n 1
#SBATCH --cpus-per-task=16
#SBATCH --mem-per-cpu=4G
#SBATCH --qos=<pi_group>
#SBATCH -p <pi_group>
#SBATCH --export=NONE
#SBATCH -o %A-%a.out
#SBATCH -e %A-%a.err
#SBATCH --mail-user=<sunet>@stanford.edu
#SBATCH --mail-type=ALL

module use /share/PI/<pi_group>/modules
module load singularity
export FS_LICENSE=$PWD/.freesurfer.txt

# task command lines should be in tasks_list.sh (one command per line)
eval $(sed "${SLURM_ARRAY_TASK_ID}q;d" tasks_list.sh)
```

## Useful Queue Commands

```bash
sinfo
squeue -u <sunet>
squeue --start -u <sunet>
sstat -j <jobid>
sacct -j <jobid>
scancel <jobid>
scancel -u <sunet> --state=pending
```
