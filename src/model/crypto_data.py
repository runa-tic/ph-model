"""Utilities to fetch cryptocurrency data."""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Tuple


import ccxt
import requests


COINGECKO_API = "https://api.coingecko.com/api/v3"

MS_IN_DAY = 24 * 60 * 60 * 1000
DAYS_LIMIT = 364


logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def _get_coin_id(ticker: str) -> str:
    """Resolve CoinGecko coin ID for a ticker.

    If multiple coins share the same ticker symbol, present the user with a
    list of options and let them choose the desired coin ID.
    """

    try:
        resp = requests.get(f"{COINGECKO_API}/coins/list", timeout=30)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(f"CoinGecko coin list request failed: {exc}") from exc
    coins = [c for c in resp.json() if c["symbol"].lower() == ticker.lower()]
    if not coins:
        raise ValueError(f"Ticker {ticker} not found on CoinGecko")
    if len(coins) == 1:
        return coins[0]["id"]

    print(f"Multiple coins found for ticker '{ticker}':")
    for idx, coin in enumerate(coins, start=1):
        print(f"{idx}. {coin['name']} ({coin['id']})")

    while True:
        choice = input(f"Select coin [1-{len(coins)}]: ")
        try:
            idx = int(choice)
            if 1 <= idx <= len(coins):
                return coins[idx - 1]["id"]
        except ValueError:
            pass
        print("Invalid selection. Please try again.")


def fetch_coin_info(ticker: str) -> Dict[str, float]:
    """Fetch current price (USD) and circulating supply for a ticker."""
    coin_id = _get_coin_id(ticker)

    try:
        data_resp = requests.get(f"{COINGECKO_API}/coins/{coin_id}", timeout=30)
        data_resp.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(
            f"CoinGecko coin info request failed for {coin_id}: {exc}"
        ) from exc
    data = data_resp.json()
    price = data["market_data"]["current_price"]["usd"]
    supply = data["market_data"]["circulating_supply"]
    return {"price": price, "circulating_supply": supply}


def _coin_markets(ticker: str) -> List[Tuple[str, str]]:
    """Return list of (exchange id, trading pair) for active markets."""
    coin_id = _get_coin_id(ticker)
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/{coin_id}/tickers", timeout=30
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(
            f"CoinGecko markets request failed for {coin_id}: {exc}"
        ) from exc
    data = resp.json()
    markets: List[Tuple[str, str]] = []
    for entry in data.get("tickers", []):
        exchange_id = entry["market"]["identifier"]
        pair = f"{entry['base']}/{entry['target']}"
        markets.append((exchange_id, pair))
    return markets


