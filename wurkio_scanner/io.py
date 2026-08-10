from __future__ import annotations

import csv
import json
from pathlib import Path

from .models import FilterConfig, StockSnapshot


def load_config(path: str | Path) -> FilterConfig:
    with Path(path).open(encoding="utf-8") as file:
        return FilterConfig(**json.load(file))


def load_stocks(path: str | Path) -> list[StockSnapshot]:
    stocks: list[StockSnapshot] = []
    with Path(path).open(newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        required = {
            "symbol", "price", "current_volume", "avg_volume_5d",
            "avg_volume_20d", "atr_14d", "latest_percent_change", "float_shares",
        }
        missing = required.difference(reader.fieldnames or ())
        if missing:
            raise ValueError(f"CSV is missing columns: {', '.join(sorted(missing))}")
        for line_number, row in enumerate(reader, start=2):
            try:
                stock = StockSnapshot(
                    symbol=row["symbol"].strip().upper(),
                    price=float(row["price"]),
                    current_volume=int(float(row["current_volume"])),
                    avg_volume_20d=int(float(row["avg_volume_20d"])),
                    atr_14d=float(row["atr_14d"]),
                    avg_volume_5d=int(float(row["avg_volume_5d"])),
                    latest_percent_change=float(row["latest_percent_change"]),
                    float_shares=int(float(row["float_shares"])),
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid market data on CSV line {line_number}: {exc}") from exc
            nonnegative = (stock.price, stock.current_volume, stock.avg_volume_5d, stock.avg_volume_20d, stock.atr_14d, stock.float_shares)
            if not stock.symbol or min(nonnegative) < 0:
                raise ValueError(f"Invalid market data on CSV line {line_number}")
            stocks.append(stock)
    return stocks
