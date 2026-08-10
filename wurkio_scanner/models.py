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

    @property
    def rvol(self) -> float:
        """Five-day relative volume, matching the supplied scanner screenshots."""
        return self.current_volume / self.avg_volume_5d if self.avg_volume_5d else 0.0

    @property
    def atr_percent(self) -> float:
        return (self.atr_14d / self.price * 100) if self.price else 0.0

    @property
    def volume_percent_change(self) -> float:
        """Percent difference between current volume and 20-day average volume."""
        if not self.avg_volume_20d:
            return 0.0
        return (self.current_volume - self.avg_volume_20d) / self.avg_volume_20d * 100


@dataclass(frozen=True)
class FilterConfig:
    """A null threshold disables that filter."""

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

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if value is not None and value < 0 and field.name != "latest_percent_change_min":
                raise ValueError(f"{field.name} cannot be negative")
        for low_name, high_name in (("price_min", "price_max"), ("atr_percent_min", "atr_percent_max"), ("float_min", "float_max")):
            low, high = getattr(self, low_name), getattr(self, high_name)
            if low is not None and high is not None and high < low:
                raise ValueError(f"{low_name}/{high_name} range is invalid")
