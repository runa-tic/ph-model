"""Utilities to fetch cryptocurrency data."""
from __future__ import annotations

import csv
import logging
import math
import sys
from datetime import datetime, timezone
from functools import lru_cache
from typing import Dict, List, Tuple


import ccxt
import requests

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm is missing
    def tqdm(iterable, **_):
        return iterable

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm is missing
    def tqdm(iterable, **_):
        return iterable

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm is missing
    def tqdm(iterable, **_):
        return iterable

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm is missing
    def tqdm(iterable, **_):
        return iterable

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover - fallback when tqdm is missing
    def tqdm(iterable, **_):
        return iterable


COINGECKO_API = "https://api.coingecko.com/api/v3"

MS_IN_DAY = 24 * 60 * 60 * 1000
DAYS_LIMIT = 364


# CoinGecko only accepts a limited set of "days" parameters for its OHLC
# endpoint.  Use the smallest allowed value greater than or equal to the
# desired ``DAYS_LIMIT``.  This prevents HTTP 400 errors such as the
# ``{"error":"Invalid days parameter"}`` seen when requesting 364 days.
COINGECKO_ALLOWED_DAYS = [1, 7, 14, 30, 90, 180, 365, 730]


def _coingecko_days(limit: int) -> int:
    """Return a valid ``days`` value for CoinGecko's OHLC endpoint."""

    for day in COINGECKO_ALLOWED_DAYS:
        if limit <= day:
            return day
    return COINGECKO_ALLOWED_DAYS[-1]


# Map CoinGecko market identifiers to ccxt exchange ids.  CoinGecko still
# uses legacy identifiers like ``mxc`` for MEXC; normalising ensures those
# exchanges appear in the available list.
EXCHANGE_ALIASES = {
    "mxc": "mexc",
    "gate-io": "gate",
    "gateio": "gate",
    "bybit_spot": "bybit",
    "bybit-spot": "bybit",
    "okex": "okx",
    "crypto_com": "cryptocom",
    "hashkey_exchange": "hashkey",
    "huobi": "huobi",
    "p2pb2b": "p2b",
}

# Exchanges that consistently fail to provide OHLCV data via ccxt. Treat them as
# unsupported to avoid noisy warnings during normal operation. Currently empty
# so all exchanges are attempted.
EXCHANGE_BLACKLIST: set[str] = set()

# Quote currencies considered "dollar" variations. Only markets using one of
# these as the quote currency will be fetched. This avoids cross pairs such as
# ``LTC/BTC`` or fiat pairs like ``BTC/JPY``.
ALLOWED_QUOTES = {
    "USD",
    "USDT",
    "USDC",
    "BUSD",
    "DAI",
    "TUSD",
    "USDD",
    "USDP",
    "PAX",
    "GUSD",
}

# Exchanges that consistently fail to provide OHLCV data via ccxt. Treat them as
# unsupported to avoid noisy warnings during normal operation.
EXCHANGE_BLACKLIST = {"lbank", "phemex", "latoken"}

# Quote currencies considered "dollar" variations. Only markets using one of
# these as the quote currency will be fetched. This avoids cross pairs such as
# ``LTC/BTC`` or fiat pairs like ``BTC/JPY``.
ALLOWED_QUOTES = {
    "USD",
    "USDT",
    "USDC",
    "BUSD",
    "DAI",
    "TUSD",
    "USDD",
    "USDP",
    "PAX",
    "GUSD",
}

# Exchanges that consistently fail to provide OHLCV data via ccxt. Treat them as
# unsupported to avoid noisy warnings during normal operation.
EXCHANGE_BLACKLIST = {"lbank", "phemex", "latoken"}


def _normalize_exchange_id(exchange_id: str) -> str:
    """Normalise CoinGecko market identifiers for ccxt."""

    return EXCHANGE_ALIASES.get(exchange_id.lower(), exchange_id.lower())


