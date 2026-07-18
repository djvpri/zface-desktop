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
        from insightface.app import FaceAnalysis
        self._model = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self._model.prepare(ctx_id=0, det_size=(640, 640))
        self.ready = True
        if progress_callback:
            progress_callback("Model siap.")

    def detect(self, frame: np.ndarray) -> List[DetectedFace]:
        if not self.ready or self._model is None:
            return []
        return [
            DetectedFace(
                bbox=tuple(f.bbox.astype(int)),
                embedding=f.embedding.tolist(),
                det_score=float(f.det_score),
            )
            for f in self._model.get(frame)
        ]

    def draw_faces(
        self,
        frame: np.ndarray,
        faces: List[DetectedFace],
        labels: List[str] = None,
    ) -> np.ndarray:
        out = frame.copy()
        for i, face in enumerate(faces):
            x1, y1, x2, y2 = face.bbox
            label = labels[i] if labels and i < len(labels) else "?"
            color = (59, 130, 246) if label not in ("Unknown", "?", "Error") else (107, 114, 128)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
            cv2.rectangle(out, (x1, y1 - th - 10), (x1 + tw + 8, y1), color, -1)
            cv2.putText(out, label, (x1 + 4, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        return out
