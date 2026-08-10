from __future__ import annotations

import argparse
import json

from .engine import Scanner
from .io import load_config, load_stocks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Filter and rank stock market snapshots.")
    parser.add_argument("--input", required=True, help="Path to a stock snapshot CSV")
    parser.add_argument("--config", default="scanner_config.json", help="Path to filter configuration JSON")
    parser.add_argument("--format", choices=("table", "json"), default="table")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    results = Scanner(load_config(args.config)).scan(load_stocks(args.input))

    if args.format == "json":
        rows = [
            {
                "rank": rank,
                "symbol": result.stock.symbol,
                "score": result.score,
                "price": result.stock.price,
                "rvol": round(result.stock.rvol, 2),
                "current_volume": result.stock.current_volume,
                "avg_volume_5d": result.stock.avg_volume_5d,
                "avg_volume_20d": result.stock.avg_volume_20d,
                "atr_percent": round(result.stock.atr_percent, 2),
                "latest_percent_change": result.stock.latest_percent_change,
                "volume_percent_change": round(result.stock.volume_percent_change, 2),
                "float_shares": result.stock.float_shares,
            }
            for rank, result in enumerate(results, start=1)
        ]
        print(json.dumps(rows, indent=2))
        return

    if not results:
        print("No stocks matched the configured filters.")
        return

    print(f"{'#':>2}  {'SYMBOL':<8} {'SCORE':>5} {'PRICE':>8} {'RVOL':>6} {'VOLUME':>12} {'AVG20':>12} {'ATR%':>7} {'CHG%':>7} {'VOL CHG%':>9} {'FLOAT':>12}")
    print("-" * 112)
    for rank, result in enumerate(results, start=1):
        stock = result.stock
        print(
            f"{rank:>2}  {stock.symbol:<8} {result.score:>5} ${stock.price:>7.2f} "
            f"{stock.rvol:>6.2f} {stock.current_volume:>12,} "
            f"{stock.avg_volume_20d:>12,} {stock.atr_percent:>6.2f}% "
            f"{stock.latest_percent_change:>6.2f}% {stock.volume_percent_change:>8.2f}% {stock.float_shares:>12,}"
        )


if __name__ == "__main__":
    main()