def _normalize_pair(exchange_id: str, pair: str) -> str:
    """Normalize trading pairs for specific exchanges."""

    if exchange_id == "kraken":
        return pair.replace("XBT", "BTC")
    return pair


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
    supply = data["market_data"].get("circulating_supply")
    if not supply:
        print("Failed to fetch circulating supply from CoinGecko.")
        while True:
            user_input = input("Please enter the circulating supply manually: ")
            try:
                supply = float(user_input)
                if supply > 0:
                    break
            except ValueError:
                pass
            print("Invalid input. Enter a positive number.")
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
    base_upper = ticker.upper()
    for entry in data.get("tickers", []):
        base = entry["base"].upper()
        quote = entry["target"].upper()
        if base != base_upper or quote not in ALLOWED_QUOTES:
            continue
        exchange_id = entry["market"]["identifier"]
        pair = f"{base}/{quote}"
        exchange_id = _normalize_exchange_id(exchange_id)
        pair = _normalize_pair(exchange_id, pair)
        markets.append((exchange_id, pair))
    return markets


def fetch_ohlcv(
    ticker: str,
    exchange: str | None = None,
    progress: bool = False,
    warnings: List[str] | None = None,
) -> Tuple[Dict[str, List[List[float]]], List[str]]:
    """Fetch up to the last ``DAYS_LIMIT`` days of OHLCV data.

    When ``exchange`` is ``None`` data is fetched from *all* ccxt-supported
    exchanges reported by CoinGecko. Returns a tuple ``(results, failures)``
    where ``results`` maps exchange ids to OHLCV rows and ``failures`` lists
    exchanges that yielded no data. If every exchange fails, the function
    falls back to CoinGecko's OHLC endpoint with the key ``"coingecko"``.

    Set ``progress=True`` to show a progress bar while iterating over exchanges.
    When ``warnings`` is provided, any errors are appended to it instead of being
    logged during the fetch. Callers can display the warnings afterwards,
    keeping the progress bar stable.
    """

    markets = _coin_markets(ticker)
    logger.debug("Found %d markets for %s", len(markets), ticker)

    supported_markets = [
        m for m in markets if m[0] in ccxt.exchanges and m[0] not in EXCHANGE_BLACKLIST
    ]
    markets_by_exchange: Dict[str, List[str]] = {}
    for ex, pair in supported_markets:
        markets_by_exchange.setdefault(ex, []).append(pair)

    collected: List[str] = warnings if warnings is not None else []

    # Record markets that cannot be fetched via ccxt or are blacklisted.
    unsupported = sorted(
        {
            ex
            for ex, _ in markets
            if ex not in ccxt.exchanges or ex in EXCHANGE_BLACKLIST
        }
    )
    if unsupported:
        collected.append("Unsupported exchanges: " + ", ".join(unsupported))

    exchanges_to_try = [exchange] if exchange else sorted(markets_by_exchange)
    if not exchanges_to_try:
        exchanges_to_try = list(ccxt.exchanges)

    results: Dict[str, List[List[float]]] = {}

    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    since_start = now_ms - DAYS_LIMIT * MS_IN_DAY

    def _trades_to_ohlcv(trades: List[Dict], duration: int) -> List[List[float]]:
        buckets: Dict[int, List[float]] = {}
        for t in trades:
            ts = int(math.floor(t["timestamp"] / duration) * duration)
            price = t["price"]
            amount = t["amount"]
            ohlcv = buckets.setdefault(
                ts, [ts, price, price, price, price, 0.0]
            )
            ohlcv[2] = max(ohlcv[2], price)
            ohlcv[3] = min(ohlcv[3], price)
            ohlcv[4] = price
            ohlcv[5] += amount
        return [buckets[k] for k in sorted(buckets)]

    def _build_from_trades(ex, symbol: str, since: int) -> List[List[float]]:
        timeframe = "1d"
        duration = ex.parse_timeframe(timeframe) * 1000
        all_data: List[List[float]] = []
        start = since
        while start < now_ms and len(all_data) < DAYS_LIMIT:
            trades = ex.fetch_trades(symbol, since=start, limit=1000)
            if not trades:
                start += duration
                continue
            ohlcv = _trades_to_ohlcv(trades, duration)
            all_data.extend(ohlcv)
            start = trades[-1]["timestamp"] + 1
        return all_data[-DAYS_LIMIT:]

    def _fetch_from_exchange(ex_name: str, symbol: str) -> List[List[float]]:
        exchange_class = getattr(ccxt, ex_name)({"enableRateLimit": True})
        timeframe = "1d"
        since = since_start
        all_data: List[List[float]] = []
        logger.debug("Trying %s %s", ex_name, symbol)
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
                logger.debug(
                    "Fetched %d rows from %s %s", len(all_data), ex_name, symbol
                )
                return all_data[-DAYS_LIMIT:]
        except Exception as exc:
            logger.debug("Initial fetch failed for %s on %s: %s", symbol, ex_name, exc)
            try:
                batch = exchange_class.fetch_ohlcv(
                    symbol, timeframe=timeframe, limit=DAYS_LIMIT
                )
                if batch:
                    logger.debug(
                        "Fetched %d rows from %s %s", len(batch), ex_name, symbol
                    )
                    return batch[-DAYS_LIMIT:]
            except Exception as exc2:
                logger.debug("Fetching without since failed for %s on %s: %s", symbol, ex_name, exc2)
                try:
                    return _build_from_trades(exchange_class, symbol, since_start)
                except Exception as exc3:
                    collected.append(
                        f"Failed to fetch {symbol} on {ex_name}: {exc3}"
                    )
        return []

    # First try explicit markets reported by CoinGecko
    iterator = tqdm(
        exchanges_to_try,
        desc="Fetching OHLCV",
        disable=not progress or not sys.stdout.isatty(),
    )
    for ex_name in iterator:
        for symbol in markets_by_exchange.get(ex_name, []):
            data = _fetch_from_exchange(ex_name, symbol)
            if data:
                results[ex_name] = data
                break

    # Try common trading pairs on exchanges that still lack data
    base_symbol = ticker.upper()
    generic_pairs = [f"{base_symbol}/{q}" for q in ("USDT", "USD", "USDC")]

    for ex_name in exchanges_to_try:
        if ex_name in results:
            continue
        exchange_class = getattr(ccxt, ex_name)({"enableRateLimit": True})
        try:
            exchange_class.load_markets()
        except Exception as exc:
            logger.debug("Skipping %s: %s", ex_name, exc)
            continue
        for symbol in generic_pairs:
            if symbol not in getattr(exchange_class, "symbols", []):
                continue
            data = _fetch_from_exchange(ex_name, symbol)
            if data:
                results[ex_name] = data
                break

    failures = [ex for ex in exchanges_to_try if ex not in results]
    if results:
        return results, failures

    # Fall back to CoinGecko's OHLC endpoint if all ccxt markets fail
    logger.info("Falling back to CoinGecko OHLC for %s", ticker)
    coin_id = _get_coin_id(ticker)
    try:
        resp = requests.get(
            f"{COINGECKO_API}/coins/{coin_id}/ohlc",
            params={"vs_currency": "usd", "days": _coingecko_days(DAYS_LIMIT)},
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
    return {"coingecko": [row + [0.0] for row in data]}, failures


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
    filename: str,
    ohlcv: List[List[float]],
    supply: float,
    multiplier: float = 1.75,
) -> float:
    """Save windows around days where intraday high crosses ``multiplier``× open.

    ``multiplier`` defaults to ``1.75`` (75% surge).

    ``supply`` is the circulating supply of the token and is used to compute
    ``ph_percentage`` (``ph_volume`` divided by supply).

    For each day where ``high / open`` is at least ``multiplier``, write a five-day
    window (two days before and after the surge) to ``filename``. The CSV includes
    an ``event_id`` to group rows, ``is_event_day`` flag, and ``ph_volume``/
    ``ph_percentage`` columns.
    """

    averages: List[float] = []
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "event_id",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "is_event_day",
                "ph_volume",
                "ph_percentage",
            ]
        )
        event_id = 1
        for i, (ts, open_, high, low, close, volume) in enumerate(ohlcv):
            if open_ > 0 and (high / open_) >= multiplier:
                start = max(0, i - 2)
                end = min(len(ohlcv), i + 3)

                surrounding = []
                for offset in (-2, -1, 1, 2):
                    j = i + offset
                    if 0 <= j < len(ohlcv):
                        surrounding.append(ohlcv[j][5])
                avg_surrounding = sum(surrounding) / len(surrounding) if surrounding else 0.0
                ph_volume = volume - avg_surrounding
                ph_percentage = ph_volume / supply if supply else 0.0
                averages.append(ph_percentage)
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
                            ph_volume,
                            ph_percentage,
                        ]
                    )
                writer.writerow([])
                event_id += 1

    return sum(averages) / len(averages) if averages else 0.0


