# FrameProof

An agentic QC inspector for AI-generated video. Generators ship
defects that humans catch late: faces that drift off-model, frames
that freeze, flicker, seizure-risk flashing, props that vanish,
shots gone soft. FrameProof inspects a clip the way a good QC
engineer would: a fast pass first, a hard second look at anything
suspicious, a second opinion before any conviction, and a human
with the final word. Entry for the OpenCV AI Competition 2026.

## The agent loop

1. **Coarse pass** (OpenCV 5, deterministic): shot boundaries,
   frozen-frame runs, blur, a rough WCAG three-flash screen,
   temporal flicker.
2. **Dense re-inspection**: every suspect span is re-measured at
   native resolution with a method suited to that check.
3. **Second opinion**: if the dense measurement disagrees with
   the coarse one, the finding is downgraded and the clip is
   escalated to a human instead of auto-judged.
4. **Verdicts**: PASS, AUTO-FIX (the fix is executed and then
   re-measured to prove it worked), REGEN NOTE (generation
   defects a human should send back), ESCALATE (safety findings
   and disagreements). Every step is written to a trace.

Specialist scans plug into the same loop: face identity drift
(YuNet detection + SFace embeddings against a reference still)
and prop persistence (ORB feature matching against a reference
crop).

## Checks

| Check | Method | Catches |
|---|---|---|
| Shot boundaries | HSV histogram correlation | unintended cuts, merged shots |
| Frozen frames | per-frame mean abs diff runs | stalled generation, dup frames |
| Blur | Laplacian variance + contrast-normalized ratio | soft or smeared shots |
| Flash screen | luminance swings per 1s window | photosensitivity risk (rough screen, not a certification) |
| Flicker | windowed-median detrended jitter | temporal instability |
| Identity drift | YuNet + SFace cosine vs reference | character face morphing |
| Prop persistence | ORB matches vs reference crop | props dropped or swapped |

## Evaluation

47 purpose-made labeled clips (clean, multi-shot, frozen, flash,
flicker, blur, plus hard negatives: dark scene, slow zoom, fast
pan, camera shake, fade, a single lightning strike). Current
score: 47/47 verdict accuracy. The set has already caught two
real bugs, both fixed by measurement, not by loosening the net:
dark scenes falsely convicted of blur, and a lightning transient
impersonating flicker. Full record: EVAL.md. Fixture smoke tests:
SMOKE_TEST.md.

## Run it

```
pip install -r requirements.txt
python3 frameproof.py clip.mp4            # coarse pass CLI
python3 agent_run.py clip.mp4             # full agent loop
python3 agent_run.py clip.mp4 --reference face.png
python3 app.py                            # web UI on :5050
python3 eval_run.py                       # evaluation harness
python3 tests/make_fixtures.py            # regenerate fixtures
```

Models (YuNet, SFace) are fetched from the OpenCV Zoo into
models/ and are not committed.

## Cloud plan

Designed for AWS: S3 ingest, a job queue, Graviton workers, with
a COOL benchmark (Graviton vs x86: latency, throughput, cost per
1,000 frames) as part of the evidence pack. The local engine in
this repo is the reference implementation the workers run.

## Honesty notes

The flash check is a rough three-flash screen, not a WCAG
certification. Thresholds are initial values calibrated on the
purpose-made evaluation set; the eval record states its own
limits. Test material is purpose-made only.
