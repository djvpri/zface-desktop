"""Cek versi terbaru ZFace dari GitHub Releases di thread terpisah.

None-blocking; gagal (offline/404) diam tak ada signal.
"""
import json
import urllib.request

from PyQt6.QtCore import QThread, pyqtSignal

from app.version import REPO, VERSION, compare_versions


class UpdateThread(QThread):
    """Cek releases/latest; emit latest_version(st|None) saat selesai."""

    latest_version = pyqtSignal(object)  # str versi terbaru, atau None

    def __init__(self, timeout: int = 8):
        super().__init__()
        self.timeout = timeout

    def run(self):
        try:
            url = f"https://api.github.com/repos/{REPO}/releases/latest"
            req = urllib.request.Request(url, headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "zface-desktop-updater",
            })
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.load(resp)
            latest = data.get("tag_name", "")
            if latest and compare_versions(latest, VERSION) > 0:
                self.latest_version.emit(latest)
            else:
                self.latest_version.emit(None)
        except Exception:
            self.latest_version.emit(None)
