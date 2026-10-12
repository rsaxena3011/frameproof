"""FrameProof agent loop.

Stage 1  coarse pass (src.checks): fast deterministic scan at low res.
Stage 2  dense re-inspection: every FAIL/WARN span is re-measured at
         native resolution with a method suited to that check.
Stage 3  second opinion: the dense measurement must agree with the
         coarse one, otherwise the finding is downgraded and the clip
         is ESCALATED to a human instead of auto-judged.

Dispositions:
  PASS        nothing confirmed
  AUTO-FIX    only fixable issues confirmed (temporal flicker: deflicker)
  REGEN NOTE  generation defects confirmed (frozen, identity drift, blur)
  ESCALATE    safety issue confirmed (flash screen) or stages disagree

Every step is written to the trace so a judge can replay the reasoning.
"""

from __future__ import annotations

import time

import cv2
import numpy as np

from .checks import analyse
from .identity import drift_scan


def _span_frames(path: str, a: int, b: int):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, a)
    frames = []
    idx = a
    while idx <= b:
        ok, fr = cap.read()
        if not ok:
            break
        frames.append(fr)
        idx += 1
    cap.release()
    return frames


def _dense_recheck(path: str, finding: dict, fps: float) -> tuple[bool, str]:
    """Re-measure one coarse finding at native resolution."""
    a, b = finding["start_frame"], finding["end_frame"]
    frames = _span_frames(path, max(0, a - 1), b + 1)
    if len(frames) < 2:
        return False, "span unreadable at native res"
    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    check = finding["check"]
    if check == "frozen_frames":
        diffs = np.array([float(cv2.absdiff(grays[i], grays[i - 1]).mean())
                          for i in range(1, len(grays))])
        frac_still = float((diffs < 0.35).mean())
        # Median + still-fraction, not max: encoder keyframe refresh spikes
        # (measured up to 2.67 on a truly frozen clip) must not veto.
        return (float(np.median(diffs)) < 0.35 and frac_still >= 0.9,
                f"native median diff {np.median(diffs):.4f}, still fraction {frac_still:.2f}")
    if check == "flash_screen":
        luma = np.array([g.mean() / 255.0 for g in grays])
        swings = int((np.abs(np.diff(luma)) > 0.18).sum())
        per_s = swings / max(1e-9, (len(frames) / fps))
        return (per_s > 3 / max(1e-9, (len(frames) / fps)) * fps / fps and swings >= 3,
                f"native swings in span: {swings}")
    if check == "blur":
        vars_ = np.array([float(cv2.Laplacian(g, cv2.CV_64F).var()) for g in grays])
        ratios = np.array([v / (float(g.var()) + 1e-6) for v, g in zip(vars_, grays)])
        return (float(np.median(vars_)) < 90.0 and float(np.median(ratios)) < 0.008,
                f"native median laplacian var {np.median(vars_):.1f}, ratio {np.median(ratios):.4f}")
    if check == "flicker":
        luma = np.array([g.mean() / 255.0 for g in grays])
        detrended = luma - np.convolve(luma, np.ones(5) / 5, mode="same")
        j = float(np.std(detrended[2:-2])) if len(luma) > 8 else 0.0
        return (j > 0.012, f"native detrended jitter {j:.4f}")
    return True, "no dense method; coarse result stands"


def run_agent(path: str, reference: str | None = None) -> dict:
    trace: list[dict] = []

    def log(stage: str, msg: str, **kw):
        trace.append({"t": round(time.time(), 3), "stage": stage, "msg": msg, **kw})

    log("coarse", "starting coarse pass")
    report = analyse(path)
    fps = report["fps"]
    log("coarse", f"{report['frames']} frames, {report['shots']} shots, "
                  f"jitter={report['luminance_jitter']}", findings=len(report["findings"]))

    # Suppress shot-boundary findings inside flash spans (known artefact).
    flash_spans = [(f["start_frame"], f["end_frame"]) for f in report["findings"]
                   if f["check"] == "flash_screen"]
    findings = []
    for f in report["findings"]:
        if f["check"] == "shot_boundary" and any(a <= f["start_frame"] <= b for a, b in flash_spans):
            log("coarse", "suppressed boundary inside flash span", frame=f["start_frame"])
            continue
        findings.append(f)

    dispositions: list[dict] = []
    for f in findings:
        if f["severity"] == "info":
            dispositions.append({**f, "disposition": "noted"})
            continue
        confirmed, evidence = _dense_recheck(path, f, fps)
        log("dense", f"{f['check']} span {f['start_frame']}-{f['end_frame']}: {evidence}",
            confirmed=confirmed)
        if confirmed:
            dispositions.append({**f, "disposition": "confirmed", "dense_evidence": evidence})
        else:
            dispositions.append({**f, "disposition": "downgraded", "dense_evidence": evidence})
            log("second_opinion", f"{f['check']} downgraded by dense re-inspection")

    if reference:
        log("identity", f"drift scan against {reference}")
        drift = drift_scan(path, reference)
        for s in drift["drift_samples"]:
            dispositions.append({
                "check": "identity_drift", "severity": "fail",
                "start_frame": int(s["t"] * fps), "end_frame": int(s["t"] * fps),
                "start_s": s["t"], "end_s": s["t"],
                "detail": f"similarity {s['similarity']} below threshold",
                "disposition": "confirmed",
            })
        log("identity", f"drift samples: {len(drift['drift_samples'])}, verdict {drift['verdict']}")

    confirmed = [d for d in dispositions if d.get("disposition") == "confirmed"]
    downgraded = [d for d in dispositions if d.get("disposition") == "downgraded"]
    checks_hit = {d["check"] for d in confirmed if d["severity"] == "fail"}
    regen = bool(checks_hit & {"frozen_frames", "identity_drift"}) or any(
        d["check"] == "blur" for d in confirmed
    )
    if "flash_screen" in checks_hit or downgraded:
        verdict = "ESCALATE"
    elif regen:
        verdict = "REGEN NOTE"
    elif confirmed:
        verdict = "AUTO-FIX"
    else:
        verdict = "PASS"
    log("verdict", verdict)

    autofix = None
    if verdict == "AUTO-FIX" and any(d["check"] == "flicker" for d in confirmed):
        autofix = _apply_deflicker(path, report["luminance_jitter"], log)

    return {
        "path": path,
        "coarse_verdict": report["verdict"],
        "verdict": verdict,
        "shots": report["shots"],
        "dispositions": dispositions,
        "autofix": autofix,
        "trace": trace,
    }


def _apply_deflicker(path: str, jitter_before: float, log) -> dict:
    """AUTO-FIX execution: ffmpeg deflicker, then re-measure the jitter."""
    import subprocess
    from pathlib import Path

    src = Path(path)
    out = src.with_name(f"{src.stem}_deflickered.mp4")
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src),
           "-vf", "deflicker=size=5:mode=pm", "-c:a", "copy", str(out)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log("autofix", f"deflicker failed: {r.stderr.strip()[:200]}")
        return {"applied": False, "error": r.stderr.strip()[:200]}
    after = analyse(str(out))
    log("autofix", f"deflickered -> {out.name}; jitter {jitter_before} -> {after['luminance_jitter']}")
    return {
        "applied": True,
        "output": str(out),
        "jitter_before": jitter_before,
        "jitter_after": after["luminance_jitter"],
    }
