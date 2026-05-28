# Few-Shot Calibration Examples

Use these examples to calibrate ranking logic, not to copy scores verbatim.

## Example 1: Algorithm-first contribution

Input idea:
"A new multimodal Transformer improves fMRI-text decoding by 10% over SOTA,
with extensive ablations but no new neuroscience mechanism."

Expected ranking direction:
1. `medical_image_analysis`
2. `ieee_tmi`
3. `imaging_neuroscience`
4. `nature_neuroscience`

## Example 2: Mechanism-first contribution

Input idea:
"Encoding analyses reveal a previously unreported hierarchical semantic map in
DMN subregions during natural language processing."

Expected ranking direction:
1. `nature_neuroscience`
2. `neuron`
3. `imaging_neuroscience`
4. `medical_image_analysis`

## Example 3: Imaging-method rigor paper

Input idea:
"A cross-subject alignment and denoising pipeline improves reproducibility of
task-fMRI effects and includes full QC and multiple-comparison controls."

Expected ranking direction:
1. `imaging_neuroscience`
2. `neuroimage`
3. `human_brain_mapping`
4. `nature_neuroscience`

## Example 4: Weak baseline and overclaim risk

Input idea:
"A model reports high performance on one private dataset and claims a new brain
theory, but no ablations or robust controls are provided."

Expected output behavior:
- Return low confidence and include gating risks.
- Recommend concrete upgrades (ablations, external validation, statistics).
