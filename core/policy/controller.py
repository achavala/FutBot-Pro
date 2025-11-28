from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable, List, Mapping, Optional, Sequence

import numpy as np

from core.agents.base import BaseAgent, TradeIntent
from core.policy import filters, scoring
from core.policy.types import FinalTradeIntent
from core.regime.types import RegimeSignal

if TYPE_CHECKING:
    from core.policy_adaptation.adaptor import PolicyAdaptor


@dataclass
class ControllerConfig:
    min_final_confidence: float = 0.25  # Lowered to 0.25 to allow more trades
    max_abs_position: float = 1.0
    blend_threshold_ratio: float = 0.05  # 5% difference


class MetaPolicyController:
    """Deterministic meta-policy controller that arbitrates agent intents."""

    def __init__(
        self,
        agent_weights: Optional[Mapping[str, float]] = None,
        filter_config: Optional[filters.FilterConfig] = None,
        config: Optional[ControllerConfig] = None,
        adaptor: Optional["PolicyAdaptor"] = None,
    ):
        self.adaptor = adaptor
        self.agent_weights = {**scoring.AGENT_WEIGHTS, **(agent_weights or {})}
        if not adaptor:
            scoring.AGENT_WEIGHTS.update(self.agent_weights)
        self.filter_config = filter_config or filters.FilterConfig()
        self.config = config or ControllerConfig()

    def decide(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
        agents: Sequence[BaseAgent],
        context: Optional[Mapping[str, object]] = None,
    ) -> FinalTradeIntent:
        # Check if testing_mode is enabled (passed via context)
        testing_mode = context and context.get("testing_mode", False)
        
        # Regime confidence veto - check early
        # VERY AGGRESSIVE: Accept any confidence level to ensure trades execute TODAY
        min_confidence = 0.0  # Accept 0% confidence - we want trades to happen!
        
        # Only block if confidence is negative (which shouldn't happen)
        if signal.confidence < 0.0:
            return self._empty_decision(reason=f"Invalid negative confidence: {signal.confidence:.2f}")
        
        # Log that we're being very lenient
        if signal.confidence == 0.0:
            # Even with 0% confidence, allow trading - we'll use price action signals
            pass  # Don't block, continue to agent evaluation

        intents = self.collect_intents(signal, market_state, agents)
        # Pass testing_mode to filters so they can bypass restrictions
        filtered = self.filter_intents(intents, signal, testing_mode=testing_mode)
        scored = self.score_intents(filtered, signal)
        decision = self.arbitrate_intents(scored, context, signal, testing_mode=testing_mode)
        return decision

    def collect_intents(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
        agents: Sequence[BaseAgent],
    ) -> List[TradeIntent]:
        intents: List[TradeIntent] = []
        for agent in agents:
            agent_intents = agent.evaluate(signal, market_state)
            intents.extend(agent_intents)
            if agent_intents and self.adaptor:
                self.adaptor.record_agent_signal(agent.name)
        return intents

    def filter_intents(self, intents: Sequence[TradeIntent], signal: RegimeSignal, testing_mode: bool = False) -> List[TradeIntent]:
        return filters.apply_filters(intents, signal, self.filter_config, testing_mode=testing_mode)

    def score_intents(self, intents: Sequence[TradeIntent], signal: RegimeSignal) -> Sequence[scoring.ScoredIntent]:
        return scoring.score_intents(intents, signal, self.adaptor)

    def arbitrate_intents(
        self,
        scored_intents: Sequence[scoring.ScoredIntent],
        context: Optional[Mapping[str, object]] = None,
        signal: Optional[RegimeSignal] = None,
        testing_mode: bool = False,
    ) -> FinalTradeIntent:
        if not scored_intents:
            return self._empty_decision(reason="No valid agent signals")

        sorted_intents = sorted(scored_intents, key=lambda s: s.score, reverse=True)
        primary = sorted_intents[0]
        contributing = [primary.intent.agent_name]
        position_delta = primary.position_delta
        score = primary.score

        blend_threshold = primary.score * self.config.blend_threshold_ratio
        close_intents = [
            si for si in sorted_intents if si is not primary and abs(primary.score - si.score) <= blend_threshold
        ]

        if close_intents:
            weighted_scores = [primary.score] + [si.score for si in close_intents]
            weighted_positions = [primary.position_delta * primary.score] + [
                si.position_delta * si.score for si in close_intents
            ]
            total_score = sum(weighted_scores)
            position_delta = sum(weighted_positions) / total_score if total_score else 0.0
            contributing = [si.intent.agent_name for si in [primary] + close_intents]
            score = max(weighted_scores)

        position_delta = float(np.clip(position_delta, -self.config.max_abs_position, self.config.max_abs_position))

        if context and context.get("risk_off"):
            return self._empty_decision(reason="Risk-off state engaged")

        confidence = float(np.clip(score, 0.0, 1.0))
        # FORCE MODE: In testing_mode, accept ANY confidence (even 0%) to force trades
        if testing_mode:
            min_final = 0.0  # Accept 0% confidence in testing mode
            logger.info(f"🔥 [TestingMode] Bypassing confidence threshold - accepting {confidence:.2f}% confidence")
        else:
            min_final = 0.05  # VERY AGGRESSIVE: Accept 5% confidence to ensure trades happen TODAY
        
        if confidence < min_final:
            return self._empty_decision(reason=f"Confidence below threshold ({confidence:.2f} < {min_final:.2f})")

        reason = primary.intent.reason if not close_intents else "Blended agent consensus"
        return FinalTradeIntent(
            position_delta=position_delta,
            confidence=confidence,
            primary_agent=primary.intent.agent_name,
            contributing_agents=contributing,
            reason=reason,
            is_valid=True,
        )

    def _empty_decision(self, reason: str) -> FinalTradeIntent:
        return FinalTradeIntent(
            position_delta=0.0,
            confidence=0.0,
            primary_agent="NONE",
            contributing_agents=[],
            reason=reason,
            is_valid=False,
        )

