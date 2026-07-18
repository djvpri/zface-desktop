import os
import sys

# Set model InsightFace ke folder portable (next to exe), bukan ~/.insightface
# Harus dilakukan SEBELUM import insightface apapun
if getattr(sys, 'frozen', False):
    _base = os.path.dirname(sys.executable)
    # PyInstaller windowed mode: stdout/stderr = None, redirect ke log file
    # agar library yang print ke stdout (insightface, onnxruntime) tidak crash
    _log_path = os.path.join(_base, 'zface.log')
    _log_file = open(_log_path, 'a', encoding='utf-8', errors='replace')
    sys.stdout = _log_file
    sys.stderr = _log_file
else:
    _base = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault('INSIGHTFACE_HOME', os.path.join(_base, 'models'))

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def apply_dark_theme(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.ColorRole.Window, QColor(17, 24, 39))
    p.setColor(QPalette.ColorRole.WindowText, QColor(229, 231, 235))
    p.setColor(QPalette.ColorRole.Base, QColor(31, 41, 55))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(17, 24, 39))
    p.setColor(QPalette.ColorRole.Text, QColor(229, 231, 235))
    p.setColor(QPalette.ColorRole.Button, QColor(31, 41, 55))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(229, 231, 235))
    p.setColor(QPalette.ColorRole.Highlight, QColor(59, 130, 246))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Link, QColor(96, 165, 250))
    app.setPalette(p)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ZFace Desktop")
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
