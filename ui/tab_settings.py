from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSlider, QVBoxLayout, QWidget,
)


class TabSettings(QWidget):
    def __init__(self, config: dict, on_save):
        super().__init__()
        self.config = config.copy()
        self.on_save = on_save
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(0)

        title = QLabel("Pengaturan")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("color:#e5e7eb;margin-bottom:20px;")
        layout.addWidget(title)

        card = QFrame()
        card.setStyleSheet("background:#1f2937;border-radius:10px;")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(24, 20, 24, 20)
        cl.setSpacing(18)

        # Koneksi
        cl.addWidget(self._sec("Koneksi"))

        url_row = QHBoxLayout()
        url_lbl = QLabel("Server URL:")
        url_lbl.setFixedWidth(150)
        url_lbl.setStyleSheet("color:#9ca3af;")
        url_row.addWidget(url_lbl)
        self.url_input = QLineEdit(self.config.get("server_url", ""))
        self.url_input.setFixedHeight(36)
        self.url_input.setStyleSheet(self._input())
        url_row.addWidget(self.url_input)
        cl.addLayout(url_row)

        zone_row = QHBoxLayout()
        zone_lbl = QLabel("ZOne URL:")
        zone_lbl.setFixedWidth(150)
        zone_lbl.setStyleSheet("color:#9ca3af;")
        zone_row.addWidget(zone_lbl)
        self.zone_input = QLineEdit(self.config.get("zone_url", ""))
        self.zone_input.setFixedHeight(36)
        self.zone_input.setStyleSheet(self._input())
        zone_row.addWidget(self.zone_input)
        cl.addLayout(zone_row)

        cl.addWidget(self._sep())
        cl.addWidget(self._sec("Kamera"))

        cam_row = QHBoxLayout()
        cam_lbl = QLabel("Indeks Kamera:")
        cam_lbl.setFixedWidth(150)
        cam_lbl.setStyleSheet("color:#9ca3af;")
        cam_row.addWidget(cam_lbl)
        self.cam_combo = QComboBox()
        self.cam_combo.addItems(["Kamera 0 (default)", "Kamera 1", "Kamera 2", "Kamera 3"])
        self.cam_combo.setCurrentIndex(self.config.get("camera_index", 0))
        self.cam_combo.setFixedHeight(36)
        self.cam_combo.setFixedWidth(200)
        self.cam_combo.setStyleSheet(
            "QComboBox{background:#111827;color:#e5e7eb;border:1px solid #374151;"
            "border-radius:6px;padding:0 12px;}"
        )
        cam_row.addWidget(self.cam_combo)
        cam_row.addStretch()
        cl.addLayout(cam_row)

        cl.addWidget(self._sep())
        cl.addWidget(self._sec("Deteksi Wajah"))

        thr_row = QHBoxLayout()
        thr_lbl = QLabel("Threshold:")
        thr_lbl.setFixedWidth(150)
        thr_lbl.setStyleSheet("color:#9ca3af;")
        thr_row.addWidget(thr_lbl)

        self.thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_slider.setRange(20, 90)
        self.thresh_slider.setValue(int(self.config.get("threshold", 0.40) * 100))
        self.thresh_slider.setFixedWidth(200)
        self.thresh_slider.setStyleSheet(
            "QSlider::groove:horizontal{background:#374151;height:6px;border-radius:3px;}"
            "QSlider::handle:horizontal{background:#3b82f6;width:16px;height:16px;"
            "margin:-5px 0;border-radius:8px;}"
            "QSlider::sub-page:horizontal{background:#3b82f6;border-radius:3px;}"
        )
        thr_row.addWidget(self.thresh_slider)

        self.thresh_val = QLabel(f"{self.config.get('threshold', 0.40):.2f}")
        self.thresh_val.setFixedWidth(40)
        self.thresh_val.setStyleSheet("color:#60a5fa;font-weight:bold;")
        self.thresh_slider.valueChanged.connect(lambda v: self.thresh_val.setText(f"{v/100:.2f}"))
        thr_row.addWidget(self.thresh_val)
        thr_row.addStretch()
        cl.addLayout(thr_row)

        log_row = QHBoxLayout()
        log_lbl = QLabel("Auto-log deteksi:")
        log_lbl.setFixedWidth(150)
        log_lbl.setStyleSheet("color:#9ca3af;")
        log_row.addWidget(log_lbl)
        self.auto_log_cb = QCheckBox()
        self.auto_log_cb.setChecked(self.config.get("auto_log", True))
        log_row.addWidget(self.auto_log_cb)
        log_row.addStretch()
        cl.addLayout(log_row)

        layout.addWidget(card)
        layout.addSpacing(20)

        save_btn = QPushButton("Simpan Pengaturan")
        save_btn.setFixedHeight(42)
        save_btn.setFixedWidth(200)
        save_btn.setStyleSheet(
            "QPushButton{background:#3b82f6;color:white;border:none;"
            "border-radius:8px;font-size:14px;font-weight:600;}"
            "QPushButton:hover{background:#2563eb;}"
        )
        save_btn.clicked.connect(self._save)
        layout.addWidget(save_btn)
        layout.addStretch()

    def _save(self):
        new_cfg = {
            "server_url": self.url_input.text().strip(),
            "zone_url": self.zone_input.text().strip(),
            "camera_index": self.cam_combo.currentIndex(),
            "threshold": self.thresh_slider.value() / 100,
            "auto_log": self.auto_log_cb.isChecked(),
        }
        self.config.update(new_cfg)
        self.on_save(new_cfg)
        QMessageBox.information(self, "Tersimpan", "Pengaturan berhasil disimpan.")

    def _sec(self, text):
        lbl = QLabel(text.upper())
        lbl.setStyleSheet("color:#6b7280;font-size:11px;font-weight:bold;letter-spacing:1px;")
        return lbl

    def _sep(self):
        f = QFrame()
        f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("background:#374151;max-height:1px;")
        return f

    def _input(self):
        return (
            "QLineEdit{background:#111827;color:#e5e7eb;border:1px solid #374151;"
            "border-radius:6px;padding:0 12px;}"
            "QLineEdit:focus{border-color:#3b82f6;}"
        )
