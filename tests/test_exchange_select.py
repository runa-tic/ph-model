import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_fetch_ohlcv_specific_exchange(monkeypatch):
    markets = [("ex1", "AAA/USDT"), ("ex2", "AAA/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: markets)

    class Ex1:
        symbols = ["AAA/USDT"]

        def __init__(self, params=None):
            pass

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            raise AssertionError("Ex1 should not be queried")

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
            return [[since, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=["ex1", "ex2"], ex1=Ex1, ex2=Ex2)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    # Simulate user selecting the second exchange from the prompt
    monkeypatch.setattr("builtins.input", lambda _: "2")

    data = crypto_data.fetch_ohlcv("aaa")
    assert data[0][1:] == [1, 2, 3, 4, 5]
