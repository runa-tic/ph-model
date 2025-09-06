"""Command-line interface for fetching crypto data."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

try:
    from colorama import Fore, Style, init
except ModuleNotFoundError:  # pragma: no cover - fallback when colorama isn't bundled
    class _NoColor:
        def __getattr__(self, name: str) -> str:
            return ""

    Fore = Style = _NoColor()

    def init(*_args, **_kwargs):  # type: ignore
        pass

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


BASE_ART = """
            ..........    
           .----------.   
         .----------:.==. 
      ...:---------:-===:. 
       ..--------.:======.
       ..------.=========.
  .  ....:---.-=========:.
    ..  ..--:==========-. 
.     ..   .==========.   
  .      .   .......      
.    ..  .  . . ...       
     ..    .              
            .             
         . .              
"""

VARIANTS = ".:=-"


def animate_banner(frames: int = 20, delay: float = 0.05) -> None:
    lines = BASE_ART.splitlines()
    footer = [
        "Paper Hands Model [Version 1.0]",
        "\u00A9 Bitmaker L.L.C-FZ. All rights reserved.",
        "",
    ]
    for _ in range(frames):
        print("\033[H\033[2J", end="")
        for line in lines:
            animated = "".join(
                random.choice(VARIANTS) if ch != " " else " " for ch in line
            )
            print(Fore.CYAN + animated)
        for line in footer:
            print(Fore.CYAN + line)
        sys.stdout.flush()
        time.sleep(delay)
    print("\033[H\033[2J", end="")
    for line in lines:
        print(Fore.CYAN + line)
    for line in footer:
        print(Fore.CYAN + line)
    print()


def main() -> None:
    init(autoreset=True)

    def prompt(text: str) -> str:
        return input(Fore.YELLOW + text + Style.RESET_ALL)

    parser = argparse.ArgumentParser(description="Fetch token info and OHLCV data")
    parser.add_argument("ticker", nargs="?", help="Token ticker symbol, e.g. btc")
    parser.add_argument("--output", default=None, help="Output CSV filename")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    print(
        Fore.CYAN
        + "Paper Hands Model [Version 1.0]\n"
        + "\u00A9 Bitmaker L.L.C-FZ. All rights reserved.\n"
    )

    ticker = args.ticker or prompt("Enter token ticker: ").strip()

    try:
        info = fetch_coin_info(ticker)
        ohlcv_map, failures = fetch_ohlcv(ticker)
    except ValueError as exc:
        print(exc)
        return

    if not ohlcv_map:
        print("No OHLCV data available")
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

    print(
        f"{ticker.upper()} data for {len(ohlcv_map)} exchanges successfully fetched, "
        f"{len(failures)} exchanges failed. Files saved to {datasets_dir}"
    )

    mode = prompt("Select mode: buyback or liquidation (b/l): ").strip().lower()
    if mode.startswith("b"):
        try:
            pct_input = prompt(
                "Minimum intraday surge percentage (default 75): "
            ).strip()
            surge_pct = float(pct_input) if pct_input else 75.0
        except ValueError:
            print("Invalid numeric input")
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
        print(f"Average PH percentage: {avg}")

        try:
            final_price = float(prompt("Final desired price for buyback: "))
            q_pct = float(prompt("Increase in sell rate q percentage: "))
            step_input = prompt(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            print("Invalid numeric input")
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
        print(f"Buyback model written to {buyback_filename}")
        chart_file = datasets_dir / f"{base}_buyback.png"
        plot_buyback_chart(buyback_filename, chart_file)
        print(f"Buyback chart written to {chart_file}")
    elif mode.startswith("l"):
        try:
            pct_input = prompt(
                "Maximum intraday selloff percentage (default -50): "
            ).strip()
            selloff_pct = float(pct_input) if pct_input else -50.0
        except ValueError:
            print("Invalid numeric input")
            return
        if selloff_pct > 0:
            print(
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
        print(f"Average PH percentage: {avg}")

        try:
            final_price = float(prompt("Final desired price for liquidation: "))
            q_pct = float(
                prompt("Increase in sell buy rate q percentage: ")
            )
            step_input = prompt(
                "Price step percentage for schedule (default 5): "
            ).strip()
            step_pct = float(step_input) if step_input else 5.0
        except ValueError:
            print("Invalid numeric input")
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
        print(f"Liquidation model written to {liquidation_filename}")
    else:
        print("Invalid mode selected")
        return


if __name__ == "__main__":
    main()
