import importlib
import sys

import model.crypto_data as cd


def test_no_tqdm(monkeypatch):
    real_tqdm = sys.modules.get("tqdm")
    monkeypatch.setitem(sys.modules, "tqdm", None)
    cd_missing = importlib.reload(cd)
    assert list(cd_missing.tqdm(range(3))) == [0, 1, 2]
    if real_tqdm is not None:
        monkeypatch.setitem(sys.modules, "tqdm", real_tqdm)
    importlib.reload(cd)
