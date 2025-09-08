"""Command-line interface for fetching crypto data."""
from __future__ import annotations

import argparse
import logging
import multiprocessing
import sys
from pathlib import Path
from typing import List

from colorama import Fore, Style, init

from model.crypto_data import (
    fetch_coin_info,
    fetch_ohlcv,
    plot_buyback_chart,
    save_buyback_model,
    save_selloff_snippets,
    save_surge_snippets,
    save_liquidation_model,
    save_to_csv,
)


BASE_ART = [
    "            ..........",
    "           .----------.",
    "         .----------:.==.",
    "      ...:---------:-===:.",
    "       ..--------.:======.",
    "       ..------.=========.",
    "  .  ....:---.-=========:.",
    "    ..  ..--:==========-.",
    ".     ..   .==========.",
    "  .      .   .......",
    ".    ..  .  . . ...",
    "     ..    .",
    "            .",
    "         . .",
]


def print_banner() -> None:
    """Render the static ASCII logo with coloured half-spheres."""
    print("\033[H\033[2J", end="")
    footer = [
        "Paper Hands Model [Version 1.0]",
        "\u00A9 Bitmaker L.L.C-FZ. All rights reserved.",
        "",
    ]
    width = max(len(line) for line in BASE_ART)
    midpoint = width // 2

    def colour_line(text: str) -> str:
        coloured = []
        for col, ch in enumerate(text.ljust(width)):
            if ch == " ":
                coloured.append(" ")
            elif ch == "=":
                colour = Fore.CYAN if col < midpoint else Fore.LIGHTRED_EX
                coloured.append(colour + ch)
            else:
                coloured.append(Fore.WHITE + ch)
        return "".join(coloured)

    for line in BASE_ART:
        print(colour_line(line))
    for line in footer:
        print(Fore.CYAN + line)
    print()


def main() -> None:
    multiprocessing.freeze_support()
    init(autoreset=True)
    print_banner()

    GRAY = Fore.LIGHTBLACK_EX
    WHITE = Fore.WHITE

    def console(text: str = "", end: str = "\n") -> None:
        print(GRAY + text + Style.RESET_ALL, end=end)

    def prompt(text: str) -> str:
        return input(GRAY + text + Style.RESET_ALL + WHITE)

    parser = argparse.ArgumentParser(description="Fetch token info and OHLCV data")
    parser.add_argument("ticker", nargs="?", help="Token ticker symbol, e.g. btc")
    parser.add_argument("--output", default=None, help="Output CSV filename")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args, _unknown = parser.parse_known_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)
    if _unknown:
        logging.debug("Ignoring extra args: %s", _unknown)

    ticker = args.ticker or prompt("Enter token ticker: ").strip()

    warns: List[str] = []
    try:
        info = fetch_coin_info(ticker)
        ohlcv_map, failures = fetch_ohlcv(ticker, progress=True, warnings=warns)
    except ValueError as exc:
        console(str(exc))
        return

    if not ohlcv_map:
        console("No OHLCV data available")
        return

    if getattr(sys, "frozen", False):
        dist_dir = Path(sys.executable).resolve().parent
    else:
        dist_dir = Path(__file__).resolve().parent.parent.parent / "dist"
    datasets_dir = dist_dir / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    base = args.output or ticker.upper()
    if base.lower().endswith(".csv"):
        base = base[:-4]
    for ex, data in ohlcv_map.items():
        filename = datasets_dir / f"{base}_{ex}_data.csv"
        save_to_csv(filename, info, data)

    console(
        f"{ticker.upper()} data for {len(ohlcv_map)} exchanges successfully fetched, "
        f"{len(failures)} exchanges failed. Files saved to {datasets_dir}"
    )
    if warns:
        console("Warnings:")
        for msg in warns:
            console(f"  - {msg}")

    mode = prompt("Select mode: buyback or liquidation (b/l): ").strip().lower()
    if mode.startswith("b"):
        try:
            console()
            pct_input = prompt(
                "Minimum intraday surge percentage (default 75): "
            ).strip()
            surge_pct = float(pct_input) if pct_input else 75.0
        except ValueError:
            console("Invalid numeric input")
            return
        surge_pct = abs(surge_pct)
        avgs = []
        for ex, data in ohlcv_map.items():
            surge_filename = datasets_dir / f"{base}_{ex}_surges.csv"
            avg = save_surge_snippets(
                surge_filename,
                data,
                info["circulating_supply"],
                1 + surge_pct / 100,
            )
            avgs.append(avg)
        avg = sum(avgs) / len(avgs) if avgs else 0.0
        console(f"Average PH percentage: {avg}")

        try:
            console()
            final_price = float(prompt("Final desired price for buyback: "))
            console()
            q_pct = float(prompt("Increase in sell rate q percentage: "))
            console()
            step_input = prompt(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            console("Invalid numeric input")
            return
        buyback_filename = datasets_dir / f"{base}_buyback.csv"
        save_buyback_model(
            buyback_filename,
            info["price"],
            info["circulating_supply"],
            avg,
            final_price,
            q_pct,
            step_pct,
        )
        console(f"Buyback model written to {buyback_filename}")
        chart_file = datasets_dir / f"{base}_buyback.png"
        plot_buyback_chart(buyback_filename, chart_file)
        console(f"Buyback chart written to {chart_file}")
    elif mode.startswith("l"):
        try:
            console()
            pct_input = prompt(
                "Maximum intraday selloff percentage (default -50): "
            ).strip()
            selloff_pct = float(pct_input) if pct_input else -50.0
        except ValueError:
            console("Invalid numeric input")
            return
        if selloff_pct > 0:
            console(
                f"Interpreting {selloff_pct}% as -{selloff_pct}% (selloff percentages should be negative)."
            )
        selloff_pct = -abs(selloff_pct)
        avgs = []
        for ex, data in ohlcv_map.items():
            selloff_filename = datasets_dir / f"{base}_{ex}_selloffs.csv"
            avg = save_selloff_snippets(
                selloff_filename,
                data,
                info["circulating_supply"],
                1 + selloff_pct / 100,
            )
            avgs.append(avg)
        avg = sum(avgs) / len(avgs) if avgs else 0.0
        console(f"Average PH percentage: {avg}")

        try:
            console()
            final_price = float(prompt("Final desired price for liquidation: "))
            console()
            q_pct = float(prompt("Increase in sell buy rate q percentage: "))
            console()
            step_input = prompt(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            console("Invalid numeric input")
            return
        liquidation_filename = datasets_dir / f"{base}_liquidation.csv"
        save_liquidation_model(
            liquidation_filename,
            info["price"],
            info["circulating_supply"],
            avg,
            final_price,
            q_pct,
            step_pct,
        )
        console(f"Liquidation model written to {liquidation_filename}")
    else:
        console("Invalid mode selected")
        return


if __name__ == "__main__":
    main()
