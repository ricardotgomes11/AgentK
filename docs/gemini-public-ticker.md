# Gemini public ticker tool

AgentK can use `tools.gemini_connector.get_gemini_ticker(symbol)` to retrieve
public market data from Gemini's `GET /v2/ticker/{symbol}` endpoint.

Example:

```python
from tools.gemini_connector import get_gemini_ticker

observation = get_gemini_ticker("BTCUSD")
```

The returned JSON-compatible dictionary contains the exchange, symbol, last
price, bid, ask, 24-hour high, and 24-hour low. It is a public-data observation,
not a trading recommendation.

## Security boundary

- No Gemini password or API key is used.
- No private account data is accessed.
- No order, transfer, or withdrawal endpoint is implemented.
- Network access is limited to a constructed URL on `api.gemini.com`.
- The connector has a 10-second request timeout and validates the symbol.

## Test

From the repository root, run:

```bash
python -m unittest tests.test_gemini_connector
```

Tests mock the HTTP response and do not require live network access.
