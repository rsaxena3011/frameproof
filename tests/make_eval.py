#!/usr/bin/env python3
"""Generate the labeled FrameProof evaluation set (purpose-made clips).

24 clips across 6 classes with an expected agent verdict per clip,
written to tests/eval/manifest.json. Classes: clean, cuts (clean
multi-shot), frozen (motion, then a frozen tail), flash, flicker,
blur. Plus 2 hard negatives: slow zoom and a dark scene (both clean).
"""

import json
from pathlib import Path

import cv2
import numpy as np

from make_fixtures import texture, writer  # noqa: F401  (writer unused here)

OUT = Path(__file__).parent / "eval"
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, SECS = 640, 360, 24, 3
N = FPS * SECS


def write_clip(name, frames):
    w = cv2.VideoWriter(str(OUT / name), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    for f in frames:
        w.write(f)
    w.release()


def main():
    manifest = []

    def add(name, defects, expected, frames):
        write_clip(name, frames)
        manifest.append({"file": name, "defects": defects, "expected_verdict": expected})
        print("wrote", name, "->", expected)

    for i, seed in enumerate([1, 2, 3, 5, 6, 7]):
        add(f"clean_{i}.mp4", [], "PASS", [texture(seed, t) for t in range(N)])

    for i, seeds in enumerate([(1, 4), (2, 5), (3, 6), (7, 1)]):
        frames = [texture(seeds[0], t) if t < N // 2 else texture(seeds[1], t) for t in range(N)]
        add(f"cuts_{i}.mp4", [], "PASS", frames)

    for i in range(4):
        frames = [texture(2 + i, t) for t in range(FPS)]
        still = frames[-1]
        frames += [still] * (N - FPS)
        add(f"frozen_{i}.mp4", ["frozen_frames"], "REGEN NOTE", frames)

    for i in range(3):
        black = np.zeros((H, W, 3), np.uint8)
        white = np.full((H, W, 3), 255, np.uint8)
        frames = [white if (t // 2) % 2 == 0 else black for t in range(N)]
        add(f"flash_{i}.mp4", ["flash_screen"], "ESCALATE", frames)

    for i, (freq, amp) in enumerate([(5, 0.05), (6, 0.06), (7, 0.05), (6, 0.08)]):
        frames = []
        for t in range(N):
            f = texture(1 + i, t).astype(np.float32)
            f *= 1.0 + amp * np.sin(2 * np.pi * freq * t / FPS)
            frames.append(np.clip(f, 0, 255).astype(np.uint8))
        add(f"flicker_{i}.mp4", ["flicker"], "AUTO-FIX", frames)

    for i in range(3):
        frames = [cv2.GaussianBlur(texture(3 + i, t), (0, 0), 3) for t in range(N)]
        add(f"blur_{i}.mp4", ["blur"], "REGEN NOTE", frames)

    # Hard negatives: dramatic but legitimate content.
    frames = []
    for t in range(N):
        big = cv2.resize(texture(1, t), (W * 2, H * 2))
        s = 1.0 + 0.25 * t / N
        cw, ch = int(W * s), int(H * s)
        x, y = (2 * W - cw) // 2, (2 * H - ch) // 2
        frames.append(cv2.resize(big[y:y + ch, x:x + cw], (W, H)))
    add("hardneg_zoom.mp4", [], "PASS", frames)

    frames = [np.clip(texture(4, t).astype(np.float32) * 0.35, 0, 255).astype(np.uint8)
              for t in range(N)]
    add("hardneg_dark.mp4", [], "PASS", frames)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {len(manifest)} clips")


if __name__ == "__main__":
    main()
