from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QStatusBar, QTabWidget, QVBoxLayout, QWidget,
)

from app.api import ZFaceAPI
from app.config import clear_token, get_token, load_config, save_config, set_token
from app.face_engine import FaceEngine
from ui.tab_history import TabHistory
from ui.tab_identify import TabIdentify
from ui.tab_register import TabRegister
from ui.tab_settings import TabSettings


class LoadingOverlay(QWidget):
    """Overlay transparan dengan progress bar indeterminate, tampil saat model loading."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background:rgba(10,14,23,210);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        icon = QLabel("🔍")
        icon.setFont(QFont("Segoe UI", 36))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)

        title = QLabel("ZFace Desktop")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color:#60a5fa;")
        layout.addWidget(title)

        self.status_lbl = QLabel("Memuat model InsightFace...")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet("color:#9ca3af;font-size:13px;")
        layout.addWidget(self.status_lbl)

        self.bar = QProgressBar()
        self.bar.setFixedSize(320, 10)
        self.bar.setRange(0, 0)  # indeterminate
        self.bar.setTextVisible(False)
        self.bar.setStyleSheet(
            "QProgressBar{background:#1f2937;border-radius:5px;border:none;}"
            "QProgressBar::chunk{background:#3b82f6;border-radius:5px;}"
        )
        layout.addWidget(self.bar, alignment=Qt.AlignmentFlag.AlignCenter)

        note = QLabel("Pertama kali: unduh model ~280MB, mohon tunggu...")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet("color:#4b5563;font-size:11px;")
        layout.addWidget(note)

    def set_status(self, text: str):
        self.status_lbl.setText(text)

    def resizeEvent(self, event):
        self.setGeometry(self.parent().rect())
        super().resizeEvent(event)


class ModelLoadThread(QThread):
    status = pyqtSignal(str)
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, engine: FaceEngine):
        super().__init__()
        self.engine = engine

    def run(self):
        try:
            self.engine.load(progress_callback=self.status.emit)
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


class SSOThread(QThread):
    done = pyqtSignal(str)

    def __init__(self, zone_url, server_url):
        super().__init__()
        self.zone_url = zone_url
        self.server_url = server_url

    def run(self):
        from app.auth import start_sso_flow
        token = start_sso_flow(self.zone_url, self.server_url) or ""
        self.done.emit(token)


class LoginDialog(QDialog):
    def __init__(self, zone_url: str, server_url: str, parent=None):
        super().__init__(parent)
        self.zone_url = zone_url
        self.server_url = server_url
        self.token_result = None
        self.setWindowTitle("ZFace Desktop — Login")
        self.setFixedSize(420, 300)
        self.setStyleSheet("QDialog{background:#111827;}")
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)

        logo = QLabel("ZFace Desktop")
        logo.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet("color:#60a5fa;")
        layout.addWidget(logo)

        sub = QLabel("Login menggunakan akun Zomet")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet("color:#9ca3af;font-size:13px;")
        layout.addWidget(sub)

        layout.addSpacing(4)

        sso_btn = QPushButton("Login via ZOne SSO")
        sso_btn.setFixedHeight(44)
        sso_btn.setStyleSheet(
            "QPushButton{background:#3b82f6;color:white;border:none;"
            "border-radius:8px;font-size:14px;font-weight:600;}"
            "QPushButton:hover{background:#2563eb;}"
        )
        sso_btn.clicked.connect(self._sso)
        layout.addWidget(sso_btn)

        sep = QLabel("atau masukkan token manual")
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sep.setStyleSheet("color:#6b7280;font-size:11px;")
        layout.addWidget(sep)

        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Paste token dari ZOne...")
        self.token_input.setFixedHeight(38)
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setStyleSheet(
            "QLineEdit{background:#1f2937;color:#e5e7eb;border:1px solid #374151;"
            "border-radius:6px;padding:0 12px;font-size:13px;}"
        )
        layout.addWidget(self.token_input)

        manual_btn = QPushButton("Konfirmasi Token")
        manual_btn.setFixedHeight(38)
        manual_btn.setStyleSheet(
            "QPushButton{background:#374151;color:#e5e7eb;border:1px solid #4b5563;"
            "border-radius:6px;font-size:13px;}"
            "QPushButton:hover{background:#4b5563;}"
        )
        manual_btn.clicked.connect(self._manual)
        layout.addWidget(manual_btn)

    def _sso(self):
        from PyQt6.QtWidgets import QProgressDialog
        prog = QProgressDialog("Menunggu login di browser...", "Batal", 0, 0, self)
        prog.setWindowModality(Qt.WindowModality.WindowModal)
        prog.setStyleSheet("QProgressDialog{background:#1f2937;color:#e5e7eb;}")
        prog.show()
        self._sso_thread = SSOThread(self.zone_url, self.server_url)
        self._sso_thread.done.connect(lambda t: self._on_sso(t, prog))
        self._sso_thread.start()

    def _on_sso(self, token: str, prog):
        prog.close()
        if token:
            self.token_result = token
            self.accept()
        else:
            QMessageBox.warning(self, "Login Gagal",
                "Tidak menerima token dari ZOne.\nCoba lagi atau gunakan token manual.")

    def _manual(self):
        t = self.token_input.text().strip()
        if not t:
            QMessageBox.warning(self, "Token Kosong", "Masukkan token terlebih dahulu.")
            return
        self.token_result = t
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.api: ZFaceAPI | None = None
        self.face_engine = FaceEngine()
        self.setWindowTitle("ZFace Desktop")
        self.setMinimumSize(1024, 700)
        self.setStyleSheet("QMainWindow{background:#111827;}")
        self._build_ui()
        self._check_auth()

    def _build_ui(self):
        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background:#0f172a;border-bottom:1px solid #1f2937;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("ZFace Desktop")
        logo.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        logo.setStyleSheet("color:#60a5fa;")
        hl.addWidget(logo)
        hl.addStretch()

        self.model_lbl = QLabel("Memuat model...")
        self.model_lbl.setStyleSheet("color:#9ca3af;font-size:12px;")
        hl.addWidget(self.model_lbl)

        self.logout_btn = QPushButton("Keluar")
        self.logout_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#ef4444;border:1px solid #ef4444;"
            "border-radius:5px;padding:4px 12px;font-size:12px;margin-left:16px;}"
            "QPushButton:hover{background:#ef444422;}"
        )
        self.logout_btn.clicked.connect(self._logout)
        self.logout_btn.hide()
        hl.addWidget(self.logout_btn)

        # Tabs
        self.tab_identify = TabIdentify(
            self.face_engine, lambda: self.api, self.config,
            on_config_change=self._on_camera_state_saved,
        )
        self.tab_register = TabRegister(self.face_engine, lambda: self.api, self.config)
        self.tab_history = TabHistory(lambda: self.api)
        self.tab_settings = TabSettings(self.config, self._on_settings_saved)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid #1f2937;border-radius:8px;background:#111827;}"
            "QTabBar::tab{background:#1f2937;color:#9ca3af;padding:10px 24px;"
            "border-radius:6px 6px 0 0;font-size:13px;font-weight:500;}"
            "QTabBar::tab:selected{background:#374151;color:#f9fafb;}"
            "QTabBar::tab:hover{background:#2d3748;color:#e5e7eb;}"
        )
        tabs.addTab(self.tab_identify, "  Identifikasi  ")
        tabs.addTab(self.tab_register, "  Daftarkan Wajah  ")
        tabs.addTab(self.tab_history, "  Riwayat  ")
        tabs.addTab(self.tab_settings, "  Setting  ")

        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(header)
        cl.addWidget(tabs)
        self.setCentralWidget(central)

        self.statusBar().setStyleSheet("QStatusBar{background:#0f172a;color:#6b7280;font-size:12px;}")
        self.statusBar().showMessage("Siap")

        # Loading overlay (hidden by default, shown saat model loading)
        self._overlay = LoadingOverlay(central)
        self._overlay.setGeometry(central.rect())
        self._overlay.hide()

    def _check_auth(self):
        token = get_token()
        if token:
            self._init_session(token)
        else:
            self._show_login()

    def _show_login(self):
        dlg = LoginDialog(self.config["zone_url"], self.config["server_url"], self)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.token_result:
            set_token(dlg.token_result)
            self._init_session(dlg.token_result)
        else:
            self.close()

    def _init_session(self, token: str):
        self.api = ZFaceAPI(self.config["server_url"], token)
        self.logout_btn.show()
        self._overlay.setGeometry(self.centralWidget().rect())
        self._overlay.show()
        self._overlay.raise_()
        self._loader = ModelLoadThread(self.face_engine)
        self._loader.status.connect(self._overlay.set_status)
        self._loader.status.connect(lambda m: self.model_lbl.setText(m))
        self._loader.done.connect(self._on_model_ready)
        self._loader.error.connect(self._on_model_error)
        self._loader.start()

    def _on_model_error(self, err: str):
        self._overlay.set_status(f"Gagal: {err}")
        self._overlay.bar.setRange(0, 1)  # stop animasi
        self._overlay.bar.setValue(0)
        self.model_lbl.setText(f"Error: {err}")

    def _on_model_ready(self):
        self._overlay.hide()
        self.model_lbl.setText("Model siap")
        self.model_lbl.setStyleSheet("color:#34d399;font-size:12px;")
        self.tab_identify.on_model_ready()
        self.tab_register.on_model_ready()

    def _logout(self):
        clear_token()
        self.api = None
        self.tab_identify.stop_camera()
        self.logout_btn.hide()
        self._show_login()

    def _on_camera_state_saved(self, new_cfg: dict):
        self.config.update(new_cfg)
        save_config(self.config)

    def _on_settings_saved(self, new_cfg: dict):
        self.config.update(new_cfg)
        save_config(self.config)
        if self.api:
            self.api.server_url = self.config["server_url"]

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_overlay'):
            self._overlay.setGeometry(self.centralWidget().rect())

    def closeEvent(self, event):
        self.tab_identify.stop_camera()
        event.accept()
