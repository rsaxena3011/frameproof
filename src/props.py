"""FrameProof prop persistence (ORB feature matching).

Given a reference crop of a prop that must stay in the scene, sample
the video and report spans where the prop can no longer be found:
the generator dropped it, swapped it, or let it morph away.
"""

from __future__ import annotations

import cv2
import numpy as np

MIN_GOOD_MATCHES = 10  # initial threshold, to be calibrated on the eval set


def _orb():
    return cv2.ORB_create(nfeatures=2000)


def _good_matches(des_ref, des_frame) -> int:
    if des_ref is None or des_frame is None:
        return 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = bf.knnMatch(des_ref, des_frame, k=2)
    good = 0
    for pair in pairs:
        if len(pair) == 2:
            m, n = pair
            if m.distance < 0.75 * n.distance:
                good += 1
    return good


def persistence_scan(video: str, prop_image: str, sample_every_s: float = 0.5) -> dict:
    prop = cv2.imread(prop_image, cv2.IMREAD_GRAYSCALE)
    if prop is None:
        raise RuntimeError(f"cannot read prop image: {prop_image}")
    orb = _orb()
    _, des_ref = orb.detectAndCompute(prop, None)
    if des_ref is None:
        raise RuntimeError("prop image has no usable texture (ORB found nothing)")

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    step = max(1, int(round(fps * sample_every_s)))
    samples, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            _, des = orb.detectAndCompute(gray, None)
            m = _good_matches(des_ref, des)
            samples.append({"t": round(idx / fps, 2), "matches": m, "present": m >= MIN_GOOD_MATCHES})
        idx += 1
    cap.release()
    missing = [s for s in samples if not s["present"]]
    return {
        "video": video,
        "prop": prop_image,
        "samples": samples,
        "missing_samples": missing,
        "verdict": "FAIL" if missing else "PASS",
    }
