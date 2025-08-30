"""Command-line interface for fetching crypto data."""
from __future__ import annotations

import argparse
import logging


from .crypto_data import (
    fetch_coin_info,
    fetch_ohlcv,
    plot_buyback_chart,
    save_buyback_model,
    save_selloff_snippets,
    save_surge_snippets,
    save_liquidation_model,
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

    mode = input("Select mode: buyback or liquidation (b/l): ").strip().lower()
    if mode.startswith("b"):
        try:
            pct_input = input(
                "Minimum intraday surge percentage (default 75): "
            ).strip()
            surge_pct = float(pct_input) if pct_input else 75.0
        except ValueError:
            print("Invalid numeric input")
            return
        surge_pct = abs(surge_pct)
        surge_filename = filename.replace("_data", "_surges")
        avg = save_surge_snippets(
            surge_filename,
            ohlcv,
            info["circulating_supply"],
            1 + surge_pct / 100,
        )
        print(f"Surge snippets written to {surge_filename}")
        print(f"Average PH percentage: {avg}")

        try:
            final_price = float(input("Final desired price for buyback: "))
            q_pct = float(input("Increase in sell rate q percentage: "))
            step_input = input(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            print("Invalid numeric input")
            return

        buyback_filename = filename.replace("_data", "_buyback")
        save_buyback_model(
            buyback_filename,
            info["price"],
            info["circulating_supply"],
            avg,
            final_price,
            q_pct,
            step_pct,
        )
        print(f"Buyback model written to {buyback_filename}")
        chart_file = buyback_filename.replace(".csv", ".png")
        plot_buyback_chart(buyback_filename, chart_file)
        print(f"Buyback chart written to {chart_file}")
    elif mode.startswith("l"):
        try:
            pct_input = input(
                "Maximum intraday selloff percentage (default -50): "
            ).strip()
            selloff_pct = float(pct_input) if pct_input else -50.0
        except ValueError:
            print("Invalid numeric input")
            return
        selloff_pct = -abs(selloff_pct)
        selloff_filename = filename.replace("_data", "_selloffs")
        avg = save_selloff_snippets(
            selloff_filename,
            ohlcv,
            info["circulating_supply"],
            1 + selloff_pct / 100,
        )
        print(f"Selloff snippets written to {selloff_filename}")
        print(f"Average PH percentage: {avg}")

        try:
            final_price = float(input("Final desired price for liquidation: "))
            q_pct = float(input("Increase in sell rate q percentage: "))
            step_input = input(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            print("Invalid numeric input")
            return

        liquidation_filename = filename.replace("_data", "_liquidation")
        save_liquidation_model(
            liquidation_filename,
            info["price"],
            info["circulating_supply"],
            avg,
            final_price,
            q_pct,
            step_pct,
        )
        print(f"Liquidation model written to {liquidation_filename}")
    else:
        print("Invalid mode selected")
        return


if __name__ == "__main__":
    main()
