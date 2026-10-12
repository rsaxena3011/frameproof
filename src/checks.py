"""FrameProof deterministic checks (OpenCV 5, no learned models).

Each check returns findings as span dicts:
  {check, start_frame, end_frame, start_s, end_s, severity, detail}
Severity is one of: info, warn, fail.
These checks are the coarse pass of the FrameProof agent loop; suspect
spans get re-inspected densely by later stages.
"""

from __future__ import annotations

import cv2
import numpy as np

# --- thresholds (initial, to be calibrated on the eval set) -----------------
SHOT_HIST_CORR_MIN = 0.72      # below this HSV-hist correlation = cut
FROZEN_MEAN_ABS_DIFF = 0.35    # per-pixel mean abs diff (0-255 scale)
FROZEN_MIN_RUN = 12            # frames (~0.5s at 24fps)
BLUR_LAPLACIAN_VAR_MIN = 45.0  # below this a frame counts as soft
BLUR_RATIO_MIN = 0.008         # laplacian var / gray var: darkness alone
                               # lowers laplacian var, real blur lowers
                               # the ratio (eval: bright clean 0.046,
                               # dark clean 0.018, blurred 0.003)
FLASH_DELTA_LUMA = 0.18        # relative luminance swing counting as a flash
FLASH_MAX_PER_SECOND = 3       # WCAG three-flash general threshold (screen)
FLICKER_JITTER_MIN = 0.015     # detrended luminance std above this = flicker


def _spans_from_flags(flags: np.ndarray, min_run: int) -> list[tuple[int, int]]:
    spans, start = [], None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            if i - start >= min_run:
                spans.append((start, i - 1))
            start = None
    if start is not None and len(flags) - start >= min_run:
        spans.append((start, len(flags) - 1))
    return spans


def analyse(path: str) -> dict:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0

    prev_gray = prev_hist = None
    hist_corr: list[float] = []
    mean_abs_diff: list[float] = []
    lap_var: list[float] = []
    lap_ratio: list[float] = []
    luma: list[float] = []
    n = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (320, 180))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        luma.append(float(gray.mean()) / 255.0)
        lv = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        lap_var.append(lv)
        lap_ratio.append(lv / (float(gray.var()) + 1e-6))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        if prev_gray is not None:
            mean_abs_diff.append(float(cv2.absdiff(gray, prev_gray).mean()))
            hist_corr.append(
                float(cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL))
            )
        prev_gray, prev_hist = gray, hist
        n += 1
    cap.release()
    if n < 2:
        raise RuntimeError("video has fewer than 2 readable frames")

    hist_corr_a = np.array(hist_corr)
    diff_a = np.array(mean_abs_diff)
    lap_a = np.array(lap_var)
    ratio_a = np.array(lap_ratio)
    luma_a = np.array(luma)

    def span_dict(check, a, b, severity, detail):
        return {
            "check": check,
            "start_frame": int(a),
            "end_frame": int(b),
            "start_s": round(a / fps, 3),
            "end_s": round(b / fps, 3),
            "severity": severity,
            "detail": detail,
        }

    findings: list[dict] = []

    # 1) Shot boundaries: single-frame findings at each cut.
    cut_idx = np.where(hist_corr_a < SHOT_HIST_CORR_MIN)[0]
    for i in cut_idx:
        findings.append(
            span_dict("shot_boundary", i + 1, i + 1, "info",
                      f"hist_corr={hist_corr_a[i]:.3f}")
        )

    # 2) Frozen frames: runs of near-zero motion (excluding exact cuts).
    frozen_flags = diff_a < FROZEN_MEAN_ABS_DIFF
    for a, b in _spans_from_flags(frozen_flags, FROZEN_MIN_RUN):
        findings.append(
            span_dict("frozen_frames", a, b + 1, "fail",
                      f"mean_abs_diff<={FROZEN_MEAN_ABS_DIFF} for {b - a + 1} frames")
        )

    # 3) Blur / softness: low Laplacian variance AND a low
    #    contrast-normalized ratio. The ratio requirement is what keeps
    #    dark-but-sharp scenes from being convicted (they failed this
    #    check on absolute variance alone in the first eval run).
    blur_flags = (lap_a < BLUR_LAPLACIAN_VAR_MIN) & (ratio_a < BLUR_RATIO_MIN)
    for a, b in _spans_from_flags(blur_flags, max(3, int(fps * 0.25))):
        seg = lap_a[a : b + 1]
        findings.append(
            span_dict("blur", a, b, "warn",
                      f"laplacian_var min={seg.min():.1f} median={np.median(seg):.1f} "
                      f"ratio median={np.median(ratio_a[a : b + 1]):.4f}")
        )

    # 4) Flash screen (rough WCAG three-flash screen, NOT a certification):
    #    count large luminance swings; >3 flashes in any 1s window = fail.
    swings = np.abs(np.diff(luma_a)) > FLASH_DELTA_LUMA
    win = max(1, int(round(fps)))
    counts = np.convolve(swings.astype(int), np.ones(win, dtype=int), mode="same")
    hot = counts > FLASH_MAX_PER_SECOND
    for a, b in _spans_from_flags(hot, 1):
        findings.append(
            span_dict("flash_screen", a, b + 1, "fail",
                      f"up to {int(counts[a:b + 1].max())} flashes in a 1s window "
                      f"(screen threshold {FLASH_MAX_PER_SECOND})")
        )

    # 5) Temporal flicker inside shots: high-frequency luminance jitter.
    if n >= 8:
        detrended = luma_a - np.convolve(luma_a, np.ones(5) / 5, mode="same")
        jitter = float(np.std(detrended[2:-2])) if n > 8 else 0.0
    else:
        jitter = 0.0
    flash_covers_all = any(
        f["check"] == "flash_screen" and f["end_frame"] - f["start_frame"] >= n - 2
        for f in findings
    )
    if jitter > FLICKER_JITTER_MIN and not flash_covers_all:
        findings.append(
            span_dict("flicker", 0, n - 1, "warn",
                      f"luminance jitter {jitter:.4f} above {FLICKER_JITTER_MIN}")
        )

    cuts = sorted(int(i) for i in cut_idx)
    return {
        "path": path,
        "frames": n,
        "fps": round(float(fps), 3),
        "duration_s": round(n / fps, 3),
        "shots": len(cuts) + 1,
        "cut_frames": cuts,
        "luminance_jitter": round(jitter, 5),
        "findings": findings,
        "verdict": "FAIL" if any(f["severity"] == "fail" for f in findings)
        else ("WARN" if any(f["severity"] == "warn" for f in findings) else "PASS"),
    }
