"""Utilitas membuka kamera dengan backend tercepat per-OS.

Di Windows, backend OpenCV untuk video capture:
  - DSHOW (CAP_DSHOW, DirectShow): umumnya paling cepat utk kamera USB UVC.
  - MSMF (CAP_MSMF, Media Foundation): native terkini, bisa lebih cepat utk
    webcam internal / hardware-accelerated pada sebagian device.
  - default (CAP_ANY): OpenCV auto-pilih (sering MSMF), kadang lambat.

Kita default ke DSHOW (terbukti cepat) dan izinkan pemilihan manual via
`backend` utk A/B test antar device (`dshow` / `msmf`).
"""
import sys

import cv2

_MSMF = getattr(cv2, "CAP_MSMF", None)  # guard versi OpenCV tanpa MSMF


def _flag_for(backend: str):
    backend = (backend or "dshow").lower()
    if backend == "msmf" and _MSMF is not None:
        return _MSMF
    return cv2.CAP_DSHOW


def open_capture(index: int, backend: str = "dshow") -> cv2.VideoCapture:
    """Buka kamera pada index tertentu, pakai backend yang diminta.

    Jika backend gagal, jatuh kembali ke default OpenCV (CAP_ANY).
    Return objek VideoCapture (belum tentu isOpened(); pemanggil wajib cek).
    """
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, _flag_for(backend))
        if cap is not None and cap.isOpened():
            return cap
        if cap is not None:
            cap.release()
        # Fallback: backend default (CAP_ANY) kalau backend spesifik gagal.
        return cv2.VideoCapture(index)
    # macOS/Linux: backend default sudah cepat.
    return cv2.VideoCapture(index)
