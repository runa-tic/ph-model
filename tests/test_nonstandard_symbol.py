import types
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_fetch_ohlcv_handles_renamed_base(monkeypatch, capsys):
    monkeypatch.setattr(crypto_data, "_get_coin_id", lambda ticker: "chrono.tech")

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "tickers": [
                    {
                        "base": "TIMECHRONO",
                        "target": "USDT",
                        "market": {"identifier": "gate-io"},
                    }
                ]
            }

    monkeypatch.setattr(crypto_data.requests, "get", lambda url, timeout=30: Resp())

    class DummyExchange:
        symbols = ["TIMECHRONO/USDT"]
        options = {}

        def __init__(self, params=None):
            pass

        def load_markets(self):
            return

        def fetch_ohlcv(self, symbol, timeframe="1d", since=0, limit=1000):
            assert symbol == "TIMECHRONO/USDT"
            return [[since or 0, 1, 2, 3, 4, 5]]

    fake_ccxt = types.SimpleNamespace(exchanges=["gate"])
    setattr(fake_ccxt, "gate", DummyExchange)
    monkeypatch.setattr(crypto_data, "ccxt", fake_ccxt)

    data, failures = crypto_data.fetch_ohlcv("time", exchange="gate")
    out = capsys.readouterr().out
    assert "gate" in out
    assert failures == []
    assert data["gate"][0][1:] == [1, 2, 3, 4, 5]

