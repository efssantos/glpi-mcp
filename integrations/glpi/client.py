"""Client for GLPI's legacy REST API (apirest.php)."""

import base64
from urllib.parse import quote

from core.config import Settings
from core.errors import ConfigurationError, IntegrationError
from core.http import request_json


class GLPIClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.glpi_url:
            raise ConfigurationError("Set GLPI_URL to the GLPI server URL.")
        self.base_url = f"{settings.glpi_url}/{settings.glpi_api_path.strip('/') }"
        self._session_token: str | None = None

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.settings.glpi_app_token:
            headers["App-Token"] = self.settings.glpi_app_token
        if self.settings.glpi_user_token:
            headers["Authorization"] = f"user_token {self.settings.glpi_user_token}"
        elif self.settings.glpi_username is not None and self.settings.glpi_password is not None:
            raw = f"{self.settings.glpi_username}:{self.settings.glpi_password}".encode()
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
        return headers

    def _call(self, path: str, *, method: str = "GET", body: object | None = None,
              params: str = "") -> object:
        headers = self._headers()
        if self._session_token:
            headers["Session-Token"] = self._session_token
        url = f"{self.base_url}/{path.lstrip('/')}{params}"
        return request_json(url, method=method, headers=headers, body=body,
                            timeout=self.settings.request_timeout, verify_tls=self.settings.verify_tls)

    def start_session(self) -> None:
        if self._session_token:
            return
        result = self._call("initSession")
        if not isinstance(result, dict) or not result.get("session_token"):
            raise IntegrationError("GLPI did not return a session token; check API and credentials.")
        self._session_token = str(result["session_token"])

    def request(self, path: str, *, method: str = "GET", body: object | None = None,
                params: str = "") -> object:
        self.start_session()
        return self._call(path, method=method, body=body, params=params)

    def close(self) -> None:
        if self._session_token:
            try:
                self._call("killSession")
            finally:
                self._session_token = None

    def get(self, itemtype: str, item_id: int) -> object:
        return self.request(f"{quote(itemtype, safe='')}/{item_id}")

    def search(self, itemtype: str, *, criteria: str = "", limit: int = 50) -> object:
        params = f"?range=0-{max(0, min(limit, 100)-1)}"
        if criteria:
            params += "&" + criteria.lstrip("?&")
        return self.request(f"search/{quote(itemtype, safe='')}", params=params)

    def create(self, itemtype: str, fields: dict) -> object:
        return self.request(f"{quote(itemtype, safe='')}", method="POST", body={"input": fields})

    def update(self, itemtype: str, item_id: int, fields: dict) -> object:
        return self.request(f"{quote(itemtype, safe='')}/{item_id}", method="PUT", body={"input": {"id": item_id, **fields}})