def fetch_ohlcv(ticker: str, exchange: str | None = None) -> List[List[float]]:
    """Fetch up to the last ``DAYS_LIMIT`` days of OHLCV data.

    Data is retrieved from ccxt exchanges when available; otherwise the
    CoinGecko OHLC endpoint is used as a fallback.
    """

    markets = _coin_markets(ticker)
    logger.debug("Found %d markets for %s", len(markets), ticker)

    supported_markets = [m for m in markets if m[0] in ccxt.exchanges]
    exchanges = sorted({ex for ex, _ in supported_markets})

    if exchange is None and exchanges:
        if len(exchanges) > 1:
            print(f"Available exchanges for {ticker}:")
            for idx, ex in enumerate(exchanges, start=1):
                print(f"{idx}. {ex}")
            while True:
                choice = input(f"Select exchange [1-{len(exchanges)}]: ")
                try:
                    idx = int(choice)
                    if 1 <= idx <= len(exchanges):
                        exchange = exchanges[idx - 1]
                        break
                except ValueError:
                    pass
                print("Invalid selection. Please try again.")
        else:
            exchange = exchanges[0]

    if exchange and exchange not in ccxt.exchanges:
        raise ValueError(f"Exchange {exchange} not supported by ccxt")

    attempted: set[str] = set()
    markets_to_try = [m for m in supported_markets if not exchange or m[0] == exchange]

    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    since_start = now_ms - DAYS_LIMIT * MS_IN_DAY

    for exchange_name, symbol in markets_to_try:
        attempted.add(exchange_name)
        exchange_class = getattr(ccxt, exchange_name)({"enableRateLimit": True})
        timeframe = "1d"
        since = since_start
        all_data: List[List[float]] = []
        logger.debug("Trying %s %s", exchange_name, symbol)
        try:
            exchange_class.load_markets()

            while True:
                batch = exchange_class.fetch_ohlcv(
                    symbol, timeframe=timeframe, since=since, limit=DAYS_LIMIT
                )
                if not batch:
                    break
                all_data.extend(batch)
                if len(all_data) >= DAYS_LIMIT:
                    all_data = all_data[-DAYS_LIMIT:]
                    break
                since = batch[-1][0] + MS_IN_DAY
            if all_data:
                logger.info(
                    "Fetched %d rows from %s %s", len(all_data), exchange_name, symbol
                )
                return all_data[-DAYS_LIMIT:]
        except Exception as exc:
            logger.warning("Failed to fetch %s on %s: %s", symbol, exchange_name, exc)
            continue

    # Try common trading pairs on selected or all exchanges before using CoinGecko
    base_symbol = ticker.upper()
    generic_pairs = [
        f"{base_symbol}/USDT",
        f"{base_symbol}/USD",
        f"{base_symbol}/BTC",
    ]

    exchange_list = [exchange] if exchange else ccxt.exchanges
    for exchange_name in exchange_list:
        if exchange_name in attempted:
            continue
        exchange_class = getattr(ccxt, exchange_name)({"enableRateLimit": True})
        try:
            exchange_class.load_markets()
        except Exception as exc:
            logger.debug("Skipping %s: %s", exchange_name, exc)
            continue
        for symbol in generic_pairs:
            if symbol not in getattr(exchange_class, "symbols", []):
                continue
            timeframe = "1d"
            since = since_start
            all_data: List[List[float]] = []
            logger.debug("Trying %s %s", exchange_name, symbol)
            try:
                while True:
                    batch = exchange_class.fetch_ohlcv(
                        symbol, timeframe=timeframe, since=since, limit=DAYS_LIMIT
                    )
                    if not batch:
                        break
                    all_data.extend(batch)
                    if len(all_data) >= DAYS_LIMIT:
                        all_data = all_data[-DAYS_LIMIT:]
                        break
                    since = batch[-1][0] + MS_IN_DAY
                if all_data:
                    logger.info(
                        "Fetched %d rows from %s %s", len(all_data), exchange_name, symbol
                    )
                    return all_data[-DAYS_LIMIT:]
            except Exception as exc:
                logger.warning("Failed to fetch %s on %s: %s", symbol, exchange_name, exc)
                break

    # Fall back to CoinGecko's OHLC endpoint if all ccxt markets fail
    logger.info("Falling back to CoinGecko OHLC for %s", ticker)
    coin_id = _get_coin_id(ticker)
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": DAYS_LIMIT},
            timeout=30,
        )
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise ValueError(
            f"CoinGecko OHLC request failed for {coin_id}: {exc}"
        ) from exc

    data = resp.json()
    if not data:
        raise ValueError(f"No OHLCV data available for {ticker}")

    data = data[-DAYS_LIMIT:]

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


def save_surge_snippets(
    filename: str, ohlcv: List[List[float]], multiplier: float = 1.75
) -> None:
    """Save windows around days where intraday high crosses ``multiplier``× open.

    ``multiplier`` defaults to ``1.75`` (75% surge).

    For each day where ``high / open`` is at least ``multiplier``, write a five-day
    window (two days before and after the surge) to ``filename``. The CSV includes
    an ``event_id`` to group rows and ``is_event_day`` flag.
    """

    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["event_id", "date", "open", "high", "low", "close", "volume", "is_event_day"]
        )
        event_id = 1
        for i, (ts, open_, high, low, close, volume) in enumerate(ohlcv):
            if open_ > 0 and (high / open_) >= multiplier:
                start = max(0, i - 2)
                end = min(len(ohlcv), i + 3)
                for j in range(start, end):
                    ts2, o2, h2, l2, c2, v2 = ohlcv[j]
                    writer.writerow(
                        [
                            event_id,
                            datetime.utcfromtimestamp(ts2 / 1000).strftime("%d-%m-%Y"),
                            o2,
                            h2,
                            l2,
                            c2,
                            v2,
                            1 if j == i else 0,
                        ]
                    )
                writer.writerow([])
                event_id += 1
