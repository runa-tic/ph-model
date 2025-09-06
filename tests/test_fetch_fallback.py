import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_fetch_ohlcv_generic_exchange(monkeypatch):
    # No markets reported from CoinGecko
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: [])

    class FakeExchange:
        symbols = ["FURY/USDT"]

        def __init__(self, params=None):
            self.called = False

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            assert since > 0
            if self.called:
                return []
            self.called = True
            return [[since, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=["fake"], fake=FakeExchange)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data, failures = crypto_data.fetch_ohlcv("fury")
    assert failures == []
    assert set(data.keys()) == {"fake"}
    assert data["fake"][0][1:] == [1, 2, 3, 4, 5]


def test_fetch_ohlcv_trade_build(monkeypatch):
    markets = [("ex", "AAA/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda t: markets)

    class FakeExchange:
        symbols = ["AAA/USDT"]

        def __init__(self, params=None):
            pass

        def load_markets(self):
            return

        def fetch_ohlcv(self, *args, **kwargs):
            raise Exception("unsupported")

        def fetch_trades(self, symbol, since=None, limit=None):
            ts = since or 0
            return [
                {"timestamp": ts, "price": 1, "amount": 1},
                {"timestamp": ts + 1000, "price": 2, "amount": 1},
            ]

        def parse_timeframe(self, tf):
            return 86400

    fake_ccxt = types.SimpleNamespace(exchanges=["ex"], ex=FakeExchange)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data, failures = crypto_data.fetch_ohlcv("aaa")
    assert failures == []
    assert data["ex"][0][1:] == [1, 2, 1, 2, 2]
