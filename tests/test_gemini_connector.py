"""Unit tests for the public Gemini ticker connector; no network required."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from tools.gemini_connector import get_gemini_ticker


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class GeminiConnectorTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "symbol": "BTCUSD",
            "close": "65000.00",
            "bid": "64999.00",
            "ask": "65001.00",
            "high": "66000.00",
            "low": "64000.00",
        }

    @patch("tools.gemini_connector.urlopen")
    def test_returns_normalized_ticker(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(self.payload)
        result = get_gemini_ticker("btcusd")
        self.assertEqual(result, {
            "exchange": "Gemini",
            "symbol": "BTCUSD",
            "last": "65000.00",
            "bid": "64999.00",
            "ask": "65001.00",
            "high_24h": "66000.00",
            "low_24h": "64000.00",
        })
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.gemini.com/v2/ticker/BTCUSD")
        self.assertEqual(mock_urlopen.call_args.kwargs["timeout"], 10)

    def test_rejects_invalid_symbols_before_network(self):
        with patch("tools.gemini_connector.urlopen") as mock_urlopen:
            for symbol in ("", "../BTCUSD", "BTC-USD", "BTC USD", "A" * 31, None):
                with self.subTest(symbol=symbol):
                    with self.assertRaises(ValueError):
                        get_gemini_ticker(symbol)
            mock_urlopen.assert_not_called()

    @patch("tools.gemini_connector.urlopen", side_effect=URLError("offline"))
    def test_network_failure_is_sanitized(self, _mock_urlopen):
        with self.assertRaisesRegex(RuntimeError, "Could not reach Gemini API"):
            get_gemini_ticker()

    @patch("tools.gemini_connector.urlopen")
    def test_rejects_incomplete_payload(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse({"symbol": "BTCUSD"})
        with self.assertRaisesRegex(RuntimeError, "missing required fields"):
            get_gemini_ticker()


if __name__ == "__main__":
    unittest.main()
