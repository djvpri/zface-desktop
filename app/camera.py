"""Utilitas membuka kamera dengan backend tercepat per-OS.

Di Windows, backend default OpenCV adalah MSMF (Microsoft Media Foundation)
yang SANGAT lambat dibuka (bisa 2-5 detik). DirectShow (CAP_DSHOW) jauh lebih
cepat, jadi kita paksa DSHOW di Windows dengan fallback ke default bila gagal.
"""
import sys

import cv2


def open_capture(index: int) -> cv2.VideoCapture:
    """Buka kamera pada index tertentu, pakai backend paling responsif.

    Return objek VideoCapture (belum tentu isOpened(); pemanggil wajib cek).
    """
    if sys.platform.startswith("win"):
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if cap is not None and cap.isOpened():
            return cap
        if cap is not None:
            cap.release()
        # Fallback: backend default (MSMF) kalau DSHOW gagal.
        return cv2.VideoCapture(index)
    # macOS/Linux: backend default sudah cepat.
    return cv2.VideoCapture(index)
