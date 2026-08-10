from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class StockSnapshot:
    symbol: str
    price: float
    current_volume: int
    avg_volume_20d: int
    atr_14d: float
    avg_volume_5d: int
    latest_percent_change: float
    float_shares: int
    open_price: float | None = None
    previous_close: float | None = None
    day_high: float | None = None
    day_low: float | None = None
    vwap: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    premarket_price: float | None = None
    premarket_volume: int | None = None
    market_cap: float | None = None
    short_float_percent: float | None = None
    week_52_high: float | None = None
    week_52_low: float | None = None

    @staticmethod
    def _percent_change(value: float | None, reference: float | None) -> float | None:
        if value is None or reference in (None, 0):
            return None
        return (value - reference) / reference * 100

    @staticmethod
    def _range_position(value: float, low: float | None, high: float | None) -> float | None:
        if low is None or high is None or high <= low:
            return None
        return (value - low) / (high - low) * 100

    @property
    def rvol(self) -> float:
        return self.current_volume / self.avg_volume_5d if self.avg_volume_5d else 0.0

    @property
    def atr_percent(self) -> float:
        return (self.atr_14d / self.price * 100) if self.price else 0.0

    @property
    def volume_percent_change(self) -> float:
        return ((self.current_volume - self.avg_volume_20d) / self.avg_volume_20d * 100) if self.avg_volume_20d else 0.0

    @property
    def gap_percent(self) -> float | None:
        return self._percent_change(self.open_price, self.previous_close)

    @property
    def premarket_percent_change(self) -> float | None:
        return self._percent_change(self.premarket_price, self.previous_close)

    @property
    def distance_from_vwap_percent(self) -> float | None:
        return self._percent_change(self.price, self.vwap)

    @property
    def above_vwap(self) -> bool | None:
        return None if self.vwap is None else self.price > self.vwap

    @property
    def above_sma_20(self) -> bool | None:
        return None if self.sma_20 is None else self.price > self.sma_20

    @property
    def above_sma_50(self) -> bool | None:
        return None if self.sma_50 is None else self.price > self.sma_50

    @property
    def above_sma_200(self) -> bool | None:
        return None if self.sma_200 is None else self.price > self.sma_200

    @property
    def dollar_volume(self) -> float:
        return self.price * self.current_volume

    @property
    def float_rotation(self) -> float | None:
        return self.current_volume / self.float_shares if self.float_shares else None

    @property
    def distance_from_high_percent(self) -> float | None:
        return self._percent_change(self.price, self.day_high)

    @property
    def distance_from_low_percent(self) -> float | None:
        return self._percent_change(self.price, self.day_low)

    @property
    def day_range_position(self) -> float | None:
        return self._range_position(self.price, self.day_low, self.day_high)

    @property
    def week_52_position(self) -> float | None:
        return self._range_position(self.price, self.week_52_low, self.week_52_high)


@dataclass(frozen=True)
class FilterConfig:
    """A null threshold disables that filter; context does not affect scoring."""

    price_min: float | None = 1.0
    price_max: float | None = 20.0
    rvol_min: float | None = 1.5
    current_volume_min: int | None = 200_000
    avg_volume_5d_min: int | None = None
    avg_volume_20d_min: int | None = 1_000_000
    atr_percent_min: float | None = 5.0
    atr_percent_max: float | None = None
    latest_percent_change_min: float | None = None
    volume_percent_change_min: float | None = None
    float_min: int | None = None
    float_max: int | None = None
    above_vwap: bool | None = None
    above_sma_20: bool | None = None
    above_sma_50: bool | None = None
    above_sma_200: bool | None = None
    gap_percent_min: float | None = None
    premarket_percent_change_min: float | None = None
    premarket_volume_min: int | None = None
    market_cap_min: float | None = None
    market_cap_max: float | None = None
    short_float_percent_min: float | None = None
    short_float_percent_max: float | None = None
    week_52_position_min: float | None = None
    day_range_position_min: float | None = None
    dollar_volume_min: float | None = None
    float_rotation_min: float | None = None
    distance_from_high_percent_min: float | None = None

    def __post_init__(self) -> None:
        negative_allowed = {
            "latest_percent_change_min", "gap_percent_min", "premarket_percent_change_min",
            "distance_from_high_percent_min",
        }
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None and not isinstance(value, bool) and value < 0 and field.name not in negative_allowed:
                raise ValueError(f"{field.name} cannot be negative")
        ranges = (
            ("price_min", "price_max"), ("atr_percent_min", "atr_percent_max"),
            ("float_min", "float_max"), ("market_cap_min", "market_cap_max"),
            ("short_float_percent_min", "short_float_percent_max"),
        )
        for low_name, high_name in ranges:
            low, high = getattr(self, low_name), getattr(self, high_name)
            if low is not None and high is not None and high < low:
                raise ValueError(f"{low_name}/{high_name} range is invalid")
