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
    supply = 1000.0
    avg = save_surge_snippets(str(out_file), ohlcv, supply, multiplier=2.0)

    with open(out_file, newline="") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    data_rows = [r for r in rows[1:] if r]

    # There should be exactly five rows of data for the surge window
    assert len(data_rows) == 5

    # Columns for ph_volume and ph_percentage should exist
    assert "ph_volume" in header
    assert "ph_percentage" in header

    # Locate the surge day row
    surge_row = next(r for r in data_rows if r[7] == "1")
    ph_volume_idx = header.index("ph_volume")
    ph_percentage_idx = header.index("ph_percentage")
    assert float(surge_row[ph_volume_idx]) == 75.0
    assert float(surge_row[ph_percentage_idx]) == 0.075
    assert avg == 0.075


def test_average_multiple_events(tmp_path):
    day_ms = 24 * 60 * 60 * 1000
    ohlcv = [
        [0, 1.0, 1.0, 0.9, 1.0, 10.0],
        [day_ms, 1.0, 2.0, 0.9, 1.5, 100.0],  # surge1 (2x)
        [2 * day_ms, 1.0, 1.0, 0.9, 1.0, 20.0],
        [3 * day_ms, 1.0, 2.0, 0.9, 1.5, 80.0],  # surge2 (2x)
        [4 * day_ms, 1.0, 1.0, 0.9, 1.0, 30.0],
    ]
    out_file = tmp_path / "surges2.csv"
    avg = save_surge_snippets(str(out_file), ohlcv, 1000.0, multiplier=2.0)
    expected = ((100.0 - (10.0 + 20.0 + 80.0) / 3) / 1000.0 + (80.0 - (100.0 + 20.0 + 30.0) / 3) / 1000.0) / 2
    assert avg == expected
