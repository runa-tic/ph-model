import csv
import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from model.crypto_data import save_liquidation_model

def test_save_liquidation_model(tmp_path):
    price = 0.0225
    supply = 58_345_815
    ph_percentage = 0.275
    out_file = tmp_path / "liquidation.csv"

    save_liquidation_model(
        str(out_file), price, supply, ph_percentage, final_price=0.01, q_pct=1.0, step_pct=10.0
    )

    with open(out_file, newline="") as f:
        rows = list(csv.reader(f))

    assert rows[0][0] == "step"
    data_rows = [r for r in rows[1:] if r]
    assert data_rows

    first = data_rows[0]
    assert abs(float(first[2]) - price) < 1e-9
    tokens_to_sell = supply * ph_percentage
    step_inc = 0.10
    steps = math.ceil((1 - 0.01 / price) / step_inc) + 1
    q_factor = 1.0 + 1.0 / 100.0
    if q_factor == 1.0:
        expected_b1 = tokens_to_sell / steps
    else:
        expected_b1 = tokens_to_sell * (1 - q_factor) / (1 - q_factor ** steps)
    assert abs(float(first[3]) - expected_b1) < 1e-6

    last = data_rows[-1]
    assert float(last[2]) <= 0.01
    assert float(last[2]) >= 0.01 - price * step_inc
    assert abs(float(last[4]) - tokens_to_sell) < 1e-6
    assert abs(float(last[8]) - (supply + float(last[4]))) < 1e-6
    assert float(last[9]) == float(last[4])
