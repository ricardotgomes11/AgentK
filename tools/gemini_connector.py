"""Read-only public market-data connector for Gemini.

This module only calls Gemini's public ticker endpoint. It does not use API
credentials and cannot access private account data, place orders, or withdraw.
"""
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "https://api.gemini.com"
_SYMBOL_RE = re.compile(r"^[A-Za-z0-9]{1,30}$")


def get_gemini_ticker(symbol: str = "BTCUSD") -> dict:
    """Return the latest public ticker observation for a trading pair."""
    if not isinstance(symbol, str) or not _SYMBOL_RE.fullmatch(symbol):
        raise ValueError("Invalid trading-pair symbol")

    url = f"{BASE_URL}/v2/ticker/{symbol.upper()}"
    request = Request(url, headers={"Accept": "application/json"}, method="GET")

    try:
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                raise RuntimeError(f"Gemini returned HTTP {response.status}")
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Gemini API returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError("Could not reach Gemini API") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Gemini returned invalid JSON") from exc

    required = ("symbol", "close", "bid", "ask", "high", "low")
    missing = [key for key in required if key not in payload]
    if missing:
        raise RuntimeError(
            "Gemini response missing required fields: " + ", ".join(missing)
        )

    return {
        "exchange": "Gemini",
        "symbol": payload["symbol"],
        "last": payload["close"],
        "bid": payload["bid"],
        "ask": payload["ask"],
        "high_24h": payload["high"],
        "low_24h": payload["low"],
    }


# Simple alias for agent frameworks that register tools by function name.
get_ticker = get_gemini_ticker


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch public Gemini ticker data (read-only; no API key needed)."
    )
    parser.add_argument("symbol", nargs="?", default="BTCUSD")
    args = parser.parse_args()
    try:
        print(json.dumps(get_gemini_ticker(args.symbol), indent=2))
    except (ValueError, RuntimeError) as exc:
        raise SystemExit(f"Connector error: {exc}") from exc
