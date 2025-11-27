from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AgentContribution:
    """Represents an agent's contribution to the final trade decision."""

    name: str
    weight: float


def distribute_reward(
    total_reward: float,
    primary_agent: str,
    contributions: Iterable[AgentContribution],
    primary_share: float = 0.7,
) -> Dict[str, float]:
    """Distribute reward across contributing agents."""
    contributions = list(contributions)
    if not contributions:
        return {primary_agent: total_reward}

    normalized = _normalize_weights(contributions)
    rewards: Dict[str, float] = {}
    primary_reward = total_reward * primary_share
    rewards[primary_agent] = rewards.get(primary_agent, 0.0) + primary_reward

    secondary_total = total_reward - primary_reward
    if secondary_total == 0 or not normalized:
        return rewards

    for contrib in normalized:
        if contrib.name == primary_agent:
            continue
        rewards[contrib.name] = rewards.get(contrib.name, 0.0) + secondary_total * contrib.weight
    return rewards


def _normalize_weights(contributions: List[AgentContribution]) -> List[AgentContribution]:
    total = sum(max(c.weight, 0.0) for c in contributions)
    if total <= 0:
        return []
    return [AgentContribution(name=c.name, weight=c.weight / total) for c in contributions]

