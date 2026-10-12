#!/usr/bin/env python3
"""FrameProof coarse-pass benchmark.

Times the deterministic coarse pass over a folder of clips and
reports throughput in the units the COOL rubric cares about:
ms per frame, frames per second, and seconds per 1,000 frames.
Run the identical script on x86 and on Graviton so the numbers
are comparable; record the machine line with the results.

Usage: python3 benchmark.py [folder]   (default: tests/eval)
"""

import json
import platform
import sys
import time
from pathlib import Path

import cv2

from src.checks import analyse


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/eval")
    clips = sorted(folder.glob("*.mp4"))
    if not clips:
        print(f"no .mp4 clips in {folder}")
        return 3
    total_frames, total_time = 0, 0.0
    per_clip = []
    for clip in clips:
        t0 = time.perf_counter()
        report = analyse(str(clip))
        dt = time.perf_counter() - t0
        total_frames += report["frames"]
        total_time += dt
        per_clip.append({"clip": clip.name, "frames": report["frames"],
                         "seconds": round(dt, 3)})
    result = {
        "machine": platform.machine(),
        "processor": platform.processor() or "unknown",
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "clips": len(clips),
        "frames": total_frames,
        "total_seconds": round(total_time, 3),
        "ms_per_frame": round(1000 * total_time / total_frames, 3),
        "fps": round(total_frames / total_time, 1),
        "seconds_per_1000_frames": round(1000 * total_time / total_frames, 3),
        "per_clip": per_clip,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
