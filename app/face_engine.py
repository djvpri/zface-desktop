from dataclasses import dataclass
from typing import List

import cv2
import numpy as np


@dataclass
class DetectedFace:
    bbox: tuple  # (x1, y1, x2, y2)
    embedding: List[float]
    det_score: float


class FaceEngine:
    def __init__(self):
        self._model = None
        self.ready = False

    def load(self, progress_callback=None):
        if progress_callback:
            progress_callback("Memuat model InsightFace buffalo_l...")
        import os
        from insightface.app import FaceAnalysis
        # Ambil root dari env var yang di-set main.py (portable path next to exe)
        model_root = os.environ.get('INSIGHTFACE_HOME', os.path.expanduser('~/.insightface'))
        self._model = FaceAnalysis(name="buffalo_l", root=model_root, providers=["CPUExecutionProvider"])
        self._model.prepare(ctx_id=0, det_size=(640, 640))
        self.ready = True
        if progress_callback:
            progress_callback("Model siap.")

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        if not self.ready or self._model is None:
            return []
        if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
            return []
        try:
            results = []
            for f in self._model.get(frame):
                if f.embedding is None or f.bbox is None:
                    continue
                results.append(DetectedFace(
                    bbox=tuple(f.bbox.astype(int)),
                    embedding=f.embedding.tolist(),
                    det_score=float(f.det_score),
                ))
            return results
        except Exception:
            return []

    def draw_faces(
        self,
        frame: np.ndarray,
        faces: List[DetectedFace],
        labels: List[str] = None,
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]
        for i, face in enumerate(faces):
            x1, y1, x2, y2 = face.bbox
            label = labels[i] if labels and i < len(labels) else "?"
            color = (59, 130, 246) if label not in ("Unknown", "?", "Error") else (107, 114, 128)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            tw_x1 = min(x1, max(w - tw - 10, 0))   # jaga label tetap dalam frame horizontal
            # Label box di atas kotak; kalau tak muat (kotak dekat tepi atas) -> taruh di bawah.
            if y1 >= th + 14:
                by0, by1 = y1 - th - 10, y1
            else:
                by0, by1 = y2 + 4, y2 + th + 14
            by1 = min(by1, h)  # jangan melebihi batas bawah frame
            cv2.rectangle(out, (tw_x1, by0), (tw_x1 + tw + 8, by1), color, -1)
            cv2.putText(out, label, (tw_x1 + 4, by1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return out
