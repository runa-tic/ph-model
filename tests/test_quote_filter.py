import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_coin_markets_filters_quotes(monkeypatch):
    def fake_get(url, timeout):  # noqa: D401 - simple fake response
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "tickers": [
                        {
                            "market": {"identifier": "bitstamp"},
                            "base": "BTC",
                            "target": "USD",
                        },
                        {
                            "market": {"identifier": "bitflyer"},
                            "base": "BTC",
                            "target": "JPY",
                        },
                        {
                            "market": {"identifier": "yobit"},
                            "base": "LTC",
                            "target": "BTC",
                        },
                        {
                            "market": {"identifier": "binance"},
                            "base": "BTC",
                            "target": "USDT",
                        },
                    ]
                }

        return Resp()

    monkeypatch.setattr(crypto_data, "_get_coin_id", lambda t: "bitcoin")
    monkeypatch.setattr(crypto_data.requests, "get", fake_get)

    markets = crypto_data._coin_markets("btc")
    assert ("bitstamp", "BTC/USD") in markets
    assert ("binance", "BTC/USDT") in markets
    # Non-dollar and cross pairs are filtered out
    assert all(ex != "bitflyer" for ex, _ in markets)
    assert all(pair != "LTC/BTC" for _, pair in markets)

