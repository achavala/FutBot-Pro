from __future__ import annotations

from typing import Dict

from core.policy_adaptation.stats import clamp, ema_smooth, percentage_change
from core.policy_adaptation.thresholds import AdaptationThresholds
from core.regime.types import RegimeType, VolatilityLevel
from core.reward.memory import FitnessSnapshot, RollingMemoryStore


def update_agent_weight(
    agent_name: str,
    current_weight: float,
    fitness: FitnessSnapshot,
    thresholds: AdaptationThresholds,
    agent_signal_counts: Dict[str, int],  # Maps agent_name -> last_bar_when_signaled
    bar_count: int,
) -> float:
    """Update agent weight based on short and long-term fitness."""
    base = thresholds.base_agent_weight
    k1 = thresholds.agent_adapt_rate_short
    k2 = thresholds.agent_adapt_rate_long

    # Compute weight adjustment from fitness
    fitness_adjustment = 1.0 + k1 * fitness.short_term + k2 * fitness.long_term
    new_weight = base * fitness_adjustment

    # Apply idle decay if agent hasn't signaled recently
    last_signal_bar = agent_signal_counts.get(agent_name, 0)
    if last_signal_bar == 0:
        # Agent never signaled - don't apply decay, just use bounds
        pass
    else:
        bars_since_signal = bar_count - last_signal_bar
        if bars_since_signal > thresholds.idle_threshold_bars:
            decay_exponent = bars_since_signal - thresholds.idle_threshold_bars
            new_weight = new_weight * (thresholds.idle_decay_rate ** decay_exponent)

    # Clamp to bounds
    new_weight = clamp(new_weight, thresholds.min_agent_weight, thresholds.max_agent_weight)

    # Smooth with current weight
    smoothed = ema_smooth(current_weight, new_weight, thresholds.weight_smoothing_alpha)

    return smoothed


def update_regime_weight(
    regime: RegimeType,
    current_weight: float,
    regime_fitness: float,
    thresholds: AdaptationThresholds,
) -> float:
    """Update regime weight based on regime-specific performance."""
    adapt_rate = thresholds.regime_adapt_rate
    adjustment = 1.0 + adapt_rate * regime_fitness
    new_weight = current_weight * adjustment
    new_weight = clamp(new_weight, thresholds.min_regime_weight, thresholds.max_regime_weight)
    smoothed = ema_smooth(current_weight, new_weight, thresholds.weight_smoothing_alpha)
    return smoothed


def update_volatility_weight(
    level: VolatilityLevel,
    current_weight: float,
    vol_fitness: float,
    thresholds: AdaptationThresholds,
) -> float:
    """Update volatility weight based on volatility-conditioned performance."""
    adapt_rate = thresholds.volatility_adapt_rate
    adjustment = 1.0 + adapt_rate * vol_fitness
    new_weight = current_weight * adjustment
    new_weight = clamp(new_weight, thresholds.min_volatility_weight, thresholds.max_volatility_weight)
    smoothed = ema_smooth(current_weight, new_weight, thresholds.weight_smoothing_alpha)
    return smoothed


def update_structural_weight(
    alignment_type: str,
    current_weight: float,
    success_rate: float,
    thresholds: AdaptationThresholds,
) -> float:
    """Update structural weight (FVG/VWAP alignment) based on success rate."""
    adapt_rate = thresholds.structure_adapt_rate
    if alignment_type == "aligned":
        adjustment = 1.0 + adapt_rate * success_rate
    else:  # conflict
        adjustment = 1.0 - adapt_rate * (1.0 - success_rate)
    new_weight = current_weight * adjustment
    new_weight = clamp(new_weight, thresholds.min_structure_weight, thresholds.max_structure_weight)
    smoothed = ema_smooth(current_weight, new_weight, thresholds.weight_smoothing_alpha)
    return smoothed


def should_apply_cooldown(
    old_weight: float,
    new_weight: float,
    thresholds: AdaptationThresholds,
    last_update_bar: int,
    current_bar: int,
) -> bool:
    """Check if cooldown should prevent weight update."""
    if current_bar - last_update_bar < thresholds.cooldown_bars:
        change_pct = percentage_change(old_weight, new_weight)
        if change_pct > thresholds.cooldown_threshold_pct:
            return True
    return False


def is_change_significant(old_weight: float, new_weight: float, thresholds: AdaptationThresholds) -> bool:
    """Check if weight change is significant enough to apply."""
    change_pct = percentage_change(old_weight, new_weight)
    return change_pct >= thresholds.min_change_threshold

