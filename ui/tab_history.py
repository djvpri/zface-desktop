from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class FetchLogsThread(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, api, limit=100):
        super().__init__()
        self.api = api
        self.limit = limit

    def run(self):
        try:
            self.done.emit(self.api.get_logs(self.limit))
        except Exception as e:
            self.error.emit(str(e))


class TabHistory(QWidget):
    def __init__(self, get_api):
        super().__init__()
        self.get_api = get_api
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Riwayat Deteksi")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color:#e5e7eb;")
        header.addWidget(title)
        header.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet(
            "QPushButton{background:#374151;color:#e5e7eb;border:none;"
            "border-radius:6px;padding:0 16px;font-size:13px;}"
            "QPushButton:hover{background:#4b5563;}"
        )
        refresh_btn.clicked.connect(self._load)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nama", "Similarity", "Sumber", "Waktu"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            "QTableWidget{background:#1f2937;border:none;border-radius:8px;"
            "color:#e5e7eb;gridline-color:#374151;font-size:13px;}"
            "QTableWidget::item{padding:8px 12px;}"
            "QTableWidget::item:alternate{background:#111827;}"
            "QTableWidget::item:selected{background:#3b82f6;}"
            "QHeaderView::section{background:#111827;color:#9ca3af;"
            "padding:8px 12px;border:none;font-size:12px;}"
        )
        layout.addWidget(self.table)

        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color:#6b7280;font-size:12px;")
        layout.addWidget(self.status_lbl)

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def _load(self):
        api = self.get_api()
        if not api:
            return
        self.status_lbl.setText("Memuat...")
        self._thread = FetchLogsThread(api)
        self._thread.done.connect(self._populate)
        self._thread.error.connect(lambda e: self.status_lbl.setText(f"Error: {e}"))
        self._thread.start()

    def _populate(self, logs: list):
        self.table.setRowCount(len(logs))
        for i, log in enumerate(logs):
            name = log.get("name", "-")
            sim = float(log.get("similarity", 0))
            source = log.get("source", "-")
            ts = str(log.get("created_at", log.get("timestamp", "-")))[:19]

            self.table.setItem(i, 0, QTableWidgetItem(name))

            sim_item = QTableWidgetItem(f"{sim:.0%}")
            sim_item.setForeground(
                QColor("#34d399") if sim >= 0.7 else
                QColor("#fbbf24") if sim >= 0.5 else
                QColor("#ef4444")
            )
            self.table.setItem(i, 1, sim_item)
            self.table.setItem(i, 2, QTableWidgetItem(source))
            self.table.setItem(i, 3, QTableWidgetItem(ts))

        self.status_lbl.setText(f"{len(logs)} entri ditampilkan")
