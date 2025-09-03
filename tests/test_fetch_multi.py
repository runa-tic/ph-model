import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_fetch_ohlcv_all_exchanges(monkeypatch):
    markets = [("ex1", "AAA/USDT"), ("ex2", "AAA/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: markets)

    class Ex1:
        symbols = ["AAA/USDT"]

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

    class Ex2:
        symbols = ["AAA/USDT"]

        def __init__(self, params=None):
            self.called = False

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            assert since > 0
            if self.called:
                return []
            self.called = True
            return [[since, 6, 7, 8, 9, 10]]

    fake_ccxt = types.SimpleNamespace(exchanges=["ex1", "ex2"], ex1=Ex1, ex2=Ex2)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data = crypto_data.fetch_ohlcv("aaa")
    assert set(data.keys()) == {"ex1", "ex2"}
    assert data["ex1"][0][1:] == [1, 2, 3, 4, 5]
    assert data["ex2"][0][1:] == [6, 7, 8, 9, 10]

