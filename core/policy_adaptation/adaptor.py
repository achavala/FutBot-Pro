from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Optional

from core.policy_adaptation.config_manager import PolicyConfigManager
from core.policy_adaptation.evolution_rules import (
    is_change_significant,
    should_apply_cooldown,
    update_agent_weight,
    update_regime_weight,
    update_structural_weight,
    update_volatility_weight,
)
from core.policy_adaptation.thresholds import AdaptationThresholds, DEFAULT_THRESHOLDS
from core.regime.types import RegimeType, VolatilityLevel
from core.reward.memory import RollingMemoryStore


@dataclass
class AdaptationState:
    """Tracks state for cooldown and update management."""

    last_update_bar: Dict[str, int] = None
    agent_signal_counts: Dict[str, int] = None
    structural_success_tracker: Dict[str, list[bool]] = None

    def __post_init__(self):
        if self.last_update_bar is None:
            self.last_update_bar = defaultdict(int)
        if self.agent_signal_counts is None:
            self.agent_signal_counts = defaultdict(int)
        if self.structural_success_tracker is None:
            self.structural_success_tracker = defaultdict(lambda: [])


class PolicyAdaptor:
    """Adapts policy weights based on reward memory and fitness signals."""

    def __init__(
        self,
        memory_store: RollingMemoryStore,
        thresholds: Optional[AdaptationThresholds] = None,
        config_manager: Optional[PolicyConfigManager] = None,
        freeze_all: bool = False,
        freeze_agents: bool = False,
        freeze_regime: bool = False,
        freeze_volatility: bool = False,
    ):
        self.memory = memory_store
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.config_manager = config_manager or PolicyConfigManager()
        self.freeze_all = freeze_all
        self.freeze_agents = freeze_agents
        self.freeze_regime = freeze_regime
        self.freeze_volatility = freeze_volatility

        # Load initial weights
        self.agent_weights, self.regime_weights, self.volatility_weights, self.structure_weights = (
            self.config_manager.load_weights()
        )

        # Track adaptation state
        self.state = AdaptationState()
        self.bar_count = 0

    def update_weights(self, bar_index: int) -> Dict[str, bool]:
        """Update all weights based on current fitness. Returns dict of what was updated."""
        self.bar_count = bar_index
        if self.freeze_all:
            return {}

        updates = {}

        if not self.freeze_agents:
            updates.update(self._update_agent_weights(bar_index))

        if not self.freeze_regime:
            updates.update(self._update_regime_weights(bar_index))

        if not self.freeze_volatility:
            updates.update(self._update_volatility_weights(bar_index))

        # Always update structural weights (not frozen separately)
        updates.update(self._update_structural_weights(bar_index))

        return updates

    def _update_agent_weights(self, bar_index: int) -> Dict[str, bool]:
        """Update agent weights based on fitness."""
        updates = {}
        for agent_name in list(self.agent_weights.keys()):
            old_weight = self.agent_weights[agent_name]
            fitness = self.memory.get_agent_fitness(agent_name)

            # Check cooldown
            if should_apply_cooldown(
                old_weight,
                old_weight,  # dummy new_weight for cooldown check
                self.thresholds,
                self.state.last_update_bar.get(f"agent_{agent_name}", 0),
                bar_index,
            ):
                continue

            new_weight = update_agent_weight(
                agent_name,
                old_weight,
                fitness,
                self.thresholds,
                self.state.agent_signal_counts,
                self.bar_count,
            )

            if is_change_significant(old_weight, new_weight, self.thresholds):
                self.agent_weights[agent_name] = new_weight
                self.state.last_update_bar[f"agent_{agent_name}"] = bar_index
                updates[f"agent_{agent_name}"] = True

        return updates

    def _update_regime_weights(self, bar_index: int) -> Dict[str, bool]:
        """Update regime weights based on regime fitness."""
        updates = {}
        for regime in list(self.regime_weights.keys()):
            old_weight = self.regime_weights[regime]
            regime_fitness = self.memory.get_regime_fitness(regime)

            new_weight = update_regime_weight(regime, old_weight, regime_fitness, self.thresholds)

            if is_change_significant(old_weight, new_weight, self.thresholds):
                self.regime_weights[regime] = new_weight
                updates[f"regime_{regime.value}"] = True

        return updates

    def _update_volatility_weights(self, bar_index: int) -> Dict[str, bool]:
        """Update volatility weights based on volatility-conditioned fitness."""
        updates = {}
        for level in list(self.volatility_weights.keys()):
            old_weight = self.volatility_weights[level]
            vol_fitness = self.memory.get_volatility_bias(level)

            new_weight = update_volatility_weight(level, old_weight, vol_fitness, self.thresholds)

            if is_change_significant(old_weight, new_weight, self.thresholds):
                self.volatility_weights[level] = new_weight
                updates[f"volatility_{level.value}"] = True

        return updates

    def _update_structural_weights(self, bar_index: int) -> Dict[str, bool]:
        """Update structural weights based on FVG/VWAP alignment success."""
        updates = {}
        for alignment_type in ["aligned", "conflict", "none"]:
            old_weight = self.structure_weights.get(alignment_type, 1.0)
            success_track = self.state.structural_success_tracker.get(alignment_type, [])

            if not success_track:
                continue

            # Compute success rate from recent history
            recent = success_track[-100:]  # last 100 samples
            success_rate = sum(recent) / len(recent) if recent else 0.5

            new_weight = update_structural_weight(alignment_type, old_weight, success_rate, self.thresholds)

            if is_change_significant(old_weight, new_weight, self.thresholds):
                self.structure_weights[alignment_type] = new_weight
                updates[f"structure_{alignment_type}"] = True

        return updates

    def record_agent_signal(self, agent_name: str) -> None:
        """Record that an agent produced a signal (for idle tracking)."""
        # Store the bar count when agent signaled (not just increment)
        self.state.agent_signal_counts[agent_name] = self.bar_count

    def record_structural_outcome(self, alignment_type: str, success: bool) -> None:
        """Record structural alignment outcome for success rate tracking."""
        track = self.state.structural_success_tracker[alignment_type]
        track.append(success)
        if len(track) > 500:  # cap memory
            track.pop(0)

    def get_agent_weight(self, agent_name: str) -> float:
        """Get current weight for an agent."""
        return self.agent_weights.get(agent_name, 1.0)

    def get_regime_weight(self, regime: RegimeType) -> float:
        """Get current weight for a regime."""
        return self.regime_weights.get(regime, 1.0)

    def get_volatility_weight(self, level: VolatilityLevel) -> float:
        """Get current weight for a volatility level."""
        return self.volatility_weights.get(level, 1.0)

    def get_structure_weight(self, alignment_type: str) -> float:
        """Get current structural weight."""
        return self.structure_weights.get(alignment_type, 1.0)

    def save_weights(self) -> None:
        """Save current weights to config file."""
        self.config_manager.save_weights(
            self.agent_weights,
            self.regime_weights,
            self.volatility_weights,
            self.structure_weights,
        )

