import csv
import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.crypto_data import save_buyback_model


def test_save_buyback_model(tmp_path):
    price = 0.0225
    supply = 58_345_815
    ph_percentage = 0.275  # 27.5%
    out_file = tmp_path / "buyback.csv"

    save_buyback_model(
        str(out_file), price, supply, ph_percentage, final_price=0.05, q_pct=1.0
    )

    with open(out_file, newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0][0] == "step"
    data_rows = [r for r in rows[1:] if r]
    assert data_rows

    first = data_rows[0]
    assert abs(float(first[2]) - price) < 1e-9
    tokens_to_sell = supply * ph_percentage
    steps = math.ceil((0.05 / price - 1) / 0.05) + 1
    q_factor = 1.0 + 1.0 / 100.0
    if q_factor == 1.0:
        expected_b1 = tokens_to_sell / steps
    else:
        expected_b1 = tokens_to_sell * (1 - q_factor) / (1 - q_factor ** steps)
    assert abs(float(first[3]) - expected_b1) < 1e-6

    last = data_rows[-1]
    assert float(last[2]) >= 0.05
    assert float(last[2]) <= 0.05 * 1.05
    assert abs(float(last[4]) - tokens_to_sell) < 1e-6
    assert abs(float(last[8]) - (supply - float(last[4]))) < 1e-6
    assert float(last[9]) == float(last[4])
