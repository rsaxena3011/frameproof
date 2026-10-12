"""FrameProof identity-drift check (YuNet detection + SFace embeddings).

Given a reference still of a character and a video, sample frames,
embed every detected face, and flag spans where the best-matching face
drifts below the identity threshold (the AI quietly changed the actor).
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

MODELS = Path(__file__).resolve().parent.parent / "models"
YUNET = MODELS / "face_detection_yunet_2023mar.onnx"
SFACE = MODELS / "face_recognition_sface_2021dec.onnx"

DRIFT_COSINE_MIN = 0.45  # initial threshold, to be calibrated on the eval set


def _detector(w: int, h: int) -> cv2.FaceDetectorYN:
    return cv2.FaceDetectorYN.create(str(YUNET), "", (w, h), 0.6, 0.3, 5000)


def _recognizer() -> cv2.FaceRecognizerSF:
    return cv2.FaceRecognizerSF.create(str(SFACE), "")


def embed_image(path: str) -> np.ndarray | None:
    """Embedding of the largest face in an image, or None if no face."""
    img = cv2.imread(path)
    if img is None:
        raise RuntimeError(f"cannot read image: {path}")
    h, w = img.shape[:2]
    det = _detector(w, h)
    _, faces = det.detect(img)
    if faces is None or len(faces) == 0:
        return None
    face = max(faces, key=lambda f: f[2] * f[3])
    rec = _recognizer()
    aligned = rec.alignCrop(img, face)
    return rec.feature(aligned).flatten()


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def drift_scan(video: str, reference: str, sample_every_s: float = 0.5) -> dict:
    """Sample a video and compare each detected face to the reference."""
    ref = embed_image(reference)
    if ref is None:
        raise RuntimeError(f"no face found in reference: {reference}")
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video: {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    step = max(1, int(round(fps * sample_every_s)))
    rec = _recognizer()
    samples, idx = [], 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            h, w = frame.shape[:2]
            det = _detector(w, h)
            _, faces = det.detect(frame)
            best = None
            if faces is not None and len(faces):
                for f in faces:
                    emb = rec.feature(rec.alignCrop(frame, f)).flatten()
                    s = cosine(ref, emb)
                    best = s if best is None else max(best, s)
            samples.append(
                {"t": round(idx / fps, 2), "similarity": None if best is None else round(best, 3)}
            )
        idx += 1
    cap.release()
    drift = [s for s in samples if s["similarity"] is not None and s["similarity"] < DRIFT_COSINE_MIN]
    missing = [s for s in samples if s["similarity"] is None]
    return {
        "video": video,
        "reference": reference,
        "samples": samples,
        "drift_samples": drift,
        "no_face_samples": missing,
        "verdict": "FAIL" if drift else ("WARN" if missing else "PASS"),
    }
