#!/usr/bin/env python3
"""Batch 2 of the FrameProof evaluation set: harder variants and more
hard negatives. Appends to tests/eval/manifest.json (run make_eval.py
first). Brings the set to 48 clips.
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

    for i, seed in enumerate([8, 9, 10, 11, 12, 13]):
        add(f"clean_{6 + i}.mp4", [], "PASS", [texture(seed, t) for t in range(N)])

    for i, seeds in enumerate([(1, 4, 2), (5, 2, 7)]):
        frames = [texture(seeds[t * 3 // N], t) for t in range(N)]
        add(f"cuts_{4 + i}.mp4", [], "PASS", frames)

    for i in range(2):
        frames = [texture(2 + i, t) for t in range(FPS)]
        frames += [frames[-1]] * FPS
        frames += [texture(2 + i, t) for t in range(FPS)]
        add(f"frozen_mid_{i}.mp4", ["frozen_frames"], "REGEN NOTE", frames)

    frames = [texture(9, 0)] * N
    add("frozen_full.mp4", ["frozen_frames"], "REGEN NOTE", frames)

    for name, freq, amp in [("flicker_4.mp4", 3, 0.06), ("flicker_5.mp4", 9, 0.05),
                            ("flicker_6.mp4", 6, 0.04)]:
        frames = []
        for t in range(N):
            f = texture(3, t).astype(np.float32)
            f *= 1.0 + amp * np.sin(2 * np.pi * freq * t / FPS)
            frames.append(np.clip(f, 0, 255).astype(np.uint8))
        add(name, ["flicker"], "AUTO-FIX", frames)

    for name, sigma in [("blur_3.mp4", 2.0), ("blur_4.mp4", 1.5)]:
        frames = [cv2.GaussianBlur(texture(6, t), (0, 0), sigma) for t in range(N)]
        add(name, ["blur"], "REGEN NOTE", frames)

    black = np.zeros((H, W, 3), np.uint8)
    white = np.full((H, W, 3), 255, np.uint8)
    add("flash_3.mp4", ["flash_screen"], "ESCALATE",
        [white if (t // 3) % 2 == 0 else black for t in range(N)])

    # Hard negatives: legitimate dramatic content.
    add("hardneg_pan.mp4", [], "PASS",
        [np.roll(texture(1, t), t * 6, axis=1) for t in range(N)])

    frames = []
    for t in range(N):
        f = np.clip(texture(4, t).astype(np.float32) * 0.3, 0, 255).astype(np.uint8)
        if FPS <= t < FPS + 2:
            f = np.clip(f.astype(np.float32) * 4.0, 0, 255).astype(np.uint8)
        frames.append(f)
    add("hardneg_lightning.mp4", [], "PASS", frames)

    rng = np.random.default_rng(3)
    frames = []
    for t in range(N):
        f = texture(5, t)
        dx, dy = int(rng.integers(-3, 4)), int(rng.integers(-3, 4))
        frames.append(np.roll(np.roll(f, dx, axis=1), dy, axis=0))
    add("hardneg_shake.mp4", [], "PASS", frames)

    frames = []
    for t in range(N):
        alpha = 1.0 - 0.85 * np.sin(np.pi * t / N)
        frames.append(np.clip(texture(2, t).astype(np.float32) * alpha, 0, 255).astype(np.uint8))
    add("hardneg_fade.mp4", [], "PASS", frames)

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"manifest now: {len(manifest)} clips")


if __name__ == "__main__":
    main()
