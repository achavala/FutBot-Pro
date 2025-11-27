from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from core.features.fvg import FairValueGap


class TrendDirection(str, Enum):
    """Enumerated trend states."""

    UP = "up"
    DOWN = "down"
    SIDEWAYS = "sideways"


class VolatilityLevel(str, Enum):
    """Enumerated volatility buckets."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RegimeType(str, Enum):
    """Top-level regime classifications."""

    TREND = "trend"
    MEAN_REVERSION = "mean_reversion"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    NEUTRAL = "neutral"


class Bias(str, Enum):
    """Directional bias for agents."""

    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class RegimeSignal:
    """Snapshot of the current regime analysis."""

    timestamp: Optional[datetime]
    trend_direction: TrendDirection
    volatility_level: VolatilityLevel
    regime_type: RegimeType
    bias: Bias
    confidence: float
    active_fvg: Optional[FairValueGap] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    is_valid: bool = True

    @property
    def is_trending(self) -> bool:
        return self.regime_type == RegimeType.TREND

    @property
    def is_mean_reversion(self) -> bool:
        return self.regime_type == RegimeType.MEAN_REVERSION

    @property
    def is_high_volatility(self) -> bool:
        return self.volatility_level == VolatilityLevel.HIGH

