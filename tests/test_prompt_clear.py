import re
import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model import crypto_data


def test_get_coin_id_clears_without_newline(monkeypatch, capsys):
    class Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return [
                {"id": "coin-a", "symbol": "btc", "name": "Coin A"},
                {"id": "coin-b", "symbol": "btc", "name": "Coin B"},
            ]

    monkeypatch.setattr(crypto_data.requests, "get", lambda url, timeout=30: Resp())
    monkeypatch.setattr("builtins.input", lambda: "1")

    coin_id = crypto_data._get_coin_id("btc")
    assert coin_id == "coin-a"
    out = capsys.readouterr().out
    ansi = re.compile(r"\x1b\[[0-9;]*m")
    clean = ansi.sub("", out)
    assert "Select coin [1-2]: \n" not in clean
    assert clean.endswith("\033[H\033[2J")
