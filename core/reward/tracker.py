from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Optional

import numpy as np

from core.policy.types import FinalTradeIntent
from core.regime.types import Bias, RegimeSignal, RegimeType, VolatilityLevel
from core.reward.attribution import AgentContribution, distribute_reward
from core.reward.memory import RollingMemoryStore


@dataclass
class RewardWeights:
    pnl: float = 0.5
    direction: float = 0.15
    confidence: float = 0.1
    volatility: float = 0.1
    regime: float = 0.1
    structure: float = 0.05


@dataclass
class RewardComponents:
    pnl: float
    direction: float
    confidence: float
    volatility: float
    regime: float
    structure: float

    @property
    def total(self) -> float:
        return self.pnl + self.direction + self.confidence + self.volatility + self.regime + self.structure


@dataclass
class TrackerConfig:
    return_scale: float = 0.02  # 2% move treated as max for confidence calibration
    high_vol_penalty: float = 1.2
    wrong_direction_penalty: float = 1.5


class RewardTracker:
    """Computes rewards and tracks rolling agent performance."""

    def __init__(
        self,
        weights: Optional[RewardWeights] = None,
        memory_store: Optional[RollingMemoryStore] = None,
        config: Optional[TrackerConfig] = None,
    ):
        self.weights = weights or RewardWeights()
        self.memory = memory_store or RollingMemoryStore()
        self.config = config or TrackerConfig()

    def compute_components(
        self,
        intent: FinalTradeIntent,
        next_return: float,
        signal: RegimeSignal,
    ) -> RewardComponents:
        position_delta = intent.position_delta
        pnl_component = position_delta * next_return

        direction_component = self._direction_component(position_delta, next_return)
        confidence_component = self._confidence_component(intent.confidence, next_return)
        volatility_component = self._volatility_component(pnl_component, signal.volatility_level)
        regime_component = self._regime_component(position_delta, signal)
        structure_component = self._structure_component(position_delta, signal)

        return RewardComponents(
            pnl=self.weights.pnl * pnl_component,
            direction=self.weights.direction * direction_component,
            confidence=self.weights.confidence * confidence_component,
            volatility=self.weights.volatility * volatility_component,
            regime=self.weights.regime * regime_component,
            structure=self.weights.structure * structure_component,
        )

    def update(
        self,
        intent: FinalTradeIntent,
        next_return: float,
        signal: RegimeSignal,
        contributions: Optional[Iterable[AgentContribution]] = None,
    ) -> Dict[str, float]:
        components = self.compute_components(intent, next_return, signal)
        total_reward = components.total

        contributions = list(contributions or self._build_default_contributions(intent))
        allocation = distribute_reward(total_reward, intent.primary_agent, contributions)

        for agent, reward in allocation.items():
            self.memory.update_agent(agent, reward)
        self.memory.update_regime(signal.regime_type, total_reward)
        self.memory.update_volatility(signal.volatility_level, total_reward)
        self.memory.record_trade(total_reward, intent.position_delta)
        return allocation

    def _build_default_contributions(self, intent: FinalTradeIntent) -> List[AgentContribution]:
        return [AgentContribution(name=name, weight=1.0) for name in intent.contributing_agents]

    def _direction_component(self, position_delta: float, next_return: float) -> float:
        if position_delta == 0 or next_return == 0:
            return 0.0
        same_direction = np.sign(position_delta) == np.sign(next_return)
        magnitude = min(abs(next_return) / self.config.return_scale, 1.0)
        return magnitude if same_direction else -magnitude * self.config.wrong_direction_penalty

    def _confidence_component(self, confidence: float, next_return: float) -> float:
        target = min(abs(next_return) / self.config.return_scale, 1.0)
        calibration = 1 - min(abs(confidence - target), 1.0)
        return (calibration * 2) - 1  # scale to [-1, 1]

    def _volatility_component(self, pnl_component: float, level: VolatilityLevel) -> float:
        modifiers = {
            VolatilityLevel.LOW: 0.8,
            VolatilityLevel.MEDIUM: 1.0,
            VolatilityLevel.HIGH: 1.2,
        }
        return pnl_component * (modifiers[level] - 1)

    def _regime_component(self, position_delta: float, signal: RegimeSignal) -> float:
        if position_delta == 0 or signal.bias == Bias.NEUTRAL:
            return 0.0
        desired_direction = 1.0 if signal.bias == Bias.LONG else -1.0
        return 1.0 if np.sign(position_delta) == desired_direction else -1.0

    def _structure_component(self, position_delta: float, signal: RegimeSignal) -> float:
        if not signal.active_fvg or position_delta == 0:
            return 0.0
        fvg_bias = 1.0 if signal.active_fvg.gap_type == "bullish" else -1.0
        return 1.0 if np.sign(position_delta) == fvg_bias else -1.0

