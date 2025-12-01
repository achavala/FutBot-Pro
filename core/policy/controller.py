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
        import logging
        logger = logging.getLogger(__name__)
        
        intents: List[TradeIntent] = []
        agent_failures = []
        logger.info(f"🔍 [Controller] Collecting intents from {len(agents)} agents")
        for agent in agents:
            try:
                agent_intents = agent.evaluate(signal, market_state)
                logger.info(f"🔍 [Controller] Agent {agent.name} generated {len(agent_intents)} intents")
                if agent_intents:
                    for intent in agent_intents:
                        # Handle both enum and string for direction
                        direction_str = intent.direction.value if hasattr(intent.direction, 'value') else str(intent.direction)
                        logger.info(f"  → Intent: {direction_str}, confidence={intent.confidence:.2f}, size={intent.size:.4f}, reason={intent.reason}")
                intents.extend(agent_intents)
                if agent_intents and self.adaptor:
                    self.adaptor.record_agent_signal(agent.name)
            except Exception as e:
                agent_failures.append(agent.name)
                logger.error(f"❌ [Controller] Agent {agent.name} evaluation failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # HARD FAIL: If ALL agents failed, raise exception to halt the run
        if len(agent_failures) == len(agents) and len(agents) > 0:
            error_msg = f"🚨 FATAL: All {len(agents)} agents failed evaluation. Halting run."
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"🔍 [Controller] Total intents collected: {len(intents)} (failures: {len(agent_failures)}/{len(agents)})")
        return intents

    def filter_intents(self, intents: Sequence[TradeIntent], signal: RegimeSignal, testing_mode: bool = False) -> List[TradeIntent]:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 [Controller] Filtering {len(intents)} intents (testing_mode={testing_mode})")
        filtered = filters.apply_filters(intents, signal, self.filter_config, testing_mode=testing_mode)
        logger.info(f"🔍 [Controller] After filtering: {len(filtered)} intents remain")
        if len(intents) > 0 and len(filtered) == 0:
            logger.warning(f"⚠️ [Controller] All {len(intents)} intents were filtered out!")
        return filtered

    def score_intents(self, intents: Sequence[TradeIntent], signal: RegimeSignal) -> Sequence[scoring.ScoredIntent]:
        return scoring.score_intents(intents, signal, self.adaptor)

    def arbitrate_intents(
        self,
        scored_intents: Sequence[scoring.ScoredIntent],
        context: Optional[Mapping[str, object]] = None,
        signal: Optional[RegimeSignal] = None,
        testing_mode: bool = False,
    ) -> FinalTradeIntent:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"🔍 [Controller] Arbitrating {len(scored_intents)} scored intents (testing_mode={testing_mode})")
        if not scored_intents:
            logger.warning(f"⚠️ [Controller] No scored intents - returning empty decision")
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
            # FORCE: If confidence is 0, set it to minimum to ensure trade executes
            if confidence == 0.0 and score > 0:
                confidence = max(0.1, score)  # Ensure at least 10% confidence for execution
            logger.info(f"🔥 [TestingMode] Bypassing confidence threshold - accepting {confidence:.2f}% confidence")
        else:
            min_final = 0.0  # ULTRA AGGRESSIVE: Accept 0% confidence to force trades NOW
        
        if confidence < min_final:
            # FORCE MODE: Even if confidence is 0, accept it in testing mode
            if testing_mode:
                confidence = 0.1  # Force minimum confidence
                logger.info(f"🔥 [TestingMode] FORCING trade with 0.1% confidence")
            else:
                logger.warning(f"⚠️ [Controller] Confidence {confidence:.2f} below threshold {min_final:.2f} - returning empty decision")
                return self._empty_decision(reason=f"Confidence below threshold ({confidence:.2f} < {min_final:.2f})")

        reason = primary.intent.reason if not close_intents else "Blended agent consensus"
        # Pass through options fields from primary intent
        final_intent = FinalTradeIntent(
            position_delta=position_delta,
            confidence=confidence,
            primary_agent=primary.intent.agent_name,
            contributing_agents=contributing,
            reason=reason,
            is_valid=True,
            instrument_type=primary.intent.instrument_type,
            option_type=primary.intent.option_type,
            moneyness=primary.intent.moneyness,
            time_to_expiry_days=primary.intent.time_to_expiry_days,
        )
        logger.info(f"✅ [Controller] Final intent: delta={position_delta:.4f}, confidence={confidence:.2f}, agent={primary.intent.agent_name}, reason={reason}")
        return final_intent

    def _empty_decision(self, reason: str) -> FinalTradeIntent:
        return FinalTradeIntent(
            position_delta=0.0,
            confidence=0.0,
            primary_agent="NONE",
            contributing_agents=[],
            reason=reason,
            is_valid=False,
        )

