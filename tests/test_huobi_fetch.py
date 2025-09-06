import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data

def test_fetch_ohlcv_huobi(monkeypatch):
    markets = [("huobi", "BTC/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: markets)

    class Huobi:
        symbols = ["BTC/USDT"]
        def __init__(self, params=None):
            pass
        def load_markets(self):
            return
        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            assert symbol == "BTC/USDT"
            assert since > 0
            return [[since, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=["huobi"], huobi=Huobi)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data, failures = crypto_data.fetch_ohlcv("btc", exchange="huobi")
    assert failures == []
    assert data["huobi"][0][1:] == [1, 2, 3, 4, 5]
