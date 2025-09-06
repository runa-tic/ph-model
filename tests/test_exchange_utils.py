from model.crypto_data import _coingecko_days, _normalize_exchange_id, _normalize_pair


def test_coingecko_days_rounding():
    assert _coingecko_days(364) == 365
    assert _coingecko_days(90) == 90


def test_exchange_normalization():
    assert _normalize_exchange_id('mxc') == 'mexc'
    assert _normalize_exchange_id('gate') == 'gate'
    assert _normalize_exchange_id('bybit_spot') == 'bybit'
    assert _normalize_exchange_id('okex') == 'okx'
    assert _normalize_exchange_id('crypto_com') == 'cryptocom'
    assert _normalize_exchange_id('hashkey_exchange') == 'hashkey'
    assert _normalize_exchange_id('huobi') == 'htx'
    assert _normalize_exchange_id('p2pb2b') == 'p2b'


def test_pair_normalization():
    assert _normalize_pair('kraken', 'XBT/EUR') == 'BTC/EUR'
    assert _normalize_pair('binance', 'BTC/USDT') == 'BTC/USDT'
