import requests
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_fetch_coin_info_handles_http_error(monkeypatch):
    monkeypatch.setattr(crypto_data, "_get_coin_id", lambda ticker: "aether-games")

    class Resp:
        def raise_for_status(self):
            raise requests.HTTPError("429 Too Many Requests")

    monkeypatch.setattr(crypto_data.requests, "get", lambda url, timeout=30: Resp())

    with pytest.raises(ValueError) as exc:
        crypto_data.fetch_coin_info("aeg")
    assert "Too Many Requests" in str(exc.value)


def test_fetch_coin_info_prompts_for_supply(monkeypatch):
    monkeypatch.setattr(crypto_data, "_get_coin_id", lambda ticker: "foo")

    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "market_data": {
                    "current_price": {"usd": 1.0},
                    "circulating_supply": None,
                }
            }

    monkeypatch.setattr(crypto_data.requests, "get", lambda url, timeout=30: Resp())
    captured = {}

    def fake_input(prompt=""):
        captured["prompt"] = prompt
        return "12345"

    monkeypatch.setattr("builtins.input", fake_input)
    info = crypto_data.fetch_coin_info("foo")
    assert info["circulating_supply"] == 12345.0
    assert captured["prompt"].endswith("\n")
