import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_prints_available_exchanges(monkeypatch, capsys):
    markets = [("foo", "BTC/USDT"), ("bar", "BTC/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: markets)

    class DummyExchange:
        symbols = ["BTC/USDT"]
        options = {}

        def __init__(self, params=None):
            pass

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            return [[since or 0, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=["foo"])
    setattr(fake_ccxt, "foo", DummyExchange)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    crypto_data.fetch_ohlcv("btc", exchange="foo")
    out = capsys.readouterr().out
    assert "foo" in out
    assert "bar" in out
