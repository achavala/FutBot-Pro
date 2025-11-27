from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class FinalTradeIntent:
    """Unified action emitted by the meta-policy after arbitration."""

    position_delta: float
    confidence: float
    primary_agent: str
    contributing_agents: List[str] = field(default_factory=list)
    reason: str = ""
    is_valid: bool = True

