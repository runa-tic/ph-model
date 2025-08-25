import csv
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.crypto_data import save_surge_snippets


def test_save_surge_snippets(tmp_path):
    day_ms = 24 * 60 * 60 * 1000
    ohlcv = [
        [0, 1.0, 1.0, 0.9, 1.0, 10.0],
        [day_ms, 1.0, 1.0, 0.9, 1.0, 20.0],
        [2 * day_ms, 1.0, 2.5, 0.9, 2.0, 100.0],  # surge day (high 2.5x open)
        [3 * day_ms, 1.0, 1.0, 0.9, 1.0, 30.0],
        [4 * day_ms, 1.0, 1.0, 0.9, 1.0, 40.0],
    ]

    out_file = tmp_path / "surges.csv"
    save_surge_snippets(str(out_file), ohlcv, multiplier=2.0)

    with open(out_file, newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data_rows = [r for r in rows[1:] if r]

    # There should be exactly five rows of data for the surge window
    assert len(data_rows) == 5

    # Column for ph_volume should exist
    assert "ph_volume" in header

    # Locate the surge day row
    surge_row = next(r for r in data_rows if r[7] == "1")
    ph_volume_idx = header.index("ph_volume")
    assert float(surge_row[ph_volume_idx]) == 75.0
