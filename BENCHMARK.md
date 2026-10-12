# FrameProof benchmark record

Method: benchmark.py, identical script on every machine, run
over the evaluation clips (coarse pass only). Numbers are
recorded with their machine line; nothing is compared across
different methods.

## Baseline, 2026-10-12 (local VM)
- machine: x86_64, 2 cores (host VM), Python 3.12.3,
  OpenCV 5.0.0
- 55 clips, 3,960 frames, 8.19 s total
- 2.069 ms per frame, 483 fps, 2.069 s per 1,000 frames

## PENDING: Graviton (Oct 15 gate)
Same script on a Graviton instance (COOL) and an x86 cloud
instance; add latency, throughput, and cost per 1,000 frames
from the instance hourly price. See ../AWS_RUNBOOK.md.
