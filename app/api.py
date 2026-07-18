from typing import Any

import requests


class ZFaceAPI:
    def __init__(self, server_url: str, token: str = None):
        self.server_url = server_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, path: str, params: dict = None) -> Any:
        r = requests.get(f"{self.server_url}{path}", headers=self._headers(), params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def _post_json(self, path: str, data: dict) -> Any:
        r = requests.post(f"{self.server_url}{path}", headers=self._headers(), json=data, timeout=15)
        r.raise_for_status()
        return r.json()

    def _post_files(self, path: str, files: dict, data: dict = None) -> Any:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.post(f"{self.server_url}{path}", headers=headers, files=files, data=data, timeout=20)
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        return self._get("/api/health")

    def get_people(self) -> list:
        return self._get("/api/people")

    def identify_by_embedding(self, embedding: list, threshold: float = 0.40) -> list:
        return self._post_json("/api/identify-by-embedding", {
            "embedding": embedding,
            "threshold": threshold,
        })

    def register_by_file(self, name: str, image_bytes: bytes, filename: str = "photo.jpg") -> dict:
        return self._post_files(
            "/api/register",
            files={"file": (filename, image_bytes, "image/jpeg")},
            data={"name": name},
        )

    def register_by_embedding(self, name: str, embedding: list) -> dict:
        return self._post_json("/api/register-embedding", {"name": name, "embedding": embedding})

    def get_logs(self, limit: int = 100) -> list:
        return self._get("/api/logs", params={"limit": limit})

    def add_log(self, name: str, similarity: float, source: str = "desktop") -> dict:
        return self._post_json("/api/logs", {"name": name, "similarity": similarity, "source": source})
