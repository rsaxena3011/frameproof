# FrameProof

Agentic quality control for AI-generated video, built on OpenCV 5.
Entry for the OpenCV AI Competition 2026 (C056).

FrameProof inspects a generated clip the way a release engineer would:
a fast deterministic coarse pass, dense re-inspection of suspect spans,
and a verdict with evidence: PASS, AUTO-FIX, REGEN NOTE, or ESCALATE
to a human.

## Coarse pass (working now)

`python3 frameproof.py <video>` runs the deterministic checks:

- Shot boundaries (HSV histogram correlation)
- Frozen-frame runs (near-zero inter-frame difference)
- Blur / softness (Laplacian variance)
- Flash screen: a rough WCAG three-flash screen (not a certification)
- Temporal luminance jitter

Exit codes: 0 PASS, 1 WARN, 2 FAIL, 3 error. `--json` for the full
structured report.

## Smoke test

`python3 tests/make_fixtures.py` generates four purpose-made synthetic
clips (clean / frozen / flashing / hard cut). Expected: PASS, FAIL,
FAIL, PASS with the cut found at exactly 1.50s. Verified 2026-10-12,
see SMOKE_TEST.md.

## Roadmap

- Face-identity drift (YuNet + SFace against reference stills)
- Prop/object persistence across shots
- Agent loop: coarse pass, dense re-inspection, second opinion,
  verdicts with full step traces
- AWS run: S3 + queue + Graviton workers, COOL benchmarked against x86
- Evaluation: 40-60 purpose-made test clips, precision/recall against
  a fixed-pipeline baseline and a VLM-only baseline
