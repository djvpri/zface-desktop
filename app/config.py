import json
import os

import keyring

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
KEYRING_SERVICE = "zface-desktop"
KEYRING_TOKEN_KEY = "auth_token"

DEFAULT_CONFIG = {
    "server_url": "https://zface.zomet.my.id",
    "zone_url": "https://zone.zomet.my.id",
    "threshold": 0.40,
    "camera_index": 0,
    "auto_log": True,
    "detect_interval_ms": 1000,
    "camera_active": False,
    "auto_detect": False,
}


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_token() -> str | None:
    return keyring.get_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)


def set_token(token: str):
    keyring.set_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY, token)


def clear_token():
    try:
        keyring.delete_password(KEYRING_SERVICE, KEYRING_TOKEN_KEY)
    except Exception:
        pass