def save_selloff_snippets(
    filename: str,
    ohlcv: List[List[float]],
    supply: float,
    multiplier: float = 0.5,
) -> float:
    """Save windows around days where intraday low falls below ``multiplier``× open.

    ``multiplier`` defaults to ``0.5`` (50% dump).

    ``supply`` is the circulating supply of the token and is used to compute
    ``ph_percentage`` (``ph_volume`` divided by supply).

    For each day where ``low / open`` is at most ``multiplier``, write a five-day
    window (two days before and after the selloff) to ``filename``. The CSV
    mirrors :func:`save_surge_snippets` and includes ``event_id`` to group rows,
    ``is_event_day`` flag, and ``ph_volume``/``ph_percentage`` columns.
    """

    averages: List[float] = []
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "event_id",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "is_event_day",
                "ph_volume",
                "ph_percentage",
            ]
        )
        event_id = 1
        for i, (ts, open_, high, low, close, volume) in enumerate(ohlcv):
            if open_ > 0 and (low / open_) <= multiplier:
                start = max(0, i - 2)
                end = min(len(ohlcv), i + 3)

                surrounding: List[float] = []
                for offset in (-2, -1, 1, 2):
                    j = i + offset
                    if 0 <= j < len(ohlcv):
                        surrounding.append(ohlcv[j][5])
                avg_surrounding = (
                    sum(surrounding) / len(surrounding) if surrounding else 0.0
                )
                ph_volume = volume - avg_surrounding
                ph_percentage = ph_volume / supply if supply else 0.0
                averages.append(ph_percentage)
                for j in range(start, end):
                    ts2, o2, h2, l2, c2, v2 = ohlcv[j]
                    writer.writerow(
                        [
                            event_id,
                            datetime.utcfromtimestamp(ts2 / 1000).strftime(
                                "%d-%m-%Y"
                            ),
                            o2,
                            h2,
                            l2,
                            c2,
                            v2,
                            1 if j == i else 0,
                            ph_volume,
                            ph_percentage,
                        ]
                    )
                writer.writerow([])
                event_id += 1

    return sum(averages) / len(averages) if averages else 0.0


