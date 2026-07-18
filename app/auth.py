import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests

CALLBACK_PORT = 7777

_callback_token: str | None = None
_callback_event = threading.Event()


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global _callback_token
        params = parse_qs(urlparse(self.path).query)
        if "token" in params:
            _callback_token = params["token"][0]
            _callback_event.set()
            body = (
                b"<html><body style='font-family:sans-serif;text-align:center;"
                b"padding:60px;background:#111827;color:#e5e7eb'>"
                b"<h2 style='color:#60a5fa'>Login Berhasil!</h2>"
                b"<p>Anda bisa tutup tab ini dan kembali ke ZFace Desktop.</p>"
                b"</body></html>"
            )
        else:
            body = b"<html><body>Error: token tidak ditemukan.</body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def start_sso_flow(zone_url: str, server_url: str, timeout: int = 120) -> str | None:
    global _callback_token
    _callback_token = None
    _callback_event.clear()

    httpd = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    t = threading.Thread(target=httpd.handle_request, daemon=True)
    t.start()

    login_url = (
        f"{zone_url}/desktop-login"
        f"?callback=http://localhost:{CALLBACK_PORT}/callback&app=zface"
    )
    webbrowser.open(login_url)

    _callback_event.wait(timeout=timeout)
    httpd.server_close()

    if not _callback_token:
        return None

    try:
        resp = requests.post(
            f"{server_url}/api/auth/sso-verify",
            json={"token": _callback_token},
            timeout=10,
        )
        if resp.ok:
            data = resp.json()
            return data.get("access_token") or data.get("token")
    except Exception:
        pass

    return None
