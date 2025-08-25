# ph-model

A simple CLI tool that gathers cryptocurrency information from CoinGecko and
historical OHLCV data from an exchange via ccxt.

## Usage

```bash
python -m model.cli btc
```

The script saves a CSV file combining the current price, circulating supply and
all available daily OHLCV data. The exchange is chosen automatically from the
active markets listed on CoinGecko.