def save_buyback_model(
    filename: str,
    price: float,
    supply: float,
    ph_percentage: float,
    final_price: float,
    q_pct: float,
    step_pct: float = 5.0,
) -> None:
    """Create a buyback model CSV based on selling pressure parameters.

    ``price`` and ``supply`` come from CoinGecko. ``ph_percentage`` is the
    average paper-hands percentage computed from surge snippets. ``final_price``
    specifies the last price level to model. Each row increases the price by a
    configurable ``step_pct`` percentage (default 5%). ``q_pct`` is the
    percentage increase in sell volume per step (e.g. 1 for a 1% increase).

    The resulting CSV contains a row for each ``step_pct`` price step until the
    price meets or exceeds ``final_price``. The model no longer halts when the
    estimated paper-hands token pool runs out; sales continue geometrically
    regardless of totals.
    """

    tokens_to_sell = supply * ph_percentage
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "step",
                "x",
                "price_usd",
                "tokens_sold",
                "tokens_sold_cumulative",
                "usd_value",
                "usd_value_cumulative",
                "weighted_avg_price",
                "freefloat",
                "buy_in_tokens",
            ]
        )

        if tokens_to_sell <= 0:
            return

        step_inc = step_pct / 100.0
        q_factor = 1.0 + q_pct / 100.0
        # number of steps required to reach the target price
        steps = math.ceil((final_price / price - 1) / step_inc) + 1
        if q_factor == 1.0:
            tokens_step = tokens_to_sell / steps
        else:
            tokens_step = tokens_to_sell * (1 - q_factor) / (1 - q_factor ** steps)
        step = 1
        price_mult = 1.0
        sold_cum = 0.0
        usd_cum = 0.0
        while True:
            price_level = price * price_mult
            sell_now = tokens_step
            sold_cum += sell_now
            usd_now = sell_now * price_level
            usd_cum += usd_now
            weighted_avg = usd_cum / sold_cum if sold_cum else 0.0
            freefloat = supply - sold_cum
            writer.writerow(
                [
                    step,
                    round(price_mult, 2),
                    price_level,
                    sell_now,
                    sold_cum,
                    usd_now,
                    usd_cum,
                    weighted_avg,
                    freefloat,
                    sold_cum,
                ]
            )
            if price_level >= final_price:
                break
            tokens_step *= q_factor
            price_mult += step_inc
            step += 1


