from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .models import FilterConfig, StockSnapshot


@dataclass(frozen=True)
class FilterEvaluation:
    name: str
    actual: str
    requirement: str
    passed: bool
    required: bool = True


@dataclass(frozen=True)
class ScoreComponent:
    category: str
    earned: int
    available: int
    explanation: str


@dataclass(frozen=True)
class ScanResult:
    stock: StockSnapshot
    score: int
    passed_filters: tuple[str, ...] = ()
    evaluations: tuple[FilterEvaluation, ...] = ()
    score_breakdown: tuple[ScoreComponent, ...] = ()


class Scanner:
    """Apply hard eligibility filters, then score qualifying stocks."""

    def __init__(self, config: FilterConfig) -> None:
        self.config = config

    def evaluate_required_filters(self, stock: StockSnapshot) -> tuple[FilterEvaluation, ...]:
        c = self.config
        evaluations: list[FilterEvaluation] = []

        def minimum(name: str, value: float, threshold: float | None, actual: str, unit: str = "") -> None:
            if threshold is not None:
                evaluations.append(FilterEvaluation(name, actual, f">= {self._display(threshold)}{unit}", value >= threshold))

        def maximum(name: str, value: float, threshold: float | None, actual: str, unit: str = "") -> None:
            if threshold is not None:
                evaluations.append(FilterEvaluation(name, actual, f"<= {self._display(threshold)}{unit}", value <= threshold))

        def optional_minimum(name: str, value: float | None, threshold: float | None, unit: str = "") -> None:
            if threshold is not None:
                actual = "N/A" if value is None else f"{value:,.2f}{unit}"
                evaluations.append(FilterEvaluation(name, actual, f">= {threshold:,.2f}{unit}", value is not None and value >= threshold))

        def optional_maximum(name: str, value: float | None, threshold: float | None, unit: str = "") -> None:
            if threshold is not None:
                actual = "N/A" if value is None else f"{value:,.2f}{unit}"
                evaluations.append(FilterEvaluation(name, actual, f"<= {threshold:,.2f}{unit}", value is not None and value <= threshold))

        def boolean_target(name: str, value: bool | None, target: bool | None) -> None:
            if target is not None:
                actual = "N/A" if value is None else ("Yes" if value else "No")
                evaluations.append(FilterEvaluation(name, actual, "Yes" if target else "No", value is not None and value == target))

        minimum("Price minimum", stock.price, c.price_min, f"${stock.price:.2f}", "")
        maximum("Price maximum", stock.price, c.price_max, f"${stock.price:.2f}", "")
        minimum("RVOL", stock.rvol, c.rvol_min, f"{stock.rvol:.2f}")
        minimum("Current Volume", stock.current_volume, c.current_volume_min, f"{stock.current_volume:,}")
        minimum("5D Average Volume", stock.avg_volume_5d, c.avg_volume_5d_min, f"{stock.avg_volume_5d:,}")
        minimum("20D Average Volume", stock.avg_volume_20d, c.avg_volume_20d_min, f"{stock.avg_volume_20d:,}")
        minimum("ATR% minimum", stock.atr_percent, c.atr_percent_min, f"{stock.atr_percent:.2f}%", "%")
        maximum("ATR% maximum", stock.atr_percent, c.atr_percent_max, f"{stock.atr_percent:.2f}%", "%")
        minimum("Daily % Change", stock.latest_percent_change, c.latest_percent_change_min, f"{stock.latest_percent_change:.2f}%", "%")
        minimum("Volume Change %", stock.volume_percent_change, c.volume_percent_change_min, f"{stock.volume_percent_change:.2f}%", "%")
        minimum("Float minimum", stock.float_shares, c.float_min, f"{stock.float_shares:,}")
        maximum("Float maximum", stock.float_shares, c.float_max, f"{stock.float_shares:,}")
        boolean_target("Above VWAP", stock.above_vwap, c.above_vwap)
        boolean_target("Above 20 SMA", stock.above_sma_20, c.above_sma_20)
        boolean_target("Above 50 SMA", stock.above_sma_50, c.above_sma_50)
        boolean_target("Above 200 SMA", stock.above_sma_200, c.above_sma_200)
        optional_minimum("Gap %", stock.gap_percent, c.gap_percent_min, "%")
        optional_minimum("Premarket % Change", stock.premarket_percent_change, c.premarket_percent_change_min, "%")
        optional_minimum("Premarket Volume", stock.premarket_volume, c.premarket_volume_min)
        optional_minimum("Market Cap minimum", stock.market_cap, c.market_cap_min, "")
        optional_maximum("Market Cap maximum", stock.market_cap, c.market_cap_max, "")
        optional_minimum("Short Float % minimum", stock.short_float_percent, c.short_float_percent_min, "%")
        optional_maximum("Short Float % maximum", stock.short_float_percent, c.short_float_percent_max, "%")
        optional_minimum("52W Range Position", stock.week_52_position, c.week_52_position_min, "%")
        optional_minimum("Day Range Position", stock.day_range_position, c.day_range_position_min, "%")
        optional_minimum("Dollar Volume", stock.dollar_volume, c.dollar_volume_min)
        optional_minimum("Float Rotation", stock.float_rotation, c.float_rotation_min, "x")
        optional_minimum("Distance From HOD", stock.distance_from_high_percent, c.distance_from_high_percent_min, "%")
        return tuple(evaluations)

    def score_breakdown(self, stock: StockSnapshot) -> tuple[ScoreComponent, ...]:
        c = self.config
        momentum_target = c.latest_percent_change_min if c.latest_percent_change_min is not None else 5.0
        rvol_target = c.rvol_min if c.rvol_min is not None else 2.0
        atr_target = c.atr_percent_min if c.atr_percent_min is not None else 5.0
        volume_target = c.current_volume_min if c.current_volume_min is not None else 1_000_000
        avg_target = c.avg_volume_20d_min if c.avg_volume_20d_min is not None else 1_000_000
        float_target = c.float_max if c.float_max is not None else 10_000_000

        momentum = self._points_above(stock.latest_percent_change, momentum_target, 25)
        relative_volume = self._points_above(stock.rvol, rvol_target, 20)
        liquidity_strength = (self._strength(stock.current_volume, volume_target) + self._strength(stock.avg_volume_20d, avg_target)) / 2
        liquidity = round(20 * liquidity_strength)
        volatility = self._points_above(stock.atr_percent, atr_target, 15)
        float_points = 10 if stock.float_shares <= float_target else max(0, round(10 * float_target / stock.float_shares))
        price_fit = round(self._range_score(stock.price, c.price_min, c.price_max) / 10)
        return (
            ScoreComponent("Momentum", momentum, 25, f"{stock.latest_percent_change:+.2f}% vs {momentum_target:.2f}% target"),
            ScoreComponent("Relative Volume", relative_volume, 20, f"{stock.rvol:.2f} vs {rvol_target:.2f} target"),
            ScoreComponent("Liquidity", liquidity, 20, f"{stock.current_volume:,} current / {stock.avg_volume_20d:,} avg"),
            ScoreComponent("Volatility", volatility, 15, f"{stock.atr_percent:.2f}% ATRP vs {atr_target:.2f}% target"),
            ScoreComponent("Float", float_points, 10, f"{stock.float_shares:,} shares vs <= {float_target:,.0f} target"),
            ScoreComponent("Price Fit", price_fit, 10, f"${stock.price:.2f} within configured range"),
        )

    def score_evaluations(self, stock: StockSnapshot) -> tuple[FilterEvaluation, ...]:
        c = self.config
        targets = (
            FilterEvaluation("Momentum score target", f"{stock.latest_percent_change:.2f}%", f">= {(c.latest_percent_change_min or 5):.2f}%", stock.latest_percent_change >= (c.latest_percent_change_min or 5), False),
            FilterEvaluation("RVOL score target", f"{stock.rvol:.2f}", f">= {(c.rvol_min or 2):.2f}", stock.rvol >= (c.rvol_min or 2), False),
            FilterEvaluation("Liquidity score target", f"{stock.current_volume:,}", ">= 1,000,000", stock.current_volume >= 1_000_000, False),
            FilterEvaluation("Volatility score target", f"{stock.atr_percent:.2f}%", f">= {(c.atr_percent_min or 5):.2f}%", stock.atr_percent >= (c.atr_percent_min or 5), False),
            FilterEvaluation("Low-float score target", f"{stock.float_shares:,}", f"<= {(c.float_max or 10_000_000):,.0f}", stock.float_shares <= (c.float_max or 10_000_000), False),
        )
        return targets

    def passes(self, stock: StockSnapshot) -> bool:
        return all(evaluation.passed for evaluation in self.evaluate_required_filters(stock))

    def passed_filter_names(self, stock: StockSnapshot) -> tuple[str, ...]:
        return tuple(item.name for item in self.evaluate_required_filters(stock) if item.passed)

    def score(self, stock: StockSnapshot) -> int:
        return sum(component.earned for component in self.score_breakdown(stock))

    def scan(self, stocks: Iterable[StockSnapshot]) -> list[ScanResult]:
        results: list[ScanResult] = []
        for stock in stocks:
            required = self.evaluate_required_filters(stock)
            if not all(item.passed for item in required):
                continue
            breakdown = self.score_breakdown(stock)
            evaluations = required + self.score_evaluations(stock)
            results.append(ScanResult(
                stock=stock,
                score=sum(item.earned for item in breakdown),
                passed_filters=tuple(item.name for item in required),
                evaluations=evaluations,
                score_breakdown=breakdown,
            ))
        return sorted(results, key=lambda result: (-result.score, -result.stock.rvol, result.stock.symbol))

    @staticmethod
    def _points_above(value: float, target: float, available: int) -> int:
        return round(available * Scanner._strength(value, target))

    @staticmethod
    def _strength(value: float, target: float) -> float:
        if target <= 0:
            return 1.0
        return min(1.0, max(0.0, value / (target * 2)))

    @staticmethod
    def _display(value: float) -> str:
        return f"{value:,.2f}" if isinstance(value, float) and not value.is_integer() else f"{value:,.0f}"

    @staticmethod
    def _range_score(value: float, minimum: float | None, maximum: float | None) -> float:
        if minimum is None and maximum is None:
            return 100.0
        if minimum is None:
            return 100.0 if value <= maximum else 0.0
        if maximum is None:
            return min(100.0, 50.0 * value / minimum) if minimum else 100.0
        if maximum == minimum:
            return 100.0
        midpoint = (minimum + maximum) / 2
        half_range = (maximum - minimum) / 2
        return max(50.0, 100.0 - 50.0 * abs(value - midpoint) / half_range)
