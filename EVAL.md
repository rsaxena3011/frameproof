# FrameProof evaluation

Purpose-made labeled set: 26 clips (tests/eval/, regenerable via
tests/make_eval.py, labels in manifest.json). Classes: clean x6,
clean multi-shot x4, frozen-tail x4, flash x3, flicker x4,
blur x3, hard negatives x2 (slow zoom, dark scene). Metric:
agent verdict vs expected verdict (eval_run.py).

## Run 1, 2026-10-12: 25/26 (96.2%)
One miss, exactly the kind the hard negatives exist to catch:
the dark scene (clean content at 35% brightness) was convicted
of blur. Cause measured: absolute Laplacian variance collapses
with brightness (dark clean 6.0 vs blurred 7.9: indistinguishable
on the absolute scale). 

## Fix: contrast-normalized sharpness
Blur now requires Laplacian variance < 45 AND ratio
(Laplacian var / gray var) < 0.008, in both the coarse pass
and the dense re-inspection. Measured separation: bright clean
ratio 0.046, dark clean 0.018, blurred 0.003.

## Run 2, 2026-10-12: 26/26 (100%)
All classes correct, both hard negatives pass, all five
hand-built fixtures unchanged (clean PASS, frozen REGEN NOTE,
flash ESCALATE, cuts PASS, flicker AUTO-FIX).

## Honest limits
Synthetic set, small n, verdict-level metric only. The real
eval (40-60 clips incl. generated-video material and span
localization scoring) is still owed before submission; this
run proves the harness and caught one real bug.

## Batch 2 + Run 3, 2026-10-12: 45/47, then 47/47
Set expanded to 47 clips (more seeds, mid-clip freezes, 3 Hz and
near-threshold flicker, milder blur, four new hard negatives:
fast pan, camera shake, fade, one lightning strike).
Run at batch 2: 45/47. Two misses, both in the flicker measure:
1. flicker_4 (3 Hz) read PASS. Its oscillation is real but the
   global detrended std (0.0105) sat under the 0.015 threshold.
2. hardneg_lightning read AUTO-FIX. One 2-frame lightning spike
   inflated the GLOBAL jitter to 0.053 while its per-window
   median was 0.0001: a transient impersonating flicker.
Fix: flicker is now the MEDIAN of per-0.5s-window detrended
jitter (coarse threshold 0.008, dense confirm 0.006), in both
stages. Measured separation: clean windows peak at 0.001,
weakest true flicker 0.0105 in every window, lightning median
0.0001. Re-run: 47/47, fixtures unchanged.
Standing lesson, twice proven in one evening: global statistics
hide exactly the local structure QC exists to catch. Measure
in windows, confirm in spans.
