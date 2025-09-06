# ph-model

A command-line tool for analysing cryptocurrency price surges and modelling
paper-hands token buybacks.

## Features

- Fetch current USD price and circulating supply from CoinGecko.
- Retrieve up to the last 364 days of daily OHLCV candles from an exchange via
  [ccxt](https://github.com/ccxt/ccxt) with automatic fallbacks to CoinGecko.
- Normalise exchange identifiers from CoinGecko to ccxt (e.g. `okex` → `okx`,
  `crypto_com` → `cryptocom`, `huobi` → `htx`, `p2pb2b` → `p2b`) so these
  markets are supported out of the box.
- Display a progress bar while downloading OHLCV data across exchanges (falls back to plain output when `tqdm` isn't installed).
- Restrict markets to USD and USD-pegged quote currencies (e.g. USDT, USDC) to
  avoid non-dollar or cross pairs such as `BTC/JPY` or `LTC/BTC`.
- Detect days where the intraday high is at least 75% above the open price and
  export five-day "surge snippets" that include `ph_volume` and `ph_percentage`
  metrics.
- Compute the average paper-hands percentage across all surge events.
- Build a geometric buyback model using 5% price steps and a user-supplied
  increase in sell rate, saving both a CSV and a PNG chart.

## Installation

1. **Clone the repository**

    ```bash
    git clone https://github.com/runa-tic/ph-model.git
    cd ph-model
    ```

2. **Create a virtual environment** *(recommended)*

    ```bash
    python -m venv .venv
    source .venv/bin/activate #.venv\Scripts\activate
    ```

3. **Install dependencies**

    ```bash
    pip install -e .
    ```

4. **Run the test suite** *(optional but recommended)*

    ```bash
    pytest -q
    ```

## Usage

```bash
crypto-fetch [ticker]
```

If `ticker` is omitted, you will be prompted to enter it interactively.

When launched, the tool displays a brief introduction:

```
Paper Hands Model [Version 1.0]
© Bitmaker L.L.C-FZ. All rights reserved.
```

If `colorama` is available, prompts are highlighted to provide a friendlier
interface, but the CLI also runs without it for standalone builds.

Example:

```bash
crypto-fetch btc
```

All generated CSV and PNG files are stored in `dist/datasets/`.

Running the command performs the following steps:

1. Fetch matching coins from CoinGecko and prompt you to choose the correct one
   if several share the same ticker.
2. Discover markets for the coin and ask for an exchange when multiple options
   are available.
3. Download up to 364 days of OHLCV data from the chosen exchange or, if
   exchanges fail, from CoinGecko.
4. Write one CSV per exchange under `dist/datasets/` containing the current
   price, circulating supply and OHLCV history, then summarise how many
   exchanges succeeded or failed.
5. Generate `dist/datasets/<TICKER>_<EXCHANGE>_surges.csv` files with five-day
   windows around `high / open >= 1.75`, including `ph_volume` and
   `ph_percentage` columns, and print the average paper-hands percentage across
   exchanges.
6. Prompt for a final buyback price and a percentage `q` increase in sell rate,
   then create `dist/datasets/<TICKER>_buyback.csv` together with a chart
   `dist/datasets/<TICKER>_buyback.png`.

Use the `--debug` flag to print detailed logging while the tool runs.

### Build a standalone binary

To distribute the CLI as a single executable (so end users do not need Python installed),
bundle it with [PyInstaller](https://pyinstaller.org/):

```bash
pip install pyinstaller
pyinstaller --name crypto-fetch --onefile src/model/cli.py --paths src
```

The compiled binary will be available in the `dist/` directory.

### Run from Finder on macOS

If you want to launch the binary by double-clicking in Finder, create a small
wrapper script in the project root:

```bash
#!/bin/bash
cd "$(dirname "$0")/dist"
./crypto-fetch "$@"
read -p "Press Enter to close..."
```

Save this as `crypto-fetch.command` and make it executable:

```bash
chmod +x crypto-fetch.command
```

Double-clicking `crypto-fetch.command` opens Terminal, runs the compiled
binary, and keeps the window open until you press Enter.

## Buyback model

The buyback schedule models how many tokens are repurchased to reach a desired
final price. Starting from the current price, each row represents a 5% price
increase. The number of tokens sold at each step grows geometrically by `q`
percent. The model uses the average `ph_percentage` computed from surge snippets
to estimate total tokens sold and produces a cumulative USD value chart.

