import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data

def _run_exchange(exchange_id, monkeypatch):
    markets = [(exchange_id, "BTC/USDT")]
    monkeypatch.setattr(crypto_data, "_coin_markets", lambda ticker: markets)

    class DummyExchange:
        symbols = ["BTC/USDT"]
        options = {}

        def __init__(self, params=None):
            pass

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            assert symbol == "BTC/USDT"
            assert since > 0
            return [[since, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=[exchange_id])
    setattr(fake_ccxt, exchange_id, DummyExchange)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data, failures = crypto_data.fetch_ohlcv("btc", exchange=exchange_id)
    assert failures == []
    assert data[exchange_id][0][1:] == [1, 2, 3, 4, 5]


def test_fetch_ohlcv_latoken(monkeypatch):
    _run_exchange("latoken", monkeypatch)


def test_fetch_ohlcv_lbank(monkeypatch):
    _run_exchange("lbank", monkeypatch)
