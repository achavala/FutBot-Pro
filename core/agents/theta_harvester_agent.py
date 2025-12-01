"""Theta Harvester Agent - Sells premium in compression regimes with high IV."""

from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.config.asset_profiles import OptionRiskProfile
from core.regime.types import RegimeSignal, RegimeType
from core.regime.microstructure import MarketMicrostructure

logger = logging.getLogger(__name__)


class ThetaHarvesterAgent(BaseAgent):
    """
    Theta Harvester Agent - Sells premium (straddles) in compression regimes.
    
    Strategy:
    - Requires COMPRESSION regime (range-bound market)
    - Requires high IV percentile (>70%) for selling premium
    - Sells ATM straddles to collect theta decay
    - Safe sizing (hybrid mode: max 5 contracts)
    """
    
    def __init__(
        self,
        symbol: str,
        config: Optional[Mapping[str, float]] = None,
        options_data_feed: Optional["OptionsDataFeed"] = None,
        option_risk_profile: Optional[OptionRiskProfile] = None,
        options_broker_client: Optional[object] = None,  # OptionsBrokerClient (if using Alpaca)
    ):
        super().__init__("theta_harvester", symbol, config)
        self.options_data_feed = options_data_feed
        self.option_risk_profile = option_risk_profile or OptionRiskProfile()
        self.options_broker_client = options_broker_client  # Store for Alpaca detection
        
        # Configuration
        self.min_iv_percentile = 70.0  # Only sell when IV > 70th percentile
        self.max_position_size = 5  # Hybrid mode cap (safe sizing)
        self.min_confidence = 0.85  # High confidence required for selling premium
        
        # Safety: Alpaca paper trading does NOT support selling naked straddles
        # (requires level 3 options approval, which paper accounts don't have)
        self.alpaca_paper_mode = False
        if self.options_broker_client:
            try:
                # Check if it's an Alpaca broker client
                if hasattr(self.options_broker_client, 'is_paper') and self.options_broker_client.is_paper:
                    self.alpaca_paper_mode = True
                    logger.warning(
                        f"[ThetaHarvester] Alpaca PAPER trading detected - "
                        f"Straddle selling will use SIM mode only "
                        f"(Alpaca paper does not support naked options selling)"
                    )
            except Exception:
                pass
        
        logger.info(f"ThetaHarvesterAgent initialized for {symbol}")
    
    def evaluate(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
    ) -> List[TradeIntent]:
        """
        Evaluate theta harvesting opportunity.
        
        Returns trade intent to SELL ATM straddle if:
        - Regime is COMPRESSION
        - IV percentile is high (>70%)
        - Market is range-bound
        """
        if not self.options_data_feed:
            return []
        
        # Helper to safely get enum value
        def get_enum_val(e):
            return e.value if hasattr(e, 'value') and not isinstance(e, str) else str(e)
        
        regime_type = get_enum_val(signal.regime_type)
        
        # REQUIREMENT 1: Compression regime
        if regime_type != "compression":
            logger.debug(f"[THETA] Skipping - regime is {regime_type}, need COMPRESSION")
            return []
        
        # REQUIREMENT 2: High confidence
        if signal.confidence < self.min_confidence:
            logger.debug(f"[THETA] Skipping - confidence {signal.confidence:.2%} < {self.min_confidence:.2%}")
            return []
        
        current_price = market_state.get("close", 0.0)
        if current_price <= 0:
            return []
        
        # Get IV percentile
        try:
            # Get options chain to calculate IV percentile
            options_chain = self.options_data_feed.get_options_chain(
                underlying_symbol=self.symbol,
                option_type="call",  # Get calls for IV calculation
            )
            
            if not options_chain:
                return []
            
            # Find ATM call to get IV
            atm_call = None
            for option in options_chain:
                strike = float(option.get("strike_price", 0))
                if abs(strike - current_price) / current_price < 0.02:  # Within 2% of ATM
                    option_symbol = option.get("symbol", "")
                    if option_symbol:
                        greeks = self.options_data_feed.get_option_greeks(option_symbol)
                        if greeks and greeks.get("implied_volatility"):
                            atm_call = option
                            iv = greeks.get("implied_volatility", 0.0)
                            break
            
            if not atm_call:
                return []
            
            # Calculate IV percentile
            iv_percentile = self.options_data_feed.calculate_iv_percentile(
                underlying_symbol=self.symbol,
                current_iv=iv,
                lookback_days=252,
                option_type="call",
            )
            
            if iv_percentile is None or iv_percentile < self.min_iv_percentile:
                logger.debug(
                    f"[THETA] Skipping - IV percentile {iv_percentile:.1f}% < {self.min_iv_percentile:.1f}%"
                )
                return []
            
        except Exception as e:
            logger.debug(f"[THETA] Error calculating IV percentile: {e}")
            return []
        
        # Find ATM call and put for straddle
        atm_call_contract = None
        atm_put_contract = None
        
        # Get both calls and puts
        calls_chain = self.options_data_feed.get_options_chain(
            underlying_symbol=self.symbol,
            option_type="call",
        )
        puts_chain = self.options_data_feed.get_options_chain(
            underlying_symbol=self.symbol,
            option_type="put",
        )
        
        if not calls_chain or not puts_chain:
            return []
        
        # Find nearest ATM strikes
        for call in calls_chain:
            strike = float(call.get("strike_price", 0))
            if abs(strike - current_price) / current_price < 0.02:
                atm_call_contract = call
                break
        
        for put in puts_chain:
            strike = float(put.get("strike_price", 0))
            if abs(strike - current_price) / current_price < 0.02:
                atm_put_contract = put
                break
        
        if not atm_call_contract or not atm_put_contract:
            return []
        
        # Get quotes for pricing
        call_symbol = atm_call_contract.get("symbol", "")
        put_symbol = atm_put_contract.get("symbol", "")
        
        if not call_symbol or not put_symbol:
            return []
        
        call_quote = self.options_data_feed.get_option_quote(call_symbol)
        put_quote = self.options_data_feed.get_option_quote(put_symbol)
        
        if not call_quote or not put_quote:
            return []
        
        call_bid = float(call_quote.get("bid", 0))
        put_bid = float(put_quote.get("bid", 0))
        
        if call_bid <= 0 or put_bid <= 0:
            return []
        
        # Calculate total credit for straddle
        total_credit = call_bid + put_bid
        
        # Calculate position size (safe sizing for hybrid mode)
        # Use 0.2% of capital per straddle, capped at max_position_size
        # This is conservative for selling premium
        size = max(1, min(self.max_position_size, int(total_credit * 10)))  # Simplified sizing
        
        strike = float(atm_call_contract.get("strike_price", current_price))
        expiration = atm_call_contract.get("expiration_date", "")
        
        # ============================================================
        # SAFETY: Alpaca Paper Trading does NOT support naked straddle selling
        # ============================================================
        # Alpaca paper accounts require level 3 options approval for selling naked options,
        # which is not available in paper trading. This would result in:
        # "422 Unprocessable entity: insufficient buying power"
        #
        # Solution: Mark as SIM-only trade when using Alpaca paper
        # This allows the strategy to run and be tracked, but won't place real orders
        
        # Check for Alpaca paper mode (can be set at runtime by scheduler)
        is_alpaca_paper = False
        if hasattr(self, 'options_broker_client') and self.options_broker_client:
            try:
                if hasattr(self.options_broker_client, 'is_paper') and self.options_broker_client.is_paper:
                    is_alpaca_paper = True
            except Exception:
                pass
        elif self.alpaca_paper_mode:
            is_alpaca_paper = True
        
        if is_alpaca_paper:
            logger.warning(
                f"[THETA HARVEST] Compression + IV={iv_percentile:.1f}% → "
                f"SELL {size}x ATM straddle @ ${strike:.2f} (SIM MODE - Alpaca paper doesn't support naked selling)"
            )
            # Mark as simulation-only in metadata
            metadata = {
                "strategy": "theta_harvester",
                "trade_type": "straddle",
                "strike": strike,
                "expiration": expiration,
                "call_symbol": call_symbol,
                "put_symbol": put_symbol,
                "total_credit": total_credit,
                "iv_percentile": iv_percentile,
                "regime": regime_type,
                "sim_only": True,  # Flag to prevent real order submission
                "reason": "Alpaca paper does not support naked options selling",
            }
        else:
            logger.info(
                f"[THETA HARVEST] Compression + IV={iv_percentile:.1f}% → "
                f"SELL {size}x ATM straddle @ ${strike:.2f}, credit=${total_credit:.2f}"
            )
            metadata = {
                "strategy": "theta_harvester",
                "trade_type": "straddle",
                "strike": strike,
                "expiration": expiration,
                "call_symbol": call_symbol,
                "put_symbol": put_symbol,
                "total_credit": total_credit,
                "iv_percentile": iv_percentile,
                "regime": regime_type,
            }
        
        # Return intent to SELL straddle
        # Note: We'll use metadata to indicate this is a straddle trade
        return [
            self._build_intent(
                direction=TradeDirection.SHORT,  # Selling premium
                size=float(size),
                confidence=signal.confidence,
                reason=(
                    f"SELL {size}x ATM STRADDLE @ ${strike:.2f}: "
                    f"Compression regime + IV={iv_percentile:.1f}% (high) → "
                    f"collect ${total_credit:.2f} credit"
                    + (" [SIM ONLY - Alpaca paper limitation]" if is_alpaca_paper else "")
                ),
                metadata=metadata,
                instrument_type="option",
                option_type="straddle",  # Special type for straddle
                moneyness="atm",
                time_to_expiry_days=0,  # Will be calculated from expiration
            )
        ]

