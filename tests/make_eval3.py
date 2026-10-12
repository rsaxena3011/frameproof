#!/usr/bin/env python3
"""Batch 3 of the FrameProof evaluation set: more defect variants and new
hard negatives. Appends to tests/eval/manifest.json (run make_eval.py and
make_eval2.py first). Brings the set to 60 clips.

New in this batch:
- clean seeds 14-17 (more clean content)
- cuts_6: three-shot clean clip
- frozen_tail_0/1: freeze at the END (the defect span matters, not only onset)
- frozen_mid_2: half-second mid freeze (shorter span)
- flicker_7: 12 Hz flicker; flicker_8: near-threshold 6 Hz (0.03 amp)
- blur_5: sigma 2.5 (stronger blur)
- flash_4: slower flash cadence (4 frames on/off)
- hardneg_dolly: slow push-in (legitimate camera move, must PASS)
- hardneg_exposure: gentle exposure ramp 60%->110% (legitimate, must PASS)
"""

import json
from pathlib import Path

import cv2
import numpy as np

from make_fixtures import texture

OUT = Path(__file__).parent / "eval"
W, H, FPS, SECS = 640, 360, 24, 3
N = FPS * SECS


def write_clip(name, frames):
    w = cv2.VideoWriter(str(OUT / name), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for f in frames:
        w.write(f)
    w.release()


def dolly(frame, factor):
    ch, cw = int(H / factor), int(W / factor)
    y0, x0 = (H - ch) // 2, (W - cw) // 2
    crop = frame[y0:y0 + ch, x0:x0 + cw]
    return cv2.resize(crop, (W, H), interpolation=cv2.INTER_LINEAR)


def main():
    manifest = json.loads((OUT / "manifest.json").read_text())
    have = {m["file"] for m in manifest}

    def add(name, defects, expected, frames):
        if name in have:
            print("skip (exists)", name)
            return
        write_clip(name, frames)
        manifest.append({"file": name, "defects": defects, "expected_verdict": expected})
        print("wrote", name, "->", expected)

    for i, seed in enumerate([14, 15, 16, 17]):
        add(f"clean_{12 + i}.mp4", [], "PASS", [texture(seed, t) for t in range(N)])

    frames = [texture(s, t) for s, t in
              [(3, t) for t in range(N // 3)] +
              [(8, t) for t in range(N // 3, 2 * N // 3)] +
              [(12, t) for t in range(2 * N // 3, N)]]
    add("cuts_6.mp4", [], "PASS", frames)

    for i, seed in enumerate([5, 9]):
        frames = [texture(seed, t) for t in range(2 * FPS)]
        frames += [frames[-1]] * (N - 2 * FPS)   # freeze the final second
        add(f"frozen_tail_{i}.mp4", ["frozen_frames"], "REGEN NOTE", frames)

    frames = [texture(7, t) for t in range(N)]
    mid = N // 2
    frames[mid:mid + FPS // 2] = [frames[mid]] * (FPS // 2)   # 0.5s freeze
    add("frozen_mid_2.mp4", ["frozen_frames"], "REGEN NOTE", frames)

    for name, freq, amp in [("flicker_7.mp4", 10, 0.05), ("flicker_8.mp4", 6, 0.03)]:
        frames = []
        for t in range(N):
            f = texture(3, t).astype(np.float32)
            f *= 1.0 + amp * np.sin(2 * np.pi * freq * t / FPS)
            frames.append(np.clip(f, 0, 255).astype(np.uint8))
        add(name, ["flicker"], "AUTO-FIX", frames)

    add("blur_5.mp4", ["blur"],
        "REGEN NOTE", [cv2.GaussianBlur(texture(6, t), (0, 0), 2.5) for t in range(N)])

    black = np.zeros((H, W, 3), np.uint8)
    white = np.full((H, W, 3), 255, np.uint8)
    add("flash_4.mp4", ["flash_screen"], "ESCALATE",
        [white if (t // 4) % 2 == 0 else black for t in range(N)])

    # Hard negatives: legitimate camera craft.
    add("hardneg_dolly.mp4", [], "PASS",
        [dolly(texture(1, t), 1.0 + 0.15 * t / N) for t in range(N)])

    frames = []
    for t in range(N):
        alpha = 0.6 + 0.5 * t / N
        frames.append(np.clip(texture(2, t).astype(np.float32) * alpha, 0, 255).astype(np.uint8))
    add("hardneg_exposure.mp4", [], "PASS", frames)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest now: {len(manifest)} clips")


if __name__ == "__main__":
    main()
