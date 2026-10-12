# Smoke test record, 2026-10-12 (local, OpenCV 5.0.0)

Fixtures are synthetic and purpose-made (tests/make_fixtures.py).
First run exposed a calibration lesson: the untextured sine pattern
was so smooth that the blur check fired on the CLEAN clip
(Laplacian var ~7 at 320x180). Adding film-like grain to the fixture
(not loosening the threshold) fixed realism; thresholds unchanged.

Final results, all as designed:
- clean.mp4  -> PASS, 1 shot
- frozen.mp4 -> FAIL, frozen_frames 0.50s-2.96s (first ~0.5s lost to
  mp4v encoder warm-up; acceptable, re-check on real codecs)
- flash.mp4  -> FAIL, flash_screen 12 flashes in a 1s window
  (plus expected shot_boundary spam inside the flash span; the agent
  layer must suppress boundary findings inside flash spans)
- cuts.mp4   -> PASS, 2 shots, cut found at exactly 1.50s

Next: YuNet + SFace identity-drift check, then the agent loop.
AWS/Graviton gate is Oct 15; organizer email reply due Oct 14.

## Identity-drift machinery, 2026-10-12 (local)
YuNet + SFace models from the OpenCV Zoo load and run under
OpenCV 5.0.0. Machinery test only, on local stills (never
submission material): same character across two views scored
cosine 0.684; a different character scored 0.37. The initial
0.45 drift threshold sits between the two, as intended.
Next: prop/object persistence + the agent loop.

## Agent loop, 2026-10-12 (local)
agent_run.py runs coarse pass -> dense native-res re-inspection ->
second opinion -> verdict, with a full step trace.
Fixtures: clean PASS, frozen REGEN NOTE, flash ESCALATE, cuts PASS.
One real bug found and fixed by measurement: the dense frozen check
used MAX frame diff, and mp4v keyframe-refresh spikes (2.67 on a
truly frozen clip; median diff 0.0) vetoed a true finding. Dense
rule now uses median diff + still-fraction >= 0.9.
The Oct 19 "agent loop live" gate is effectively met locally,
a week early. Remaining: prop persistence, deflicker auto-fix,
evaluation set, AWS/Graviton (Oct 15 gate).

## Flicker auto-fix + prop persistence, 2026-10-12 (local)
- flicker.mp4 (6 Hz luminance oscillation, below flash delta):
  agent verdict AUTO-FIX, deflicker executed, measured jitter
  0.0252 -> 0.0049 after the fix. The fix is verified by
  re-measurement, not assumed.
- prop.mp4 (textured prop patch present 0-2s, gone 2-3s):
  ORB persistence scan reads 75-78 good matches while present,
  exactly 0 once gone. Verdict FAIL with the missing span.
Engine status: coarse checks (boundaries, frozen, blur, flash
screen, flicker), identity drift (YuNet/SFace), prop persistence
(ORB), agent loop with dense re-inspection, second opinion,
verdicts PASS / AUTO-FIX / REGEN NOTE / ESCALATE and full traces.
Remaining: evaluation set, AWS/Graviton run (Oct 15 gate), UI,
submission packaging.