def save_liquidation_model(
    filename: str,
    price: float,
    supply: float,
    ph_percentage: float,
    final_price: float,
    q_pct: float,
    step_pct: float = 5.0,
) -> None:
    """Create a liquidation model CSV based on dumping pressure parameters.

    ``price`` and ``supply`` come from CoinGecko. ``ph_percentage`` is the
    average paper-hands percentage computed from selloff snippets. ``final_price``
    specifies the last price level to model (typically below the current price).
    Each row decreases the price by a configurable ``step_pct`` percentage
    (default 5%). ``q_pct`` is the percentage increase in sell volume per step
    (e.g. 1 for a 1% increase).
    """

    tokens_to_sell = supply * ph_percentage
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "step",
                "x",
                "price_usd",
                "tokens_sold",
                "tokens_sold_cumulative",
                "usd_value",
                "usd_value_cumulative",
                "weighted_avg_price",
                "freefloat",
                "sell_out_tokens",
            ]
        )

        if tokens_to_sell <= 0:
            return

        step_inc = step_pct / 100.0
        q_factor = 1.0 + q_pct / 100.0
        steps = max(1, math.ceil((1 - final_price / price) / step_inc) + 1)
        if q_factor == 1.0:
            tokens_step = tokens_to_sell / steps
        else:
            tokens_step = tokens_to_sell * (1 - q_factor) / (1 - q_factor ** steps)

        step = 1
        price_mult = 1.0
        sold_cum = 0.0
        usd_cum = 0.0
        while True:
            price_level = price * price_mult
            sell_now = tokens_step
            sold_cum += sell_now
            usd_now = sell_now * price_level
            usd_cum += usd_now
            weighted_avg = usd_cum / sold_cum if sold_cum else 0.0
            freefloat = supply + sold_cum
            writer.writerow(
                [
                    step,
                    round(price_mult, 2),
                    price_level,
                    sell_now,
                    sold_cum,
                    usd_now,
                    usd_cum,
                    weighted_avg,
                    freefloat,
                    sold_cum,
                ]
            )
            if price_level <= final_price:
                break
            tokens_step *= q_factor
            price_mult -= step_inc
            step += 1


def plot_buyback_chart(csv_filename: str, image_filename: str) -> None:
    """Plot price vs cumulative USD value from a buyback model CSV."""
    prices: List[float] = []
    usd_cum: List[float] = []
    with open(csv_filename, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                prices.append(float(row["price_usd"]))
                usd_cum.append(float(row["usd_value_cumulative"]))
            except (KeyError, ValueError):
                continue
    if not prices:
        return
    import matplotlib.pyplot as plt

    plt.figure()
    plt.plot(prices, usd_cum)
    plt.xlabel("Price (USD)")
    plt.ylabel("Cumulative USD value")
    plt.title("Buyback schedule")
    plt.savefig(image_filename)
    plt.close()
