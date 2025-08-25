"""Utilities to fetch cryptocurrency data."""
from __future__ import annotations

import csv
import logging
from datetime import datetime
from typing import Dict, List, Tuple


import ccxt
import requests


COINGECKO_API = "https://api.coingecko.com/api/v3"


logger = logging.getLogger(__name__)


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
    logger.debug("Found %d markets for %s", len(markets), ticker)
    for exchange_name, symbol in markets:
        if exchange_name not in ccxt.exchanges:
            logger.debug("Skipping unsupported exchange %s", exchange_name)
            continue
        exchange_class = getattr(ccxt, exchange_name)({"enableRateLimit": True})
        timeframe = "1d"
        since = 0
        all_data: List[List[float]] = []
        logger.debug("Trying %s %s", exchange_name, symbol)
        try:
            exchange_class.load_markets()

            while True:
                batch = exchange_class.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
                if not batch:
                    break
                all_data.extend(batch)
                since = batch[-1][0] + 24 * 60 * 60 * 1000
            if all_data:
                logger.info("Fetched %d rows from %s %s", len(all_data), exchange_name, symbol)
                return all_data
        except Exception as exc:
            logger.warning("Failed to fetch %s on %s: %s", symbol, exchange_name, exc)

            continue

    # Fall back to CoinGecko's OHLC endpoint if all ccxt markets fail
    logger.info("Falling back to CoinGecko OHLC for %s", ticker)
    coin_id = _get_coin_id(ticker)
    resp = requests.get(
        f"{COINGECKO_API}/coins/{coin_id}/ohlc",
        params={"vs_currency": "usd", "days": "max"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"No OHLCV data available for {ticker}")

    # CoinGecko's OHLC endpoint does not provide volume; set it to 0.0
    return [row + [0.0] for row in data]


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
