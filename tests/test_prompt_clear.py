import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_get_coin_id_clears_and_uses_newline(monkeypatch, capsys):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {"id": "coin-a", "symbol": "btc", "name": "Coin A"},
                {"id": "coin-b", "symbol": "btc", "name": "Coin B"},
            ]

    monkeypatch.setattr(crypto_data.requests, "get", lambda url, timeout=30: Resp())

    captured = {}

    def fake_input(prompt=""):
        captured["prompt"] = prompt
        return "1"

    monkeypatch.setattr("builtins.input", fake_input)

    coin_id = crypto_data._get_coin_id("btc")
    assert coin_id == "coin-a"
    assert captured["prompt"].endswith("\n")
    out = capsys.readouterr().out
    assert out.endswith("\033[H\033[2J")
