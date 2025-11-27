from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptationThresholds:
    """Configuration for policy adaptation bounds and decay settings."""

    # Agent weight bounds
    min_agent_weight: float = 0.1
    max_agent_weight: float = 3.0
    base_agent_weight: float = 1.0

    # Regime weight bounds
    min_regime_weight: float = 0.5
    max_regime_weight: float = 2.0

    # Volatility weight bounds
    min_volatility_weight: float = 0.5
    max_volatility_weight: float = 1.5

    # Structural weight bounds
    min_structure_weight: float = 0.5
    max_structure_weight: float = 2.0

    # Adaptation rates
    agent_adapt_rate_short: float = 0.1
    agent_adapt_rate_long: float = 0.05
    regime_adapt_rate: float = 0.08
    volatility_adapt_rate: float = 0.06
    structure_adapt_rate: float = 0.1

    # Smoothing
    weight_smoothing_alpha: float = 0.3

    # Cooldown
    cooldown_bars: int = 10
    cooldown_threshold_pct: float = 0.15

    # Change threshold (ignore tiny updates)
    min_change_threshold: float = 0.005

    # Idle decay
    idle_decay_rate: float = 0.99
    idle_threshold_bars: int = 50

    # EMA decay for fitness
    fitness_decay_short: float = 0.90
    fitness_decay_long: float = 0.98


DEFAULT_THRESHOLDS = AdaptationThresholds()

