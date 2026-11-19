"""JSON HTTP helpers used by integrations."""

import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .errors import IntegrationError


def request_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    body: object | None = None,
    timeout: float = 30,
    verify_tls: bool = True,
) -> object:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = Request(url, data=payload, headers=request_headers, method=method)
    context = None if verify_tls else ssl._create_unverified_context()
    try:
        with urlopen(request, timeout=timeout, context=context) as response:
            raw = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        raise IntegrationError(
            f"HTTP {exc.code} from GLPI: {detail or exc.reason}"
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise IntegrationError(f"Could not reach GLPI: {exc}") from exc
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrationError("GLPI returned a non-JSON response") from exc
