"""Options trading agent for analyzing and trading options."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Mapping, Optional

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.config.asset_profiles import OptionRiskProfile
from core.regime.types import RegimeSignal

# Import OptionsSelector if available
try:
    from core.agents.options_selector import OptionsSelector
except ImportError:
    OptionsSelector = None  # Will be set later if needed

logger = logging.getLogger(__name__)


class OptionsAgent(BaseAgent):
    """
    Options trading agent that analyzes options opportunities.
    
    For PUT trades (bearish):
    - Requires DOWNTREND regime
    - Requires SHORT bias
    - Requires high confidence
    - Analyzes IV rank/percentile
    - Considers time to expiration
    """
    
    def __init__(
        self,
        symbol: str,
        config: Optional[Mapping[str, float]] = None,
        options_data_feed: Optional["OptionsDataFeed"] = None,
        option_risk_profile: Optional[OptionRiskProfile] = None,
        trend_agent_signal: Optional[TradeIntent] = None,
        mean_reversion_agent_signal: Optional[TradeIntent] = None,
        volatility_agent_signal: Optional[TradeIntent] = None,
    ):
        super().__init__("options_agent", symbol, config)
        self.options_data_feed = options_data_feed
        self.option_risk_profile = option_risk_profile or OptionRiskProfile()  # Default profile
        self.trend_agent_signal = trend_agent_signal
        self.mean_reversion_agent_signal = mean_reversion_agent_signal
        self.volatility_agent_signal = volatility_agent_signal
        
        # Use risk profile values if available
        self.min_confidence = float(self.config.get("min_confidence", 0.70))
        self.min_iv_percentile = self.option_risk_profile.min_iv_percentile
        self.max_iv_percentile = self.option_risk_profile.max_iv_percentile
        self.min_dte = self.option_risk_profile.min_dte_for_entry
        self.max_dte = self.option_risk_profile.max_dte_for_entry
        self.delta_range = self.option_risk_profile.delta_range
        
        # STEP 6: Contract selection engine
        if OptionsSelector is not None:
            self.options_selector = OptionsSelector(self.option_risk_profile)
        else:
            self.options_selector = None
    
    def evaluate(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
    ) -> List[TradeIntent]:
        """
        Evaluate options trading opportunity.
        
        For PUT trades:
        - Regime must be DOWNTREND or EXPANSION (bearish)
        - Bias must be SHORT
        - Confidence must be high (≥70%)
        - Volatility should be MEDIUM to HIGH (good for options)
        """
        # TRACE LOGGING: Log when agent is called
        logger.info(
            f"OptionsAgent.evaluate() called for {self.symbol}: "
            f"regime={signal.regime_type.value}, "
            f"confidence={signal.confidence:.2%}, "
            f"trend={signal.trend_direction.value}, "
            f"bias={signal.bias.value}, "
            f"volatility={signal.volatility_level.value}"
        )
        
        # CONFIG VALIDATION: Log effective runtime config
        logger.info(
            f"CONFIG LOADED: "
            f"min_confidence={self.min_confidence:.2%}, "
            f"min_iv={self.min_iv_percentile:.1%}, "
            f"max_iv={self.max_iv_percentile:.1%}, "
            f"dte_range=[{self.min_dte}, {self.max_dte}], "
            f"delta_range={self.delta_range}, "
            f"testing_mode={self.option_risk_profile.testing_mode}, "
            f"has_selector={self.options_selector is not None}, "
            f"has_data_feed={self.options_data_feed is not None}"
        )
        
        # Check basic requirements
        if signal.confidence < self.min_confidence:
            logger.debug(f"OptionsAgent: Confidence too low: {signal.confidence:.2%} < {self.min_confidence:.2%}")
            return []
        
        if not signal.is_valid:
            logger.debug(f"OptionsAgent: Regime not valid")
            return []
        
        # For PUT trades, we need bearish conditions
        is_bearish = (
            signal.trend_direction.value == "down"
            or (signal.regime_type.value == "expansion" and signal.bias.value == "short")
        )
        
        if not is_bearish:
            return []
        
        # Volatility check (options need some volatility)
        if signal.volatility_level.value == "low":
            return []
        
        # If we have options data feed, analyze specific options
        if self.options_data_feed:
            return self._analyze_options_chain(signal, market_state)
        
        # Otherwise, return generic PUT intent
        price = market_state.get("close", market_state.get("price", 0.0))
        if price <= 0:
            return []
        
        # Generic PUT trade intent
        # Note: This would need to be converted to actual option symbol later
        reason = (
            f"PUT opportunity: {signal.regime_type.value} regime, "
            f"{signal.bias.value} bias, confidence {signal.confidence:.2%}"
        )
        
        return [
            self._build_intent(
                direction=TradeDirection.SHORT,  # PUT = bearish
                size=1.0,  # Will be converted to contracts
                confidence=signal.confidence,
                reason=reason,
                metadata={
                    "option_type": "put",
                    "underlying_symbol": self.symbol,
                    "regime_type": signal.regime_type.value,
                    "volatility": signal.volatility_level.value,
                },
            )
        ]
    
    def _analyze_options_chain(
        self,
        signal: RegimeSignal,
        market_state: Mapping[str, float],
    ) -> List[TradeIntent]:
        """Analyze options chain for specific opportunities."""
        if not self.options_data_feed:
            return []
        
        try:
            # Get options chain for PUTs
            logger.info(f"OptionsAgent: Fetching options chain for {self.symbol} PUTs...")
            options_chain = self.options_data_feed.get_options_chain(
                underlying_symbol=self.symbol,
                option_type="put",
            )
            
            logger.info(f"OptionsAgent: Received {len(options_chain) if options_chain else 0} contracts from options chain")
            
            if not options_chain:
                logger.warning(f"OptionsAgent: No options chain returned for {self.symbol}")
                return []
            
            # Filter options by criteria
            current_price = market_state.get("close", 0.0)
            if current_price <= 0:
                return []
            
            # STEP 6: Use contract selector to find best option
            # First, get quotes and Greeks for all contracts
            logger.info(f"OptionsAgent: Fetching quotes and Greeks for {len(options_chain)} contracts...")
            quotes = {}
            greeks_dict = {}
            quotes_fetched = 0
            greeks_fetched = 0
            
            for option in options_chain:
                option_symbol = option.get("symbol", "")
                if not option_symbol:
                    continue
                
                quote = self.options_data_feed.get_option_quote(option_symbol)
                if quote:
                    quotes[option_symbol] = quote
                    quotes_fetched += 1
                    greek = self.options_data_feed.get_option_greeks(option_symbol)
                    if greek:
                        greeks_dict[option_symbol] = greek
                        greeks_fetched += 1
            
            logger.info(f"OptionsAgent: Fetched {quotes_fetched} quotes, {greeks_fetched} Greeks")
            
            # Use selector to pick best contract (if available)
            if self.options_selector and quotes and greeks_dict:
                target_delta = (self.delta_range[0] + self.delta_range[1]) / 2  # Mid-range delta
                logger.info(f"OptionsAgent: Using selector to pick best contract (target_delta={target_delta:.3f})")
                best_contract = self.options_selector.select_best_contract(
                    contracts=options_chain,
                    quotes=quotes,
                    greeks=greeks_dict,
                    target_delta=target_delta,
                    target_expiration=None,  # Could be passed from config
                    current_price=current_price,
                )
                
                if best_contract:
                    logger.info(f"OptionsAgent: Selector returned contract: {best_contract.get('symbol', 'unknown')}")
                    # STEP 5: Validate the selected contract
                    option_symbol = best_contract.get("symbol", "")
                    quote = best_contract.get("quote", {})
                    greek = best_contract.get("greeks", {})
                    
                    expiration = best_contract.get("expiration_date", "")
                    try:
                        exp_date = datetime.strptime(expiration, "%Y-%m-%d")
                        dte = (exp_date - datetime.now()).days
                    except:
                        dte = 0
                    
                    is_valid, reason = self.validate_option_contract(
                        contract=best_contract,
                        quote=quote,
                        greeks=greek,
                        current_price=current_price,
                        dte=dte,
                    )
                    
                    if is_valid:
                        logger.info(f"ACCEPT {option_symbol}: Validation passed, generating trade intent")
                        reason_text = (
                            f"PUT {best_contract.get('strike_price', 'unknown')} exp {expiration}: "
                            f"delta {greek.get('delta', 0):.2f}, IV {greek.get('implied_volatility', 0):.2%}"
                        )
                        return [
                            self._build_intent(
                                direction=TradeDirection.SHORT,
                                size=1.0,
                                confidence=signal.confidence,
                                reason=reason_text,
                                metadata={
                                    "option_symbol": option_symbol,
                                    "option_type": "put",
                                    "strike": best_contract.get("strike_price"),
                                    "expiration": expiration,
                                    "dte": dte,
                                    "delta": greek.get("delta"),
                                    "iv": greek.get("implied_volatility"),
                                },
                            )
                        ]
                    else:
                        logger.info(f"REJECT {option_symbol}: Selected contract failed validation: {reason}")
                else:
                    logger.info(f"OptionsAgent: Selector returned no contract, falling back to manual evaluation")
            else:
                logger.info(f"OptionsAgent: Selector not available or missing quotes/Greeks, using fallback")
            
            # Fallback: Manual contract evaluation
            logger.info(f"OptionsAgent: Fallback: Evaluating {len(options_chain)} contracts manually...")
            suitable_options = []
            candidates_evaluated = 0
            for option in options_chain:
                candidates_evaluated += 1
                strike = float(option.get("strike_price", 0))
                expiration = option.get("expiration_date", "")
                option_symbol = option.get("symbol", "")
                
                # Calculate days to expiration
                try:
                    exp_date = datetime.strptime(expiration, "%Y-%m-%d")
                    dte = (exp_date - datetime.now()).days
                except:
                    continue
                
                # Filter by DTE
                if dte < self.min_dte or dte > self.max_dte:
                    continue
                
                # Get option quote and Greeks
                quote = self.options_data_feed.get_option_quote(option_symbol)
                if not quote:
                    continue
                
                greeks = self.options_data_feed.get_option_greeks(option_symbol)
                if not greeks:
                    continue
                
                delta = greeks.get("delta", 0.0)
                iv = greeks.get("implied_volatility", 0.0)
                theta = greeks.get("theta", 0.0)
                gamma = greeks.get("gamma", 0.0)
                
                # STEP 2: Spread and liquidity filters
                bid = float(quote.get("bid", 0))
                ask = float(quote.get("ask", 0))
                open_interest = int(quote.get("open_interest", 0))
                volume = int(quote.get("volume", 0))
                
                if bid <= 0 or ask <= 0:
                    logger.debug(f"OptionsAgent: {option_symbol} - No bid/ask")
                    continue
                
                mid = (bid + ask) / 2
                spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 100.0
                theta_decay_pct = (abs(theta) / mid * 100) if mid > 0 and theta < 0 else 0.0
                
                # TRACE LOGGING: Log contract details before validation
                logger.info(
                    f"OptionsAgent: Evaluating contract {option_symbol}: "
                    f"strike={strike}, expiry={expiration}, DTE={dte}, "
                    f"bid={bid:.2f}, ask={ask:.2f}, mid={mid:.2f}, spread={spread_pct:.2f}%, "
                    f"OI={open_interest}, volume={volume}, "
                    f"delta={delta:.3f}, theta={theta:.4f} ({theta_decay_pct:.2f}%/day), "
                    f"gamma={gamma:.4f}, IV={iv:.2%}"
                )
                
                # Reject if spread too wide
                if spread_pct > self.option_risk_profile.max_spread_pct:
                    logger.debug(f"REJECT {option_symbol}: Spread too wide: {spread_pct:.2f}% > {self.option_risk_profile.max_spread_pct:.2f}%")
                    continue
                
                # Reject if open interest too low
                if open_interest < self.option_risk_profile.min_open_interest:
                    logger.debug(f"REJECT {option_symbol}: Open interest too low: {open_interest} < {self.option_risk_profile.min_open_interest}")
                    continue
                
                # Reject if volume too low
                if volume < self.option_risk_profile.min_volume:
                    logger.debug(f"REJECT {option_symbol}: Volume too low: {volume} < {self.option_risk_profile.min_volume}")
                    continue
                
                # Check delta range (for PUTs, should be negative)
                delta_min, delta_max = self.delta_range
                if delta < delta_min or delta > delta_max:
                    continue
                
                # Check IV percentile (if available)
                # For now, we'll use IV directly
                if iv < (self.min_iv_percentile / 100.0) or iv > (self.max_iv_percentile / 100.0):
                    continue
                
                # STEP 4: Theta & gamma risk models
                # Check theta decay risk
                if mid > 0:
                    theta_decay_pct = abs(theta) / mid if theta < 0 else 0.0
                    if theta_decay_pct > self.option_risk_profile.max_theta_decay_allowed:
                        continue  # Too much time decay risk
                
                # Check gamma risk (high gamma = more volatile position)
                # For now, we'll use a simple threshold
                if abs(gamma) > 0.10:  # High gamma = restrict position size later
                    pass  # Will handle in position sizing
                
                # Calculate profit potential
                bid = float(quote.get("bid", 0))
                ask = float(quote.get("ask", 0))
                mid = (bid + ask) / 2 if bid > 0 and ask > 0 else 0
                
                if mid <= 0:
                    continue
                
                # Estimate profit if price moves down
                # This is simplified - real calculation would use Greeks
                price_move_pct = abs(delta) * 0.05  # 5% underlying move
                estimated_profit_pct = (price_move_pct * abs(delta) * 100) / mid if mid > 0 else 0
                
                if estimated_profit_pct < 0.50:  # Need at least 50% profit potential
                    continue
                
                suitable_options.append({
                    "symbol": option_symbol,
                    "strike": strike,
                    "expiration": expiration,
                    "dte": dte,
                    "delta": delta,
                    "iv": iv,
                    "mid_price": mid,
                    "estimated_profit_pct": estimated_profit_pct,
                })
            
            # Sort by profit potential
            suitable_options.sort(key=lambda x: x["estimated_profit_pct"], reverse=True)
            
            # Return top opportunity
            if suitable_options:
                best_option = suitable_options[0]
                reason = (
                    f"PUT {best_option['strike']} exp {best_option['expiration']}: "
                    f"delta {best_option['delta']:.2f}, IV {best_option['iv']:.2%}, "
                    f"profit potential {best_option['estimated_profit_pct']:.1%}"
                )
                
                return [
                    self._build_intent(
                        direction=TradeDirection.SHORT,
                        size=1.0,  # Number of contracts
                        confidence=signal.confidence,
                        reason=reason,
                        metadata={
                            "option_symbol": best_option["symbol"],
                            "option_type": "put",
                            "strike": best_option["strike"],
                            "expiration": best_option["expiration"],
                            "dte": best_option["dte"],
                            "delta": best_option["delta"],
                            "iv": best_option["iv"],
                            "entry_price": best_option["mid_price"],
                            "estimated_profit_pct": best_option["estimated_profit_pct"],
                        },
                    )
                ]
            
            logger.info(f"OptionsAgent: No suitable options found after evaluating {candidates_evaluated} candidates")
            return []
        except Exception as e:
            logger.error(f"Error analyzing options chain: {e}", exc_info=True)
            return []
    
    def _check_agent_alignment(self, signal: RegimeSignal) -> bool:
        """
        STEP 3: Check if underlying trend agents are aligned.
        
        For options, we need multiple agents to agree before trading.
        """
        # Count how many agents are aligned
        alignment_count = 0
        alignment_details = []
        
        # Check trend agent signal
        if self.trend_agent_signal:
            if self.trend_agent_signal.direction == TradeDirection.SHORT:
                if signal.trend_direction.value == "down":
                    alignment_count += 1
                    alignment_details.append("trend_agent: SHORT aligned with DOWN trend")
                else:
                    alignment_details.append(f"trend_agent: SHORT but trend is {signal.trend_direction.value}")
            else:
                alignment_details.append(f"trend_agent: {self.trend_agent_signal.direction.value} (not SHORT)")
        else:
            alignment_details.append("trend_agent: no signal")
        
        # Check mean reversion agent signal
        if self.mean_reversion_agent_signal:
            if signal.regime_type.value == "mean_reversion":
                alignment_count += 1
                alignment_details.append("mean_reversion_agent: aligned with MR regime")
            else:
                alignment_details.append(f"mean_reversion_agent: regime is {signal.regime_type.value} (not MR)")
        else:
            alignment_details.append("mean_reversion_agent: no signal")
        
        # Check volatility agent signal
        if self.volatility_agent_signal:
            if signal.volatility_level.value in ["medium", "high"]:
                alignment_count += 1
                alignment_details.append(f"volatility_agent: aligned with {signal.volatility_level.value} volatility")
            else:
                alignment_details.append(f"volatility_agent: volatility is {signal.volatility_level.value} (not MEDIUM/HIGH)")
        else:
            alignment_details.append("volatility_agent: no signal")
        
        # Require at least 2 out of 3 agents to align (or 1 of 3 in testing mode)
        required_alignment = 1 if self.option_risk_profile.testing_mode else 2
        if self.trend_agent_signal and self.mean_reversion_agent_signal and self.volatility_agent_signal:
            # Still require 2 out of 3 in production, 1 out of 3 in testing
            required_alignment = 1 if self.option_risk_profile.testing_mode else 2
        
        is_aligned = alignment_count >= required_alignment
        
        logger.debug(
            f"OptionsAgent: Agent alignment: {alignment_count}/{required_alignment} required. "
            f"Details: {'; '.join(alignment_details)}"
        )
        
        return is_aligned
    
    def validate_option_contract(
        self,
        contract: Dict,
        quote: Dict,
        greeks: Dict,
        current_price: float,
        dte: int,
    ) -> tuple[bool, str]:
        """
        STEP 5: Pre-trade sanity check for option contract.
        
        Returns:
            (is_valid, reason)
        """
        # Check liquidity
        bid = float(quote.get("bid", 0))
        ask = float(quote.get("ask", 0))
        open_interest = int(quote.get("open_interest", 0))
        volume = int(quote.get("volume", 0))
        
        if bid <= 0 or ask <= 0:
            return False, "No bid/ask"
        
        mid = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 100.0
        
        if spread_pct > self.option_risk_profile.max_spread_pct:
            return False, f"Spread too wide: {spread_pct:.2f}%"
        
        if open_interest < self.option_risk_profile.min_open_interest:
            return False, f"Open interest too low: {open_interest}"
        
        if volume < self.option_risk_profile.min_volume:
            return False, f"Volume too low: {volume}"
        
        # Check expiration suitability
        if dte < self.option_risk_profile.min_dte_for_entry:
            return False, f"Too close to expiration: {dte} days"
        
        if dte > self.option_risk_profile.max_dte_for_entry:
            return False, f"Too far from expiration: {dte} days"
        
        # Check theta risk
        theta = greeks.get("theta", 0.0)
        if mid > 0:
            theta_decay_pct = abs(theta) / mid if theta < 0 else 0.0
            if theta_decay_pct > self.option_risk_profile.max_theta_decay_allowed:
                return False, f"Theta decay too high: {theta_decay_pct:.2%}"
        
        # Check delta range
        delta = greeks.get("delta", 0.0)
        delta_min, delta_max = self.delta_range
        if delta < delta_min or delta > delta_max:
            return False, f"Delta out of range: {delta:.2f} not in [{delta_min}, {delta_max}]"
        
        # Check IV range
        iv = greeks.get("implied_volatility", 0.0)
        if iv < (self.min_iv_percentile / 100.0) or iv > (self.max_iv_percentile / 100.0):
            return False, f"IV out of range: {iv:.2%} not in [{self.min_iv_percentile}%, {self.max_iv_percentile}%]"
        
        # Check premium limit
        if mid > self.option_risk_profile.max_premium_per_trade:
            return False, f"Premium too high: ${mid:.2f} > ${self.option_risk_profile.max_premium_per_trade:.2f}"
        
        # TRACE LOGGING: Log successful validation
        logger.info(
            f"ACCEPT {contract.get('symbol', 'unknown')}: Validation passed - "
            f"spread={spread_pct:.2f}%, OI={open_interest}, volume={volume}, "
            f"delta={delta:.3f}, DTE={dte}, IV={iv:.2%}, premium=${mid:.2f}"
        )
        
        return True, "OK"

