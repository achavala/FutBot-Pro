from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, Tuple

from core.regime.types import RegimeType, VolatilityLevel


@dataclass
class FitnessSnapshot:
    """Represents short and long horizon agent fitness."""

    short_term: float
    long_term: float


class RollingMemoryStore:
    """Maintains rolling windows of rewards for agents, regimes, and volatility buckets."""

    def __init__(self, short_window: int = 20, long_window: int = 500):
        self.short_window = short_window
        self.long_window = long_window
        self.agent_rewards: Dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=long_window))
        self.regime_rewards: Dict[RegimeType, Deque[float]] = defaultdict(lambda: deque(maxlen=long_window))
        self.volatility_rewards: Dict[VolatilityLevel, Deque[float]] = defaultdict(lambda: deque(maxlen=long_window))
        self.trade_history: Deque[Tuple[float, float]] = deque(maxlen=long_window)

    def record_trade(self, reward: float, position_delta: float) -> None:
        self.trade_history.append((reward, position_delta))

    def update_agent(self, name: str, reward: float) -> None:
        self.agent_rewards[name].append(reward)

    def update_regime(self, regime: RegimeType, reward: float) -> None:
        self.regime_rewards[regime].append(reward)

    def update_volatility(self, level: VolatilityLevel, reward: float) -> None:
        self.volatility_rewards[level].append(reward)

    def get_agent_fitness(self, name: str) -> FitnessSnapshot:
        rewards = list(self.agent_rewards.get(name, []))
        if not rewards:
            return FitnessSnapshot(short_term=0.0, long_term=0.0)
        short_slice = rewards[-self.short_window :]
        short_avg = sum(short_slice) / len(short_slice)
        long_avg = sum(rewards) / len(rewards)
        return FitnessSnapshot(short_term=short_avg, long_term=long_avg)

    def get_regime_fitness(self, regime: RegimeType) -> float:
        rewards = self.regime_rewards.get(regime, [])
        if not rewards:
            return 0.0
        return sum(rewards) / len(rewards)

    def get_volatility_bias(self, level: VolatilityLevel) -> float:
        rewards = self.volatility_rewards.get(level, [])
        if not rewards:
            return 0.0
        return sum(rewards) / len(rewards)

