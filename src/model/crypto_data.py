"""Utilities to fetch cryptocurrency data."""
from __future__ import annotations

import csv
from datetime import datetime
from typing import Dict, List

import ccxt
import requests


COINGECKO_API = "https://api.coingecko.com/api/v3"


def fetch_coin_info(ticker: str) -> Dict[str, float]:
    """Fetch current price (USD) and circulating supply for a ticker.

    Parameters
    ----------
    ticker: str
        Symbol of the token, e.g. "btc".
    """
    # Find CoinGecko coin ID for ticker
    resp = requests.get(f"{COINGECKO_API}/coins/list", timeout=30)
    resp.raise_for_status()
    coins = resp.json()
    coin_id = next((c["id"] for c in coins if c["symbol"].lower() == ticker.lower()), None)
    if not coin_id:
        raise ValueError(f"Ticker {ticker} not found on CoinGecko")

    data_resp = requests.get(f"{COINGECKO_API}/coins/{coin_id}", timeout=30)
    data_resp.raise_for_status()
    data = data_resp.json()
    price = data["market_data"]["current_price"]["usd"]
    supply = data["market_data"]["circulating_supply"]
    return {"price": price, "circulating_supply": supply}


def fetch_ohlcv(ticker: str, exchange_name: str = "binance") -> List[List[float]]:
    """Fetch OHLCV data from an exchange using ccxt.

    Returns list of [timestamp, open, high, low, close, volume].
    """
    exchange_class = getattr(ccxt, exchange_name)()
    symbol = f"{ticker.upper()}/USDT"
    timeframe = "1d"
    since = 0
    all_data: List[List[float]] = []
    while True:
        batch = exchange_class.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        all_data.extend(batch)
        since = batch[-1][0] + 24 * 60 * 60 * 1000
    return all_data


def save_to_csv(filename: str, info: Dict[str, float], ohlcv: List[List[float]]) -> None:
    """Save token info and OHLCV data to a CSV file."""
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["metric", "value"])
        writer.writerow(["current_price_usd", info["price"]])
        writer.writerow(["circulating_supply", info["circulating_supply"]])
        writer.writerow([])
        writer.writerow(["timestamp", "open", "high", "low", "close", "volume"])
        for ts, open_, high, low, close, volume in ohlcv:
            writer.writerow([
                datetime.utcfromtimestamp(ts / 1000).isoformat(),
                open_,
                high,
                low,
                close,
                volume,
            ])
