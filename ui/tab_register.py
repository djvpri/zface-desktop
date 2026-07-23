import os

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QImage, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from app.face_engine import FaceEngine
from ui.tab_identify import CameraThread


class RegisterThread(QThread):
    done = pyqtSignal(bool, str)

    def __init__(self, api, name, image_bytes, filename, embedding=None):
        super().__init__()
        self.api = api
        self.name = name
        self.image_bytes = image_bytes
        self.filename = filename
        self.embedding = embedding

    def run(self):
        try:
            if self.embedding:
                self.api.register_by_embedding(self.name, self.embedding)
            else:
                self.api.register_by_file(self.name, self.image_bytes, self.filename)
            self.done.emit(True, f"Wajah '{self.name}' berhasil didaftarkan.")
        except Exception as e:
            self.done.emit(False, str(e))


class TabRegister(QWidget):
    def __init__(self, face_engine: FaceEngine, get_api, config: dict):
        super().__init__()
        self.face_engine = face_engine
        self.get_api = get_api
        self.config = config
        self._model_ready = False
        self._camera_thread = None
        self._current_frame = None
        self._captured_bytes = None
        self._captured_embedding = None
        self._capture_filename = "photo.jpg"
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        left = QFrame()
        left.setStyleSheet("background:#1f2937;border-radius:10px;")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 12, 12)
        ll.setSpacing(10)

        self.preview = QLabel("Preview wajah")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(480, 360)
        self.preview.setStyleSheet("background:#111827;border-radius:8px;color:#6b7280;font-size:14px;")
        ll.addWidget(self.preview)

        btns = QHBoxLayout()
        self.cam_btn = QPushButton("Aktifkan Kamera")
        self.cam_btn.setFixedHeight(38)
        self.cam_btn.setStyleSheet(self._btn("#3b82f6"))
        self.cam_btn.clicked.connect(self._toggle_camera)
        btns.addWidget(self.cam_btn)

        snap_btn = QPushButton("Ambil Foto")
        snap_btn.setFixedHeight(38)
        snap_btn.setStyleSheet(self._btn("#059669"))
        snap_btn.clicked.connect(self._capture)
        btns.addWidget(snap_btn)

        upload_btn = QPushButton("Upload File")
        upload_btn.setFixedHeight(38)
        upload_btn.setStyleSheet(self._btn("#7c3aed"))
        upload_btn.clicked.connect(self._upload_file)
        btns.addWidget(upload_btn)
        ll.addLayout(btns)
        layout.addWidget(left, 3)

        right = QFrame()
        right.setFixedWidth(300)
        right.setStyleSheet("background:#1f2937;border-radius:10px;")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(20, 20, 20, 20)
        rl.setSpacing(12)

        title = QLabel("Daftarkan Wajah")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color:#e5e7eb;")
        rl.addWidget(title)

        lbl = QLabel("Nama Lengkap")
        lbl.setStyleSheet("color:#9ca3af;font-size:12px;")
        rl.addWidget(lbl)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Masukkan nama...")
        self.name_input.setFixedHeight(40)
        self.name_input.setStyleSheet(
            "QLineEdit{background:#111827;color:#e5e7eb;border:1px solid #374151;"
            "border-radius:6px;padding:0 12px;font-size:14px;}"
            "QLineEdit:focus{border-color:#3b82f6;}"
        )
        rl.addWidget(self.name_input)

        rl.addSpacing(8)
        self.status_label = QLabel("Belum ada foto dipilih")
        self.status_label.setStyleSheet("color:#6b7280;font-size:12px;")
        self.status_label.setWordWrap(True)
        rl.addWidget(self.status_label)

        rl.addStretch()

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        rl.addWidget(self.progress)

        save_btn = QPushButton("Daftarkan")
        save_btn.setFixedHeight(44)
        save_btn.setStyleSheet(
            "QPushButton{background:#059669;color:white;border:none;"
            "border-radius:8px;font-size:14px;font-weight:600;}"
            "QPushButton:hover{background:#047857;}"
        )
        save_btn.clicked.connect(self._register)
        rl.addWidget(save_btn)
        layout.addWidget(right)

    def on_model_ready(self):
        self._model_ready = True

    def _toggle_camera(self):
        if self._camera_thread and self._camera_thread.isRunning():
            self.stop_camera()
        else:
            # Buka kamera di thread terpisah agar UI tidak freeze saat inisialisasi.
            idx = self.config.get("camera_index", 0)
            self._camera_thread = CameraThread(idx)
            self._camera_thread.frame_ready.connect(self._on_frame)
            self._camera_thread.error.connect(self._on_camera_error)
            self._camera_thread.start()
            self.cam_btn.setText("Stop Kamera")
            self.cam_btn.setStyleSheet(self._btn("#ef4444"))

    def stop_camera(self):
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None
        self.cam_btn.setText("Aktifkan Kamera")
        self.cam_btn.setStyleSheet(self._btn("#3b82f6"))
        self.preview.clear()
        self.preview.setText("Preview wajah")

    def _on_frame(self, frame: np.ndarray):
        self._current_frame = frame
        self._show_frame(frame)

    def _on_camera_error(self, msg: str):
        self._camera_thread = None
        self.cam_btn.setText("Aktifkan Kamera")
        self.cam_btn.setStyleSheet(self._btn("#3b82f6"))
        self.preview.setText(f"Error kamera: {msg}\n\nCoba ganti Indeks Kamera di tab Setting")
        QMessageBox.warning(self, "Error", f"Tidak bisa membuka kamera.\n{msg}")

    def _show_frame(self, frame: np.ndarray):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        self.preview.setPixmap(
            QPixmap.fromImage(qt_img).scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _capture(self):
        if self._current_frame is None:
            QMessageBox.warning(self, "Tidak Ada Kamera", "Aktifkan kamera terlebih dahulu.")
            return
        frame = self._current_frame.copy()
        _, buf = cv2.imencode(".jpg", frame)
        self._captured_bytes = buf.tobytes()
        self._capture_filename = "photo.jpg"
        if self._model_ready:
            faces = self.face_engine.detect(frame)
            self._captured_embedding = faces[0].embedding if faces else None
            ok = len(faces) > 0
            self.status_label.setText(f"Foto diambil - {len(faces)} wajah terdeteksi")
            self.status_label.setStyleSheet("color:#34d399;" if ok else "color:#fbbf24;")
        else:
            self.status_label.setText("Foto diambil")
            self.status_label.setStyleSheet("color:#34d399;")

    def _upload_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Foto", "", "Gambar (*.jpg *.jpeg *.png *.webp)"
        )
        if not path:
            return
        with open(path, "rb") as f:
            self._captured_bytes = f.read()
        self._capture_filename = os.path.basename(path)
        frame = cv2.imread(path)
        if frame is not None:
            self._current_frame = frame
            self._show_frame(frame)
            if self._model_ready:
                faces = self.face_engine.detect(frame)
                self._captured_embedding = faces[0].embedding if faces else None
                ok = len(faces) > 0
                self.status_label.setText(f"File dipilih - {len(faces)} wajah terdeteksi")
                self.status_label.setStyleSheet("color:#34d399;" if ok else "color:#fbbf24;")
            else:
                self.status_label.setText("File dipilih")
                self.status_label.setStyleSheet("color:#34d399;")

    def _register(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Nama Kosong", "Masukkan nama terlebih dahulu.")
            return
        if not self._captured_bytes:
            QMessageBox.warning(self, "Tidak Ada Foto", "Ambil foto atau upload file terlebih dahulu.")
            return
        api = self.get_api()
        if not api:
            return
        self.progress.show()
        self._reg_thread = RegisterThread(
            api, name, self._captured_bytes, self._capture_filename, self._captured_embedding
        )
        self._reg_thread.done.connect(self._on_done)
        self._reg_thread.start()

    def _on_done(self, success: bool, msg: str):
        self.progress.hide()
        if success:
            QMessageBox.information(self, "Berhasil", msg)
            self.name_input.clear()
            self._captured_bytes = None
            self._captured_embedding = None
            self.status_label.setText("Belum ada foto dipilih")
            self.status_label.setStyleSheet("color:#6b7280;")
        else:
            QMessageBox.critical(self, "Gagal", f"Gagal mendaftarkan wajah:\n{msg}")

    def _btn(self, color: str) -> str:
        return (
            f"QPushButton{{background:{color};color:white;border:none;"
            "border-radius:6px;font-size:13px;font-weight:500;}}"
        )
