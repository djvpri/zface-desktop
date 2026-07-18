from datetime import datetime

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, QByteArray
from PyQt6.QtGui import QColor, QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from app.face_engine import FaceEngine


class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self._running = False

    def run(self):
        cap = None
        try:
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                self.error.emit(f"Kamera index {self.camera_index} tidak ditemukan")
                return
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._running = True
            fail_count = 0
            while self._running:
                ret, frame = cap.read()
                if ret:
                    fail_count = 0
                    self.frame_ready.emit(frame)
                    self.msleep(33)  # ~30fps max
                else:
                    fail_count += 1
                    if fail_count > 30:
                        self.error.emit("Kamera terputus")
                        break
                    self.msleep(50)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

    def stop(self):
        self._running = False
        if not self.wait(3000):
            self.terminate()


class IdentifyThread(QThread):
    """Jalankan deteksi + API call di background agar UI tidak freeze."""
    done = pyqtSignal(list, list)   # faces, labels
    error = pyqtSignal(str)

    def __init__(self, face_engine, api, frame, threshold, auto_log):
        super().__init__()
        self.face_engine = face_engine
        self.api = api
        self.frame = frame
        self.threshold = threshold
        self.auto_log = auto_log

    def run(self):
        try:
            faces = self.face_engine.detect(self.frame)
            if not faces:
                self.done.emit([], [])
                return
            labels = []
            for face in faces:
                try:
                    matches = self.api.identify_by_embedding(face.embedding, self.threshold)
                    if matches:
                        top = matches[0]
                        name = top.get("name", "Unknown")
                        sim = float(top.get("similarity", 0))
                        labels.append(f"{name} ({sim:.0%})")
                        if self.auto_log:
                            try:
                                self.api.add_log(name, sim)
                            except Exception:
                                pass
                    else:
                        labels.append("Unknown")
                except Exception:
                    labels.append("Error")
            self.done.emit(faces, labels)
        except Exception as e:
            self.error.emit(str(e))


