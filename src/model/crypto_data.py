"""Utilities to fetch cryptocurrency data."""
from __future__ import annotations

import csv
from datetime import datetime
from typing import Dict, List, Tuple


import ccxt
import requests


COINGECKO_API = "https://api.coingecko.com/api/v3"


def _get_coin_id(ticker: str) -> str:
    """Resolve CoinGecko coin ID for a ticker."""

    resp = requests.get(f"{COINGECKO_API}/coins/list", timeout=30)
    resp.raise_for_status()
    coins = resp.json()
    coin_id = next((c["id"] for c in coins if c["symbol"].lower() == ticker.lower()), None)
    if not coin_id:
        raise ValueError(f"Ticker {ticker} not found on CoinGecko")
    return coin_id


def fetch_coin_info(ticker: str) -> Dict[str, float]:
    """Fetch current price (USD) and circulating supply for a ticker."""
    coin_id = _get_coin_id(ticker)

    data_resp = requests.get(f"{COINGECKO_API}/coins/{coin_id}", timeout=30)
    data_resp.raise_for_status()
    data = data_resp.json()
    price = data["market_data"]["current_price"]["usd"]
    supply = data["market_data"]["circulating_supply"]
    return {"price": price, "circulating_supply": supply}


def _coin_markets(ticker: str) -> List[Tuple[str, str]]:
    """Return list of (exchange id, trading pair) for active markets."""
    coin_id = _get_coin_id(ticker)
    resp = requests.get(f"{COINGECKO_API}/coins/{coin_id}/tickers", timeout=30)
    resp.raise_for_status()
    data = resp.json()
    markets: List[Tuple[str, str]] = []
    for entry in data.get("tickers", []):
        exchange_id = entry["market"]["identifier"]
        pair = f"{entry['base']}/{entry['target']}"
        markets.append((exchange_id, pair))
    return markets


def fetch_ohlcv(ticker: str) -> List[List[float]]:
    """Fetch OHLCV data from the first active market available via ccxt."""
    markets = _coin_markets(ticker)
    for exchange_name, symbol in markets:
        if exchange_name not in ccxt.exchanges:
            continue
        exchange_class = getattr(ccxt, exchange_name)()
        timeframe = "1d"
        since = 0
        all_data: List[List[float]] = []
        try:
            while True:
                batch = exchange_class.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
                if not batch:
                    break
                all_data.extend(batch)
                since = batch[-1][0] + 24 * 60 * 60 * 1000
            if all_data:
                return all_data
        except Exception:
            continue
    raise ValueError(f"No OHLCV data available for {ticker}")



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
