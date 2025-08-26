"""Command-line interface for fetching crypto data."""
from __future__ import annotations

import argparse
import logging


from .crypto_data import (
    fetch_coin_info,
    fetch_ohlcv,
    save_buyback_model,
    save_surge_snippets,
    save_to_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch token info and OHLCV data")
    parser.add_argument("ticker", help="Token ticker symbol, e.g. btc")
    parser.add_argument("--output", default=None, help="Output CSV filename")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    try:
        info = fetch_coin_info(args.ticker)
        ohlcv = fetch_ohlcv(args.ticker)
    except ValueError as exc:
        print(exc)
        return

    filename = args.output or f"{args.ticker.upper()}_data.csv"
    save_to_csv(filename, info, ohlcv)
    print(f"Data written to {filename}")

    surge_filename = filename.replace("_data", "_surges")
    avg = save_surge_snippets(surge_filename, ohlcv, info["circulating_supply"])
    print(f"Surge snippets written to {surge_filename}")
    print(f"Average PH percentage: {avg}")

    try:
        step_pct = float(input("Price step percentage: "))
        q_pct = float(input("Increase in sell rate q percentage: "))
    except ValueError:
        print("Invalid numeric input")
        return

    buyback_filename = filename.replace("_data", "_buyback")
    save_buyback_model(
        buyback_filename,
        info["price"],
        info["circulating_supply"],
        avg,
        step_pct,
        q_pct,
    )
    print(f"Buyback model written to {buyback_filename}")


if __name__ == "__main__":
    main()
