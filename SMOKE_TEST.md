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
