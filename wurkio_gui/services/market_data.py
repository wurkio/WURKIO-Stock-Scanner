from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    bid: float | None
    ask: float | None
    volume: int | None
    timestamp: datetime
    source: str


@dataclass(frozen=True)
class Candle:
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@runtime_checkable
class MarketDataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str, at: datetime | None = None) -> Quote:
        ...

    def get_candles(self, symbol: str, start: datetime, end: datetime) -> list[Candle]:
        ...


class SimulatedMarketDataProvider:
    """Deterministic feed for tests and demos. Never represented as live data."""

    name = "simulated"

    def __init__(self, prices: dict[str, float] | None = None) -> None:
        self.prices = prices or {}

    def get_quote(self, symbol: str, at: datetime | None = None) -> Quote:
        timestamp = at or datetime.now().astimezone()
        base = self.prices.get(symbol.upper(), 10.0)
        minutes = timestamp.minute + timestamp.hour * 60
        price = base * (1 + ((minutes % 17) - 8) / 1000)
        return Quote(symbol.upper(), round(price, 4), round(price - 0.01, 4), round(price + 0.01, 4), 1_000_000, timestamp, self.name)

    def get_candles(self, symbol: str, start: datetime, end: datetime) -> list[Candle]:
        candles: list[Candle] = []
        current = start
        while current <= end:
            quote = self.get_quote(symbol, current)
            price = quote.price
            candles.append(Candle(symbol.upper(), current, price, price * 1.003, price * 0.997, price, 10_000))
            current += timedelta(minutes=1)
        return candles
