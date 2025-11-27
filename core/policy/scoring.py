from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Optional, Sequence

import numpy as np

from core.agents.base import TradeDirection, TradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, VolatilityLevel

if TYPE_CHECKING:
    from core.policy_adaptation.adaptor import PolicyAdaptor


AGENT_WEIGHTS: Dict[str, float] = {
    "trend_agent": 1.0,
    "mean_reversion_agent": 0.9,
    "volatility_agent": 0.8,
    "fvg_agent": 1.1,
}

REGIME_WEIGHTS: Dict[RegimeType, float] = {
    RegimeType.TREND: 1.2,
    RegimeType.MEAN_REVERSION: 1.2,
    RegimeType.COMPRESSION: 0.8,
    RegimeType.EXPANSION: 1.0,
    RegimeType.NEUTRAL: 1.0,
}

VOLATILITY_WEIGHTS: Dict[VolatilityLevel, float] = {
    VolatilityLevel.LOW: 1.0,
    VolatilityLevel.MEDIUM: 1.0,
    VolatilityLevel.HIGH: 0.9,
}

STRUCTURE_WEIGHTS: Dict[str, float] = {
    "aligned": 1.2,
    "conflict": 0.8,
    "none": 1.0,
}


@dataclass(frozen=True)
class ScoredIntent:
    intent: TradeIntent
    score: float
    position_delta: float


def score_intents(
    intents: Sequence[TradeIntent], signal: RegimeSignal, adaptor: Optional["PolicyAdaptor"] = None
) -> Sequence[ScoredIntent]:
    """Score intents using adaptive weights if adaptor provided, else static weights."""
    scored = []
    for intent in intents:
        direction = _direction_multiplier(intent.direction)
        position_delta = direction * intent.size
        structure_weight = _structure_weight(intent, signal, adaptor)
        agent_weight = adaptor.get_agent_weight(intent.agent_name) if adaptor else AGENT_WEIGHTS.get(intent.agent_name, 0.8)
        regime_weight = adaptor.get_regime_weight(signal.regime_type) if adaptor else REGIME_WEIGHTS.get(signal.regime_type, 1.0)
        volatility_weight = (
            adaptor.get_volatility_weight(signal.volatility_level) if adaptor else VOLATILITY_WEIGHTS.get(signal.volatility_level, 1.0)
        )
        score = intent.confidence * agent_weight * regime_weight * volatility_weight * structure_weight
        scored.append(ScoredIntent(intent=intent, score=float(score), position_delta=position_delta))
    return scored


def _structure_weight(intent: TradeIntent, signal: RegimeSignal, adaptor: Optional["PolicyAdaptor"] = None) -> float:
    """Compute structure weight, using adaptor if available."""
    if not signal.active_fvg:
        alignment_type = "none"
    elif (intent.direction == TradeDirection.LONG and signal.active_fvg.gap_type == "bullish") or (
        intent.direction == TradeDirection.SHORT and signal.active_fvg.gap_type == "bearish"
    ):
        alignment_type = "aligned"
    else:
        alignment_type = "conflict"

    if adaptor:
        return adaptor.get_structure_weight(alignment_type)
    return STRUCTURE_WEIGHTS.get(alignment_type, 1.0)


def _direction_multiplier(direction: TradeDirection) -> float:
    if direction == TradeDirection.LONG:
        return 1.0
    if direction == TradeDirection.SHORT:
        return -1.0
    return 0.0

