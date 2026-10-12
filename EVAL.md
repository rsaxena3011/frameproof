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

## Batch 3 + Run 4, 2026-10-13: 59/61, then 61/61
Set expanded to 61 clips (tests/make_eval3.py): 4 more clean
seeds, a 3-shot cuts clip, end-of-clip freezes, a 0.5s mid
freeze, 10 Hz + near-threshold (0.03 amp) 6 Hz flicker, sigma
2.5 blur, a slower-cadence flash, and two new hard negatives
(slow dolly push-in, gentle exposure ramp).
Run at batch 3: 59/61. Two misses, one mine, one real:
1. flicker_7 read PASS. My fixture bug: 12 Hz flicker sampled
   at 24 fps aliases exactly to zero (sin(pi*t)=0 for integer
   t), so the clip contained NO oscillation at all. The agent
   was right; the fixture was wrong. Regenerated at 10 Hz.
2. frozen_mid_2 (12-frame freeze) read PASS. Real gap, in two
   layers. (a) Coarse: diff-runs are one shorter than
   frame-runs (11 zero diffs for a 12-frame freeze) and
   FROZEN_MIN_RUN was 12. Measured every PASS clip's max
   zero-diff run = 0 (grain + motion guarantee motion), so
   the floor was lowered 12 -> 8 frames with large margin;
   kept at 8, not lower, for headroom on noisier real footage.
   (b) Dense: the still fraction was measured over the padded
   span, so the 2 padded motion diffs ate the 0.9 budget on a
   short span (11/13 = 0.85). Fraction is now measured over
   the INTERIOR diffs of the reported span (11/11 = 1.0);
   the padded median still guards the boundary.
Re-run: 61/61, all five hand-built fixtures unchanged.
Standing lesson: a detector's floor is defined by its
shortest-span defect, not its average case; verify the floor
at both stages (coarse min-run AND dense confirm) whenever a
new span length enters the eval set.
