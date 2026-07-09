#!/usr/bin/env bash
# Stage 3: run fitlins once per multiverse variant model.
set -euo pipefail

STAGE="${STAGE:-${BR_NEUROPROGRAM_STAGE:-$PWD/.br_runs/neuroprogram_fitlins}}"
SPACE_NAME="${SPACE_NAME:-MNI152NLin2009cAsym}"
SUBJECTS="${SUBJECTS:-01 02 03}"
NCPUS="${NCPUS:-2}"
VARIANTS="${VARIANTS:-mv01 mvB mvC}"

export TEMPLATEFLOW_HOME="${TEMPLATEFLOW_HOME:-$STAGE/templateflow}"
export MPLBACKEND=Agg
mkdir -p "$TEMPLATEFLOW_HOME"

for v in $VARIANTS; do
  model="$STAGE/models/model-$v.json"
  out="$STAGE/out_$v"
  if [ ! -f "$model" ]; then
    echo "SKIP $v: missing $model"
    continue
  fi
  echo ">> fitlins $v"
  fitlins "$STAGE/bids" "$out" dataset \
    -d "$STAGE/fmriprep" \
    -m "$model" \
    --space "$SPACE_NAME" \
    --estimator nilearn \
    --participant-label $SUBJECTS \
    -w "$STAGE/work_$v" \
    --n-cpus "$NCPUS"
  n=$(find "$out" -name "*stat-z_statmap.nii.gz" 2>/dev/null | wc -l)
  echo ">> $v done: $n stat-z maps"
done

echo ">> all variants done under $STAGE/out_<variant>/"
