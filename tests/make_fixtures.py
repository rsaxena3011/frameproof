#!/usr/bin/env python3
"""Generate synthetic smoke-test fixtures (purpose-made, no third-party footage).

clean.mp4  : moving textured pattern, no defects         -> expect PASS
frozen.mp4 : one static frame for 3s                     -> expect FAIL (frozen)
flash.mp4  : black/white alternating every 2 frames      -> expect FAIL (flash)
cuts.mp4   : two different patterns with a hard cut      -> expect PASS, 2 shots
"""

import cv2
import numpy as np
from pathlib import Path

OUT = Path(__file__).parent / "fixtures"
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS, SECS = 640, 360, 24, 3
N = FPS * SECS


def writer(name):
    return cv2.VideoWriter(
        str(OUT / name), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H)
    )


def texture(seed_shift: int, t: int) -> np.ndarray:
    x = np.linspace(0, 6, W, dtype=np.float32)[None, :]
    y = np.linspace(0, 6, H, dtype=np.float32)[:, None]
    base = (np.sin(x * 3 + t * 0.3 + seed_shift) + np.cos(y * 4 - t * 0.2)) * 60 + 128
    img = np.repeat(base[:, :, None], 3, axis=2)
    img[:, :, 0] = np.clip(img[:, :, 0] * 0.7 + seed_shift * 10, 0, 255)
    img[:, :, 2] = np.clip(img[:, :, 2] * 0.7 + (5 - seed_shift) * 12, 0, 255)
    # Film-like grain so the blur check sees realistic texture levels.
    grain = np.random.default_rng(1000 + t).normal(0, 9, img.shape)
    return np.clip(img + grain, 0, 255).astype(np.uint8)


def main():
    w = writer("clean.mp4")
    for t in range(N):
        w.write(texture(1, t))
    w.release()

    still = texture(2, 0)
    w = writer("frozen.mp4")
    for _ in range(N):
        w.write(still)
    w.release()

    w = writer("flash.mp4")
    black = np.zeros((H, W, 3), np.uint8)
    white = np.full((H, W, 3), 255, np.uint8)
    for t in range(N):
        w.write(white if (t // 2) % 2 == 0 else black)
    w.release()

    w = writer("cuts.mp4")
    for t in range(N):
        w.write(texture(1, t) if t < N // 2 else texture(4, t))
    w.release()

    print("fixtures written to", OUT)


if __name__ == "__main__":
    main()
