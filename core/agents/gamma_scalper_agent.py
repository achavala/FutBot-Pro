"""Gamma Scalper Agent - Buys strangles in negative GEX + cheap IV conditions."""

from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.config.asset_profiles import OptionRiskProfile
from core.regime.types import RegimeSignal
from core.regime.microstructure import MarketMicrostructure

logger = logging.getLogger(__name__)


class GammaScalperAgent(BaseAgent):
    """
    Gamma Scalper Agent - Buys strangles when negative GEX + cheap IV.
    
    Strategy:
    - Requires NEGATIVE GEX (dealers short gamma → volatility expansion)
    - Requires low IV percentile (<30%) for buying premium cheap
    - Buys 25-delta strangles to profit from volatility explosions
    - Aggressive sizing (hybrid mode: max 7 contracts, but capped)
    """
    
    def __init__(
        self,
        symbol: str,
        config: Optional[Mapping[str, float]] = None,
        options_data_feed: Optional["OptionsDataFeed"] = None,
        option_risk_profile: Optional[OptionRiskProfile] = None,
    ):
        super().__init__("gamma_scalper", symbol, config)
        self.options_data_feed = options_data_feed
        self.option_risk_profile = option_risk_profile or OptionRiskProfile()
        
        # Configuration
        self.max_iv_percentile = 30.0  # Only buy when IV < 30th percentile (cheap)
        self.min_gex_strength = 2.0  # Minimum GEX strength in billions
        self.max_position_size = 7  # Hybrid mode cap (aggressive but safe)
        self.target_delta = 0.25  # 25-delta strangles
        
        logger.info(f"GammaScalperAgent initialized for {symbol}")
    
    def evaluate(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
    ) -> List[TradeIntent]:
        """
        Evaluate gamma scalping opportunity.
        
        Returns trade intent to BUY 25-delta strangle if:
        - GEX regime is NEGATIVE (dealers short gamma)
        - GEX strength > $2B
        - IV percentile is low (<30%)
        """
        if not self.options_data_feed:
            return []
        
        current_price = market_state.get("close", 0.0)
        if current_price <= 0:
            return []
        
        # Get GEX data from microstructure
        microstructure = MarketMicrostructure()
        gex = microstructure.get(self.symbol)
        
        gex_regime = gex.get('gex_regime', 'NEUTRAL')
        gex_strength = gex.get('gex_strength', 0.0)
        
        # REQUIREMENT 1: Negative GEX with sufficient strength
        if gex_regime != "NEGATIVE" or gex_strength < self.min_gex_strength:
            logger.debug(
                f"[GAMMA] Skipping - GEX regime={gex_regime}, strength={gex_strength:.2f}B "
                f"(need NEGATIVE > {self.min_gex_strength}B)"
            )
            return []
        
        # Get IV percentile
        try:
            # Get options chain to calculate IV percentile
            options_chain = self.options_data_feed.get_options_chain(
                underlying_symbol=self.symbol,
                option_type="call",
            )
            
            if not options_chain:
                return []
            
            # Find ATM call to get IV
            iv = 0.0
            for option in options_chain:
                strike = float(option.get("strike_price", 0))
                if abs(strike - current_price) / current_price < 0.02:  # Within 2% of ATM
                    option_symbol = option.get("symbol", "")
                    if option_symbol:
                        greeks = self.options_data_feed.get_option_greeks(option_symbol)
                        if greeks and greeks.get("implied_volatility"):
                            iv = greeks.get("implied_volatility", 0.0)
                            break
            
            if iv <= 0:
                return []
            
            # Calculate IV percentile
            iv_percentile = self.options_data_feed.calculate_iv_percentile(
                underlying_symbol=self.symbol,
                current_iv=iv,
                lookback_days=252,
                option_type="call",
            )
            
            if iv_percentile is None or iv_percentile > self.max_iv_percentile:
                logger.debug(
                    f"[GAMMA] Skipping - IV percentile {iv_percentile:.1f}% > {self.max_iv_percentile:.1f}%"
                )
                return []
            
        except Exception as e:
            logger.debug(f"[GAMMA] Error calculating IV percentile: {e}")
            return []
        
        # Find 25-delta call and put for strangle
        call_25_contract = None
        put_25_contract = None
        
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
        
        # Find 25-delta strikes (closest to target_delta)
        best_call_delta_diff = float('inf')
        best_put_delta_diff = float('inf')
        
        for call in calls_chain:
            option_symbol = call.get("symbol", "")
            if not option_symbol:
                continue
            
            greeks = self.options_data_feed.get_option_greeks(option_symbol)
            if not greeks:
                continue
            
            delta = abs(float(greeks.get("delta", 0)))
            delta_diff = abs(delta - self.target_delta)
            
            if delta_diff < best_call_delta_diff:
                best_call_delta_diff = delta_diff
                call_25_contract = call
        
        for put in puts_chain:
            option_symbol = put.get("symbol", "")
            if not option_symbol:
                continue
            
            greeks = self.options_data_feed.get_option_greeks(option_symbol)
            if not greeks:
                continue
            
            delta = abs(float(greeks.get("delta", 0)))
            delta_diff = abs(delta - self.target_delta)
            
            if delta_diff < best_put_delta_diff:
                best_put_delta_diff = delta_diff
                put_25_contract = put
        
        if not call_25_contract or not put_25_contract:
            return []
        
        # Get quotes for pricing
        call_symbol = call_25_contract.get("symbol", "")
        put_symbol = put_25_contract.get("symbol", "")
        
        if not call_symbol or not put_symbol:
            return []
        
        call_quote = self.options_data_feed.get_option_quote(call_symbol)
        put_quote = self.options_data_feed.get_option_quote(put_symbol)
        
        if not call_quote or not put_quote:
            return []
        
        call_ask = float(call_quote.get("ask", 0))
        put_ask = float(put_quote.get("ask", 0))
        
        if call_ask <= 0 or put_ask <= 0:
            return []
        
        # Calculate total debit for strangle
        total_debit = call_ask + put_ask
        
        # Calculate position size (aggressive but capped for hybrid mode)
        # Use 0.5% of capital per strangle, capped at max_position_size
        size = max(1, min(self.max_position_size, int(total_debit * 15)))  # Simplified sizing
        
        call_strike = float(call_25_contract.get("strike_price", 0))
        put_strike = float(put_25_contract.get("strike_price", 0))
        expiration = call_25_contract.get("expiration_date", "")
        
        logger.info(
            f"[GAMMA SCALP] NEGATIVE GEX ({gex_strength:.2f}B) + IV={iv_percentile:.1f}% → "
            f"BUY {size}x 25Δ strangle (CALL ${call_strike:.2f} / PUT ${put_strike:.2f}), "
            f"debit=${total_debit:.2f}"
        )
        
        # Return intent to BUY strangle
        return [
            self._build_intent(
                direction=TradeDirection.LONG,  # Buying premium
                size=float(size),
                confidence=1.20,  # High confidence for volatility expansion plays
                reason=(
                    f"BUY {size}x 25Δ STRANGLE (CALL ${call_strike:.2f} / PUT ${put_strike:.2f}): "
                    f"NEGATIVE GEX ({gex_strength:.2f}B) + IV={iv_percentile:.1f}% (cheap) → "
                    f"volatility expansion edge, debit=${total_debit:.2f}"
                ),
                metadata={
                    "strategy": "gamma_scalper",
                    "trade_type": "strangle",
                    "call_strike": call_strike,
                    "put_strike": put_strike,
                    "expiration": expiration,
                    "call_symbol": call_symbol,
                    "put_symbol": put_symbol,
                    "total_debit": total_debit,
                    "iv_percentile": iv_percentile,
                    "gex_regime": gex_regime,
                    "gex_strength": gex_strength,
                    "target_delta": self.target_delta,
                },
                instrument_type="option",
                option_type="strangle",  # Special type for strangle
                moneyness="otm",  # Strangles are OTM
                time_to_expiry_days=0,  # Will be calculated from expiration
            )
        ]


