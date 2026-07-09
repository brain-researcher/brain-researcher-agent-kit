#!/usr/bin/env bash
# Stage 1: fetch real fMRIPrep derivatives from the public OpenNeuro
# derivatives remote and stage a pruned BIDS + fMRIPrep tree for fitlins.
set -euo pipefail

: "${DERIV_REPO:?set DERIV_REPO to a local OpenNeuro fMRIPrep derivatives checkout}"
: "${RAW_DIR:?set RAW_DIR to the matching raw OpenNeuro BIDS checkout}"

TASK="${TASK:-fingerfootlips}"
SUBJECTS="${SUBJECTS:-01 02 03}"
SESSION="${SESSION:-test}"
SPACE="${SPACE:-MNI152NLin2009cAsym_res-2}"
ANNEX_REMOTE="${ANNEX_REMOTE:-openneuro-derivatives}"
STAGE="${STAGE:-${BR_NEUROPROGRAM_STAGE:-$PWD/.br_runs/neuroprogram_fitlins}}"

B="$STAGE/bids"
D="$STAGE/fmriprep"
rm -rf "$STAGE"
mkdir -p "$B" "$D" "$STAGE/models" "$STAGE/work"

sesseg=""
if [ -n "$SESSION" ]; then
  sesseg="ses-${SESSION}/"
fi

echo ">> pulling derivatives for subjects: $SUBJECTS (task=$TASK session=$SESSION space=$SPACE)"
cd "$DERIV_REPO"
files=()
for s in $SUBJECTS; do
  for kind in \
    "space-${SPACE}_desc-preproc_bold.nii.gz" \
    "space-${SPACE}_desc-preproc_bold.json" \
    "space-${SPACE}_desc-brain_mask.nii.gz" \
    "desc-confounds_timeseries.tsv" \
    "desc-confounds_timeseries.json"; do
    f=$(find "sub-$s/${sesseg}func" -name "*task-${TASK}*${kind}" 2>/dev/null | head -1 || true)
    if [ -n "$f" ]; then
      files+=("$f")
    fi
  done
done

if [ "${#files[@]}" -eq 0 ]; then
  echo "ERROR: no derivative files matched" >&2
  exit 1
fi
git annex get --from="$ANNEX_REMOTE" "${files[@]}"

echo ">> staging pruned BIDS + fMRIPrep trees at $STAGE"
cp "$RAW_DIR/dataset_description.json" "$B/"
cp "$RAW_DIR/task-${TASK}_bold.json" "$B/" 2>/dev/null || true
cp "$RAW_DIR/task-${TASK}_events.tsv" "$B/" 2>/dev/null || true
cp "$DERIV_REPO/dataset_description.json" "$D/"

for s in $SUBJECTS; do
  mkdir -p "$B/sub-$s/${sesseg}func" "$D/sub-$s/${sesseg}func"
  raw_func="$RAW_DIR/sub-$s/${sesseg}func"
  deriv_func="$DERIV_REPO/sub-$s/${sesseg}func"

  raw_bold=$(find "$raw_func" -name "*task-${TASK}_bold.nii.gz" 2>/dev/null | head -1 || true)
  if [ -n "$raw_bold" ]; then
    ln -sf "$(readlink -f "$raw_bold")" "$B/sub-$s/${sesseg}func/$(basename "$raw_bold")"
  fi

  while IFS= read -r ev; do
    [ -n "$ev" ] || continue
    ln -sf "$(readlink -f "$ev")" "$B/sub-$s/${sesseg}func/$(basename "$ev")"
  done < <(find "$raw_func" -name "*task-${TASK}*events.tsv" 2>/dev/null || true)

  while IFS= read -r f; do
    [ -n "$f" ] || continue
    resolved=$(readlink -f "$f" 2>/dev/null || true)
    if [ -e "$resolved" ]; then
      ln -sf "$resolved" "$D/sub-$s/${sesseg}func/$(basename "$f")"
    fi
  done < <(find "$deriv_func" -name "*task-${TASK}*" 2>/dev/null || true)
done

echo ">> verifying staged derivative symlinks"
n_real=0
while IFS= read -r f; do
  resolved=$(readlink -f "$f" 2>/dev/null || true)
  if [ -e "$resolved" ]; then
    n_real=$((n_real + 1))
  else
    echo "BROKEN $f" >&2
  fi
done < <(find "$D" -type l 2>/dev/null || true)
echo ">> $n_real real derivative symlinks staged under $D"
echo ">> STAGE ready: $STAGE"
