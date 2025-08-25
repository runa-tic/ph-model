"""Command-line interface for fetching crypto data."""
from __future__ import annotations

import argparse
import logging


from .crypto_data import fetch_coin_info, fetch_ohlcv, save_to_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch token info and OHLCV data")
    parser.add_argument("ticker", help="Token ticker symbol, e.g. btc")
    parser.add_argument("--output", default=None, help="Output CSV filename")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    info = fetch_coin_info(args.ticker)
    ohlcv = fetch_ohlcv(args.ticker)

    filename = args.output or f"{args.ticker.upper()}_data.csv"
    save_to_csv(filename, info, ohlcv)
    print(f"Data written to {filename}")


if __name__ == "__main__":
    main()
