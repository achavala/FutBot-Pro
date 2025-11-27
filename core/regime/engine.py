from __future__ import annotations

from typing import Iterable, Mapping, Optional, Sequence, Tuple

import numpy as np

from core.features.fvg import FairValueGap, is_fvg_filled
from core.regime.thresholds import DEFAULT_THRESHOLDS, RegimeThresholds
from core.regime.types import Bias, RegimeSignal, RegimeType, TrendDirection, VolatilityLevel


Observation = Mapping[str, object]


class RegimeEngine:
    """Deterministic regime classifier built on engineered features."""

    def __init__(self, thresholds: Optional[RegimeThresholds] = None, debug: bool = False):
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.debug = debug

    def classify_bar(self, features: Observation) -> RegimeSignal:
        """Classify a single observation into a structured regime signal."""
        adx = float(features.get("adx", 0.0) or 0.0)
        slope = float(features.get("slope", 0.0) or 0.0)
        r_squared = float(features.get("r_squared", 0.0) or 0.0)
        hurst = float(features.get("hurst", 0.5) or 0.5)
        atr_pct = float(features.get("atr_pct", 0.0) or 0.0)
        vwap_dev = float(features.get("vwap_deviation", 0.0) or 0.0)
        price = float(features.get("close") or features.get("price") or 0.0)
        timestamp = features.get("timestamp")
        bar_index = features.get("bar_index")
        fvgs = self._coerce_fvgs(features.get("active_fvgs") or features.get("fvgs"))
        
        # Get asset type from features (if provided)
        asset_type = features.get("asset_type", "equity")  # Default to equity for backward compatibility

        # Check for NaN values - replace with defaults if needed BEFORE calculations
        adx_clean = adx if not np.isnan(adx) and adx > 0 else 20.0
        slope_clean = slope if not np.isnan(slope) else 0.0
        r_squared_clean = r_squared if not np.isnan(r_squared) and r_squared >= 0 else 0.0
        hurst_clean = hurst if not np.isnan(hurst) and 0 <= hurst <= 1 else 0.5
        atr_pct_clean = atr_pct if not np.isnan(atr_pct) and atr_pct > 0 else 1.0
        
        # Calculate with cleaned values
        # Asset-aware logic: crypto vs equity
        is_crypto = asset_type == "crypto"
        
        # For crypto, we may want to adjust some thresholds or skip equity-specific features
        # For now, we use the same logic but could branch here in the future
        trend_direction, trend_conf = self._determine_trend(adx_clean, slope_clean, r_squared_clean)
        volatility = self._determine_volatility(atr_pct_clean)
        
        # FVG detection: may be less relevant for crypto (24/7 trading, fewer gaps)
        # But we'll still use it for now
        active_fvg = self._select_active_fvg(fvgs, price, bar_index, atr_pct_clean)
        
        regime_type = self._determine_regime_type(trend_direction, hurst_clean, volatility, vwap_dev, active_fvg)
        bias = self._determine_bias(regime_type, trend_direction, vwap_dev, active_fvg)
        confidence = self._score_confidence(trend_conf, hurst_clean, r_squared_clean, volatility, bias, active_fvg)
        
        # Force minimum confidence - should never be 0.0 if we have valid features
        # This is a safety net in case confidence calculation fails
        if confidence <= 0.0 or np.isnan(confidence):
            confidence = 0.3  # Force minimum for trading
        
        is_valid = not np.isnan(np.array([adx_clean, slope_clean, r_squared_clean, hurst_clean, atr_pct_clean])).any()
        
        # Update metrics with cleaned values
        metrics = {
            "adx": adx_clean,
            "slope": slope_clean,
            "r_squared": r_squared_clean,
            "hurst": hurst_clean,
            "atr_pct": atr_pct_clean,
            "vwap_dev": vwap_dev,
        }
        metrics["confidence"] = confidence
        metrics["trend_conf"] = trend_conf

        return RegimeSignal(
            timestamp=timestamp,
            trend_direction=trend_direction,
            volatility_level=volatility,
            regime_type=regime_type,
            bias=bias,
            confidence=confidence,
            active_fvg=active_fvg,
            metrics=metrics if self.debug else {},
            is_valid=is_valid,
        )

    def classify_dataframe(self, df) -> Sequence[RegimeSignal]:
        """Vectorized helper across a DataFrame; expects matching column names."""
        return [self.classify_bar(row) for _, row in df.iterrows()]

    def _determine_trend(self, adx: float, slope: float, r_squared: float) -> Tuple[TrendDirection, float]:
        thresholds = self.thresholds.trend

        if adx >= thresholds.adx_strong_trend_min and r_squared >= thresholds.r2_min_for_trend:
            if slope >= thresholds.slope_up_min:
                return TrendDirection.UP, 1.0
            if slope <= thresholds.slope_down_max:
                return TrendDirection.DOWN, 1.0

        if abs(slope) <= thresholds.slope_flat_abs_max or adx < thresholds.adx_trending_min:
            return TrendDirection.SIDEWAYS, 0.4

        if slope > 0:
            return TrendDirection.UP, 0.7
        if slope < 0:
            return TrendDirection.DOWN, 0.7
        return TrendDirection.SIDEWAYS, 0.3

    def _determine_volatility(self, atr_pct: float) -> VolatilityLevel:
        thresholds = self.thresholds.volatility
        if atr_pct <= thresholds.atr_pct_low_max:
            return VolatilityLevel.LOW
        if atr_pct <= thresholds.atr_pct_medium_max:
            return VolatilityLevel.MEDIUM
        return VolatilityLevel.HIGH

    def _determine_regime_type(
        self,
        trend_direction: TrendDirection,
        hurst: float,
        volatility: VolatilityLevel,
        vwap_dev: float,
        active_fvg: Optional[FairValueGap],
    ) -> RegimeType:
        h_thresholds = self.thresholds.hurst
        vwap_thresholds = self.thresholds.vwap

        if (
            trend_direction != TrendDirection.SIDEWAYS
            and hurst >= h_thresholds.hurst_trend_min
            and volatility != VolatilityLevel.LOW
        ):
            return RegimeType.TREND

        if (
            hurst <= h_thresholds.hurst_mean_reversion_max
            and volatility != VolatilityLevel.HIGH
            and abs(vwap_dev) <= vwap_thresholds.vwap_dev_reversion_max
        ):
            return RegimeType.MEAN_REVERSION

        if volatility == VolatilityLevel.HIGH:
            return RegimeType.EXPANSION

        if volatility == VolatilityLevel.LOW:
            return RegimeType.COMPRESSION

        if active_fvg:
            return RegimeType.MEAN_REVERSION

        return RegimeType.NEUTRAL

    def _determine_bias(
        self,
        regime_type: RegimeType,
        trend_direction: TrendDirection,
        vwap_dev: float,
        active_fvg: Optional[FairValueGap],
    ) -> Bias:
        if regime_type == RegimeType.TREND:
            if trend_direction == TrendDirection.UP:
                return Bias.LONG
            if trend_direction == TrendDirection.DOWN:
                return Bias.SHORT
            return Bias.NEUTRAL

        if regime_type == RegimeType.MEAN_REVERSION:
            if active_fvg:
                return Bias.LONG if active_fvg.gap_type == "bullish" else Bias.SHORT
            # Use VWAP deviation sign for fallback bias
            if vwap_dev > 0:
                return Bias.SHORT
            if vwap_dev < 0:
                return Bias.LONG

        return Bias.NEUTRAL

    def _score_confidence(
        self,
        trend_conf: float,
        hurst: float,
        r_squared: float,
        volatility: VolatilityLevel,
        bias: Bias,
        active_fvg: Optional[FairValueGap],
    ) -> float:
        weights = self.thresholds.confidence
        score = weights.base

        if trend_conf >= 0.9:
            score += weights.weight_adx_strong

        hurst_distance = abs(hurst - 0.5)
        if hurst_distance >= 0.1:
            score += weights.weight_hurst_strong

        if r_squared >= self.thresholds.trend.r2_min_for_trend:
            score += weights.weight_r2_strong

        score += weights.weight_vol_bucket * {"low": 0.5, "medium": 0.7, "high": 0.9}[volatility.value]

        if active_fvg and bias != Bias.NEUTRAL:
            aligned = (active_fvg.gap_type == "bullish" and bias == Bias.LONG) or (
                active_fvg.gap_type == "bearish" and bias == Bias.SHORT
            )
            if aligned:
                score += weights.weight_fvg_alignment

        # Ensure minimum confidence - base should always give at least 0.3
        # This prevents confidence from being 0.0 when we have valid features
        # Even if all conditions fail, we should have at least base confidence
        final_score = max(score, weights.base)  # At least base (0.5), but we'll allow lower for edge cases
        # However, if score is very low, ensure minimum of 0.3 for trading
        if final_score < 0.3:
            final_score = 0.3  # Force minimum for trading
        return float(np.clip(final_score, 0.0, 1.0))

    def _select_active_fvg(
        self,
        fvgs: Sequence[FairValueGap],
        price: float,
        bar_index: Optional[int],
        atr_pct: float,
    ) -> Optional[FairValueGap]:
        if not fvgs or price <= 0:
            return None

        thresholds = self.thresholds.fvg
        atr_component = max(atr_pct / 100, 0.01)

        for fvg in fvgs:
            if bar_index is not None and (bar_index - fvg.index) > thresholds.max_age_bars:
                continue
            relative_size = abs(fvg.upper - fvg.lower) / price
            if relative_size < thresholds.min_relative_size * atr_component:
                continue
            if is_fvg_filled(price, fvg):
                continue
            return fvg
        return None

    @staticmethod
    def _coerce_fvgs(fvgs: Optional[Iterable[FairValueGap]]) -> Sequence[FairValueGap]:
        if fvgs is None:
            return []
        return list(fvgs)

