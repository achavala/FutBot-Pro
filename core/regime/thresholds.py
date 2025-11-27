from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrendThresholds:
    adx_trending_min: float = 20.0
    adx_strong_trend_min: float = 30.0
    slope_up_min: float = 0.05
    slope_down_max: float = -0.05
    slope_flat_abs_max: float = 0.03
    r2_min_for_trend: float = 0.5


@dataclass(frozen=True)
class HurstThresholds:
    hurst_mean_reversion_max: float = 0.45
    hurst_trend_min: float = 0.55


@dataclass(frozen=True)
class VolatilityThresholds:
    atr_pct_low_max: float = 1.0
    atr_pct_medium_max: float = 2.0


@dataclass(frozen=True)
class VwapThresholds:
    vwap_dev_reversion_max: float = 0.5
    vwap_dev_extended_min: float = 1.5


@dataclass(frozen=True)
class FvgThresholds:
    max_age_bars: int = 20
    min_relative_size: float = 0.25


@dataclass(frozen=True)
class ConfidenceWeights:
    base: float = 0.5
    weight_adx_strong: float = 0.15
    weight_hurst_strong: float = 0.15
    weight_r2_strong: float = 0.1
    weight_vol_bucket: float = 0.1
    weight_fvg_alignment: float = 0.1


@dataclass(frozen=True)
class RegimeThresholds:
    trend: TrendThresholds = TrendThresholds()
    hurst: HurstThresholds = HurstThresholds()
    volatility: VolatilityThresholds = VolatilityThresholds()
    vwap: VwapThresholds = VwapThresholds()
    fvg: FvgThresholds = FvgThresholds()
    confidence: ConfidenceWeights = ConfidenceWeights()


DEFAULT_THRESHOLDS = RegimeThresholds()

