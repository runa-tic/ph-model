from model.crypto_data import _coingecko_days, _normalize_exchange_id


def test_coingecko_days_rounding():
    assert _coingecko_days(364) == 365
    assert _coingecko_days(90) == 90


def test_exchange_normalization():
    assert _normalize_exchange_id('mxc') == 'mexc'
    assert _normalize_exchange_id('gate') == 'gate'
    assert _normalize_exchange_id('bybit_spot') == 'bybit'
