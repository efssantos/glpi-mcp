"""Tests for the shared JSON HTTP helper."""

import io
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from core.errors import IntegrationError
from core.http import request_json


class HTTPHelperTests(unittest.TestCase):
    @patch("core.http.urlopen")
    def test_decodes_json_response(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok": true}'
        urlopen.return_value = response
        self.assertEqual(request_json("https://example.test/api"), {"ok": True})

    @patch("core.http.urlopen")
    def test_returns_none_for_empty_response(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b""
        urlopen.return_value = response
        self.assertIsNone(request_json("https://example.test/api"))

    @patch("core.http.urlopen")
    def test_rejects_non_json_response(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b"not-json"
        urlopen.return_value = response
        with self.assertRaisesRegex(IntegrationError, "non-JSON"):
            request_json("https://example.test/api")

    @patch("core.http.urlopen")
    def test_translates_http_errors(self, urlopen):
        urlopen.side_effect = HTTPError("https://example.test", 401, "Unauthorized", {}, io.BytesIO(b"bad token"))
        with self.assertRaisesRegex(IntegrationError, "HTTP 401"):
            request_json("https://example.test/api")

    @patch("core.http.urlopen")
    def test_translates_connection_errors(self, urlopen):
        urlopen.side_effect = URLError("connection refused")
        with self.assertRaisesRegex(IntegrationError, "Could not reach GLPI"):
            request_json("https://example.test/api")

    @patch("core.http.urlopen")
    def test_serializes_request_body_and_sets_content_type(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"created": true}'
        urlopen.return_value = response
        request_json("https://example.test/api", method="POST", body={"name": "Ticket"})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(request.data, b'{"name": "Ticket"}')


if __name__ == "__main__":
    unittest.main()