class TabIdentify(QWidget):
    def __init__(self, face_engine: FaceEngine, get_api, config: dict, on_config_change=None):
        super().__init__()
        self.face_engine = face_engine
        self.get_api = get_api
        self.config = config
        self._on_config_change = on_config_change  # dipanggil saat state kamera berubah
        self._camera_thread = None
        self._identify_thread = None
        self._frame_buffer = None
        self._last_faces = []
        self._last_labels = []
        self._model_ready = False
        self._frozen = False        # True saat capture freeze aktif
        self._frozen_frame = None   # Frame yang di-freeze
        self._auto_timer = QTimer()
        self._auto_timer.timeout.connect(self._trigger_identify)
        self._resume_timer = QTimer()
        self._resume_timer.setSingleShot(True)
        self._resume_timer.timeout.connect(self._resume_live)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # --- Panel kamera (kiri) ---
        cam_panel = QFrame()
        cam_panel.setStyleSheet("background:#1f2937;border-radius:10px;")
        cl = QVBoxLayout(cam_panel)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(10)

        self.cam_label = QLabel("Kamera tidak aktif")
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_label.setMinimumSize(640, 420)
        self.cam_label.setStyleSheet(
            "background:#111827;border-radius:8px;color:#6b7280;font-size:14px;"
        )
        cl.addWidget(self.cam_label)

        # Baris 1: Mulai/Stop + Auto Deteksi
        row1 = QHBoxLayout()
        self.start_btn = QPushButton("Mulai Kamera")
        self.start_btn.setFixedHeight(40)
        self.start_btn.setStyleSheet(self._btn("#3b82f6"))
        self.start_btn.clicked.connect(self._toggle_camera)
        row1.addWidget(self.start_btn)

        self.detect_btn = QPushButton("Auto Deteksi: OFF")
        self.detect_btn.setCheckable(True)
        self.detect_btn.setChecked(False)   # default OFF
        self.detect_btn.setFixedHeight(40)
        self.detect_btn.setStyleSheet(self._btn("#374151"))
        self.detect_btn.toggled.connect(self._toggle_detect)
        row1.addWidget(self.detect_btn)
        cl.addLayout(row1)

        # Baris 2: Tombol Capture (full width, menonjol)
        self.capture_btn = QPushButton("Capture & Identifikasi")
        self.capture_btn.setFixedHeight(44)
        self.capture_btn.setEnabled(False)
        self.capture_btn.setStyleSheet(
            "QPushButton{background:#7c3aed;color:white;border:none;"
            "border-radius:8px;font-size:14px;font-weight:600;}"
            "QPushButton:hover{background:#6d28d9;}"
            "QPushButton:disabled{background:#374151;color:#6b7280;}"
        )
        self.capture_btn.clicked.connect(self._capture)
        cl.addWidget(self.capture_btn)

        self.capture_status = QLabel("")
        self.capture_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_status.setStyleSheet("color:#9ca3af;font-size:11px;")
        self.capture_status.setFixedHeight(18)
        cl.addWidget(self.capture_status)

        layout.addWidget(cam_panel, 3)

        # --- Panel hasil (kanan) ---
        right = QFrame()
        right.setFixedWidth(280)
        right.setStyleSheet("background:#1f2937;border-radius:10px;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(12, 12, 12, 12)
        rl.setSpacing(8)

        hdr = QLabel("Terdeteksi")
        hdr.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        hdr.setStyleSheet("color:#e5e7eb;")
        rl.addWidget(hdr)

        self.result_list = QListWidget()
        self.result_list.setStyleSheet(
            "QListWidget{background:#111827;border-radius:8px;border:none;}"
            "QListWidget::item{padding:10px 12px;border-bottom:1px solid #1f2937;color:#e5e7eb;}"
            "QListWidget::item:selected{background:#374151;}"
        )
        rl.addWidget(self.result_list)

        clear_btn = QPushButton("Bersihkan")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(self._btn("#374151"))
        clear_btn.clicked.connect(self.result_list.clear)
        rl.addWidget(clear_btn)
        layout.addWidget(right)

    def on_model_ready(self):
        self._model_ready = True
        # Restore state sesi sebelumnya
        if self.config.get("camera_active", False):
            self._start_camera()
        if self.config.get("auto_detect", False):
            self.detect_btn.setChecked(True)

    # ---- Kamera ----

    def _toggle_camera(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self._auto_timer.stop()
            self._camera_thread.stop()
            self._camera_thread = None
            self.start_btn.setText("Mulai Kamera")
            self.start_btn.setStyleSheet(self._btn("#3b82f6"))
            self.cam_label.clear()
            self.cam_label.setText("Kamera tidak aktif")
            self.capture_btn.setEnabled(False)
            self._save_state(camera_active=False)
        else:
            self._start_camera()

    def _start_camera(self):
        idx = self.config.get("camera_index", 0)
        self._camera_thread = CameraThread(idx)
        self._camera_thread.frame_ready.connect(self._on_frame)
        self._camera_thread.error.connect(self._on_camera_error)
        self._camera_thread.start()
        self.start_btn.setText("Stop Kamera")
        self.start_btn.setStyleSheet(self._btn("#ef4444"))
        self.capture_btn.setEnabled(True)
        if self.detect_btn.isChecked():
            self._auto_timer.start(self.config.get("detect_interval_ms", 1000))
        self._save_state(camera_active=True)

    def _on_camera_error(self, msg: str):
        self._auto_timer.stop()
        self._camera_thread = None
        self.start_btn.setText("Mulai Kamera")
        self.start_btn.setStyleSheet(self._btn("#3b82f6"))
        self.capture_btn.setEnabled(False)
        self.cam_label.setText(
            f"Error kamera: {msg}\n\nCoba ganti Camera Index di tab Setting"
        )

    def _toggle_detect(self, checked: bool):
        if checked:
            self.detect_btn.setText("Auto Deteksi: ON")
            self.detect_btn.setStyleSheet(self._btn("#059669"))
            if self._camera_thread and self._camera_thread.isRunning():
                self._auto_timer.start(self.config.get("detect_interval_ms", 1000))
        else:
            self.detect_btn.setText("Auto Deteksi: OFF")
            self.detect_btn.setStyleSheet(self._btn("#374151"))
            self._auto_timer.stop()
            self._last_faces = []
            self._last_labels = []
        self._save_state(auto_detect=checked)

    def _save_state(self, **kwargs):
        self.config.update(kwargs)
        if self._on_config_change:
            self._on_config_change(self.config)

    def _on_frame(self, frame: np.ndarray):
        self._frame_buffer = frame
        if self._frozen:
            return  # jangan update display saat freeze
        self._show_frame(frame, self._last_faces, self._last_labels)

    def _show_frame(self, frame, faces=None, labels=None):
        display = (
            self.face_engine.draw_faces(frame, faces, labels)
            if faces else frame
        )
        rgb = cv2.cvtColor(display, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.cam_label.setPixmap(
            QPixmap.fromImage(qt_img).scaled(
                self.cam_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _resume_live(self):
        self._frozen = False
        self._frozen_frame = None
        self._last_faces = []
        self._last_labels = []

    # ---- Identifikasi ----

    def _capture(self):
        """Ambil frame sekarang dan identifikasi secara manual."""
        if not self._model_ready:
            self.capture_status.setText("Model belum siap...")
            return
        if self._frame_buffer is None:
            self.capture_status.setText("Kamera belum aktif")
            return
        if self._identify_thread and self._identify_thread.isRunning():
            self.capture_status.setText("Sedang memproses, tunggu...")
            return
        api = self.get_api()
        if not api:
            self.capture_status.setText("Sesi tidak valid, login ulang")
            return
        self.capture_btn.setEnabled(False)
        self.capture_btn.setText("Memproses...")
        self.capture_status.setText("Mendeteksi wajah...")
        # Freeze kamera pada frame ini
        self._frozen = True
        self._frozen_frame = self._frame_buffer.copy()
        self._start_identify(self._frozen_frame, api)

    def _trigger_identify(self):
        """Dipanggil oleh auto-detect timer."""
        if not self._model_ready or self._frame_buffer is None:
            return
        if self._identify_thread and self._identify_thread.isRunning():
            return  # skip tick ini jika masih proses
        api = self.get_api()
        if not api:
            return
        self._start_identify(self._frame_buffer.copy(), api)

    def _start_identify(self, frame, api):
        threshold = self.config.get("threshold", 0.40)
        auto_log = self.config.get("auto_log", True)
        self._identify_thread = IdentifyThread(
            self.face_engine, api, frame, threshold, auto_log
        )
        self._identify_thread.done.connect(self._on_identify_done)
        self._identify_thread.error.connect(self._on_identify_error)
        self._identify_thread.start()

    def _on_identify_done(self, faces, labels):
        self._last_faces = faces
        self._last_labels = labels
        if not faces:
            self.capture_status.setText("Tidak ada wajah terdeteksi")
            self._reset_capture_btn()
            self._resume_timer.start(2000)  # resume live setelah 2 detik
            return
        self.capture_status.setText(f"{len(faces)} wajah terdeteksi")
        # Tampilkan hasil di frame yang di-freeze
        if self._frozen_frame is not None:
            self._show_frame(self._frozen_frame, faces, labels)
        self._resume_timer.start(3000)  # resume live setelah 3 detik
        for i, (face, label) in enumerate(zip(faces, labels)):
            # label format: "Nama (85%)" atau "Unknown" atau "Error"
            if label in ("Unknown", "?"):
                self._add_result_raw("Unknown", 0.0, known=False)
            elif label == "Error":
                self._add_result_raw("Error (server)", 0.0, known=False)
            else:
                # parse "Nama (85%)"
                try:
                    parts = label.rsplit("(", 1)
                    name = parts[0].strip()
                    sim = float(parts[1].rstrip("%)").strip()) / 100
                except Exception:
                    name, sim = label, 0.0
                self._add_result_raw(name, sim, known=True)
        self._reset_capture_btn()

    def _on_identify_error(self, err: str):
        self._last_faces = []
        self._last_labels = []
        self.capture_status.setText(f"Error: {err[:60]}")
        self._reset_capture_btn()
        self._resume_timer.start(2000)

    def _reset_capture_btn(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self.capture_btn.setEnabled(True)
        self.capture_btn.setText("Capture & Identifikasi")

    def _add_result_raw(self, name: str, sim: float, known: bool = True):
        ts = datetime.now().strftime("%H:%M:%S")
        text = f"{name}\n{sim:.0%}  —  {ts}" if known and sim > 0 else f"{name}\n{ts}"
        item = QListWidgetItem(text)
        if not known:
            item.setForeground(QColor("#6b7280"))
        elif sim >= 0.7:
            item.setForeground(QColor("#34d399"))
        else:
            item.setForeground(QColor("#fbbf24"))
        self.result_list.insertItem(0, item)
        while self.result_list.count() > 50:
            self.result_list.takeItem(self.result_list.count() - 1)

    def stop_camera(self):
        self._auto_timer.stop()
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None

    def _btn(self, color: str) -> str:
        return (
            f"QPushButton{{background:{color};color:white;border:none;"
            "border-radius:6px;font-size:13px;font-weight:500;}}"
            f"QPushButton:hover{{background:{color}dd;}}"
        )
