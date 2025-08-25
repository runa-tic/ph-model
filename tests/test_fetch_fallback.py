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

    data = crypto_data.fetch_ohlcv("fury")
    assert data[0][1:] == [1, 2, 3, 4, 5]
