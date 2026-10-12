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
