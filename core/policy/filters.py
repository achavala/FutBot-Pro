from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from core.agents.base import TradeDirection, TradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, VolatilityLevel


@dataclass
class FilterConfig:
    """Configuration parameters for meta-policy filtering stage."""

    min_confidence: float = 0.5
    high_vol_confidence: float = 0.75
    blend_conflict_threshold: float = 0.05


def apply_filters(intents: Sequence[TradeIntent], signal: RegimeSignal, config: FilterConfig | None = None) -> List[TradeIntent]:
    cfg = config or FilterConfig()
    step = _confidence_filter(intents, cfg.min_confidence)
    step = _regime_filter(step, signal)
    step = _volatility_filter(step, signal, cfg)
    step = _direction_conflict_filter(step)
    return step


def _confidence_filter(intents: Sequence[TradeIntent], min_confidence: float) -> List[TradeIntent]:
    return [intent for intent in intents if intent.confidence >= min_confidence]


def _regime_filter(intents: Sequence[TradeIntent], signal: RegimeSignal) -> List[TradeIntent]:
    if not intents:
        return []

    results: List[TradeIntent] = []
    for intent in intents:
        if signal.regime_type == RegimeType.TREND:
            if signal.bias == Bias.LONG and intent.direction == TradeDirection.SHORT:
                continue
            if signal.bias == Bias.SHORT and intent.direction == TradeDirection.LONG:
                continue
        if signal.regime_type == RegimeType.MEAN_REVERSION and "trend" in intent.agent_name:
            continue
        results.append(intent)
    return results


def _volatility_filter(intents: Sequence[TradeIntent], signal: RegimeSignal, cfg: FilterConfig) -> List[TradeIntent]:
    if not intents:
        return []
    kept: List[TradeIntent] = []
    for intent in intents:
        if signal.volatility_level == VolatilityLevel.HIGH and "mean_reversion" in intent.agent_name:
            if intent.confidence < cfg.high_vol_confidence:
                continue
        if signal.volatility_level == VolatilityLevel.LOW and "volatility" in intent.agent_name:
            continue
        kept.append(intent)
    return kept


def _direction_conflict_filter(intents: Sequence[TradeIntent]) -> List[TradeIntent]:
    if not intents:
        return []
    long_intents = [i for i in intents if i.direction == TradeDirection.LONG]
    short_intents = [i for i in intents if i.direction == TradeDirection.SHORT]
    if long_intents and short_intents:
        best_long = max(long_intents, key=lambda i: i.confidence)
        best_short = max(short_intents, key=lambda i: i.confidence)
        return [best_long] if best_long.confidence >= best_short.confidence else [best_short]
    return list(intents)

