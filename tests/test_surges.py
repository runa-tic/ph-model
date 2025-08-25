import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.crypto_data import save_surge_snippets


def test_save_surge_snippets(tmp_path):
    day_ms = 24 * 60 * 60 * 1000
    ohlcv = [
        [0, 1.0, 1.5, 0.9, 1.2, 0.0],
        [day_ms, 1.0, 1.8, 0.8, 1.6, 0.0],  # high is 1.8x the open -> surge
        [2 * day_ms, 1.5, 1.6, 1.4, 1.5, 0.0],
    ]

    out_file = tmp_path / "surges.csv"
    save_surge_snippets(str(out_file), ohlcv)

    with open(out_file, newline="") as f:
        rows = list(csv.reader(f))

    # there should be a row marking the surge day
    assert any(row and row[-1] == "1" for row in rows), rows
