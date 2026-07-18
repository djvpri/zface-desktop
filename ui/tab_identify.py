from datetime import datetime

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QVBoxLayout, QWidget,
)

from app.face_engine import FaceEngine


class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._running = True
        while self._running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                self.msleep(30)
        cap.release()

    def stop(self):
        self._running = False
        self.wait(2000)


class TabIdentify(QWidget):
    def __init__(self, face_engine: FaceEngine, get_api, config: dict):
        super().__init__()
        self.face_engine = face_engine
        self.get_api = get_api
        self.config = config
        self._camera_thread = None
        self._frame_buffer = None
        self._last_faces = []
        self._last_labels = []
        self._model_ready = False
        self._identify_timer = QTimer()
        self._identify_timer.timeout.connect(self._run_identify)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        cam_panel = QFrame()
        cam_panel.setStyleSheet("background:#1f2937;border-radius:10px;")
        cl = QVBoxLayout(cam_panel)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(10)

        self.cam_label = QLabel("Kamera tidak aktif")
        self.cam_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cam_label.setMinimumSize(640, 460)
        self.cam_label.setStyleSheet("background:#111827;border-radius:8px;color:#6b7280;font-size:14px;")
        cl.addWidget(self.cam_label)

        btns = QHBoxLayout()
        self.start_btn = QPushButton("Mulai Kamera")
        self.start_btn.setFixedHeight(38)
        self.start_btn.setStyleSheet(self._btn("#3b82f6"))
        self.start_btn.clicked.connect(self._toggle_camera)
        btns.addWidget(self.start_btn)

        self.detect_btn = QPushButton("Auto Deteksi: ON")
        self.detect_btn.setCheckable(True)
        self.detect_btn.setChecked(True)
        self.detect_btn.setFixedHeight(38)
        self.detect_btn.setStyleSheet(self._btn("#059669"))
        self.detect_btn.toggled.connect(self._toggle_detect)
        btns.addWidget(self.detect_btn)
        cl.addLayout(btns)
        layout.addWidget(cam_panel, 3)

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

    def _toggle_camera(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self._identify_timer.stop()
            self._camera_thread.stop()
            self._camera_thread = None
            self.start_btn.setText("Mulai Kamera")
            self.start_btn.setStyleSheet(self._btn("#3b82f6"))
            self.cam_label.clear()
            self.cam_label.setText("Kamera tidak aktif")
        else:
            idx = self.config.get("camera_index", 0)
            self._camera_thread = CameraThread(idx)
            self._camera_thread.frame_ready.connect(self._on_frame)
            self._camera_thread.start()
            self.start_btn.setText("Stop Kamera")
            self.start_btn.setStyleSheet(self._btn("#ef4444"))
            if self.detect_btn.isChecked():
                self._identify_timer.start(self.config.get("detect_interval_ms", 1000))

    def _toggle_detect(self, checked: bool):
        if checked:
            self.detect_btn.setText("Auto Deteksi: ON")
            self.detect_btn.setStyleSheet(self._btn("#059669"))
            if self._camera_thread and self._camera_thread.isRunning():
                self._identify_timer.start(self.config.get("detect_interval_ms", 1000))
        else:
            self.detect_btn.setText("Auto Deteksi: OFF")
            self.detect_btn.setStyleSheet(self._btn("#374151"))
            self._identify_timer.stop()
            self._last_faces = []
            self._last_labels = []

    def _on_frame(self, frame: np.ndarray):
        self._frame_buffer = frame
        display = (
            self.face_engine.draw_faces(frame, self._last_faces, self._last_labels)
            if self._last_faces else frame
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

    def _run_identify(self):
        if not self._model_ready or self._frame_buffer is None:
            return
        api = self.get_api()
        if not api:
            return
        frame = self._frame_buffer.copy()
        faces = self.face_engine.detect(frame)
        if not faces:
            self._last_faces = []
            self._last_labels = []
            return
        threshold = self.config.get("threshold", 0.40)
        labels = []
        for face in faces:
            try:
                matches = api.identify_by_embedding(face.embedding, threshold)
                if matches:
                    top = matches[0]
                    name = top.get("name", "Unknown")
                    sim = float(top.get("similarity", 0))
                    labels.append(f"{name} ({sim:.0%})")
                    self._add_result(name, sim)
                    if self.config.get("auto_log", True):
                        try:
                            api.add_log(name, sim)
                        except Exception:
                            pass
                else:
                    labels.append("Unknown")
            except Exception:
                labels.append("Error")
        self._last_faces = faces
        self._last_labels = labels

    def _add_result(self, name: str, sim: float):
        item = QListWidgetItem(f"{name}\n{sim:.0%}  -  {datetime.now().strftime('%H:%M:%S')}")
        item.setForeground(QColor("#34d399") if sim >= 0.7 else QColor("#fbbf24"))
        self.result_list.insertItem(0, item)
        while self.result_list.count() > 50:
            self.result_list.takeItem(self.result_list.count() - 1)

    def stop_camera(self):
        self._identify_timer.stop()
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None

    def _btn(self, color: str) -> str:
        return (
            f"QPushButton{{background:{color};color:white;border:none;"
            "border-radius:6px;font-size:13px;font-weight:500;}}"
        )
