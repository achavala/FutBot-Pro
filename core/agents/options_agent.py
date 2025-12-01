"""Options trading agent for analyzing and trading options."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Mapping, Optional

from core.agents.base import BaseAgent, TradeDirection, TradeIntent
from core.config.asset_profiles import OptionRiskProfile
from core.regime.types import RegimeSignal
from core.regime.microstructure import MarketMicrostructure

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
        
        # PERFORMANCE: Lower confidence threshold for more trades (especially 0DTE)
        # Use risk profile testing_mode to determine threshold
        default_confidence = 0.30 if self.option_risk_profile.testing_mode else 0.50
        self.min_confidence = float(self.config.get("min_confidence", default_confidence))
        self.min_iv_percentile = self.option_risk_profile.min_iv_percentile
        self.max_iv_percentile = self.option_risk_profile.max_iv_percentile
        
        # IV Rank/Percentile thresholds (institutional edge)
        self.iv_percentile_buy_threshold = 20.0  # Buy options when IV < 20th percentile (cheap)
        self.iv_percentile_sell_threshold = 80.0  # Sell premium when IV > 80th percentile (expensive)
        self.min_dte = self.option_risk_profile.min_dte_for_entry
        self.max_dte = self.option_risk_profile.max_dte_for_entry
        self.delta_range = self.option_risk_profile.delta_range
        
        # STEP 6: Contract selection engine
        if OptionsSelector is not None:
            self.options_selector = OptionsSelector(self.option_risk_profile)
        else:
            self.options_selector = None
        
        # IV percentile tracking (for GEX v2 confidence adjustment)
        self.iv_percentile: Optional[float] = None
    
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
        # Helper to safely get enum value
        def get_enum_val(e):
            return e.value if hasattr(e, 'value') and not isinstance(e, str) else str(e)
        
        logger.info(
            f"OptionsAgent.evaluate() called for {self.symbol}: "
            f"regime={get_enum_val(signal.regime_type)}, "
            f"confidence={signal.confidence:.2%}, "
            f"trend={get_enum_val(signal.trend_direction)}, "
            f"bias={get_enum_val(signal.bias)}, "
            f"volatility={get_enum_val(signal.volatility_level)}"
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
        # PERFORMANCE: More lenient confidence check for 0DTE trading
        # In testing mode, allow lower confidence (15% minimum)
        min_effective_confidence = 0.15 if self.option_risk_profile.testing_mode else self.min_confidence
        if signal.confidence < min_effective_confidence:
            logger.debug(f"OptionsAgent: Confidence too low: {signal.confidence:.2%} < {min_effective_confidence:.2%}")
            return []
        
        if not signal.is_valid:
            logger.debug(f"OptionsAgent: Regime not valid")
            return []
        
        # Helper to safely get enum value
        def get_enum_val(e):
            return e.value if hasattr(e, 'value') and not isinstance(e, str) else str(e)
        
        # Determine trade direction based on regime and bias
        trend_val = get_enum_val(signal.trend_direction)
        regime_val = get_enum_val(signal.regime_type)
        bias_val = get_enum_val(signal.bias)
        vol_val = get_enum_val(signal.volatility_level)
        
        # Determine if we should trade CALL (bullish) or PUT (bearish)
        is_bearish = (
            trend_val == "down"
            or (regime_val == "expansion" and bias_val == "short")
            or bias_val == "short"
        )
        
        is_bullish = (
            trend_val == "up"
            or (regime_val == "trend" and bias_val == "long")
            or bias_val == "long"
        )
        
        # If neither bullish nor bearish, skip
        if not is_bullish and not is_bearish:
            return []
        
        # Volatility check (options need some volatility)
        if vol_val == "low":
            return []
        
        # Determine option type and direction
        option_type = "put" if is_bearish else "call"
        trade_direction = TradeDirection.LONG  # Always buy options (long calls or long puts)
        
        # If we have options data feed, analyze specific options
        if self.options_data_feed:
            return self._analyze_options_chain(signal, market_state)
        
        # Otherwise, return generic options intent with synthetic pricing
        price = market_state.get("close", market_state.get("price", 0.0))
        if price <= 0:
            return []
        
        # PERFORMANCE: Prefer 0DTE for faster trades (testing mode) or medium+ confidence
        # 0DTE is preferred for aggressive strategies
        if self.option_risk_profile.testing_mode:
            dte = 0  # Always use 0DTE in testing mode for speed
        else:
            dte = 0 if signal.confidence > 0.6 else 1  # 0DTE for medium+ confidence, 1DTE otherwise
        
        # Build reason string
        reason = (
            f"{option_type.upper()} opportunity: {regime_val} regime, "
            f"{bias_val} bias, confidence {signal.confidence:.2%}"
        )
        
        return [
            self._build_intent(
                direction=trade_direction,  # LONG for buying options
                size=1.0,  # Number of contracts (will be scaled by position sizing)
                confidence=signal.confidence,
                reason=reason,
                metadata={
                    "option_type": option_type,
                    "underlying_symbol": self.symbol,
                    "regime_type": regime_val,
                    "volatility": vol_val,
                },
                instrument_type="option",  # Mark as options trade
                option_type=option_type,  # "call" or "put"
                moneyness="atm",  # At-the-money
                time_to_expiry_days=dte,  # Days to expiration
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
                        # Apply Greeks-based regime filter to selected contract
                        delta = greek.get("delta", 0.0)
                        gamma = greek.get("gamma", 0.0)
                        theta = greek.get("theta", 0.0)
                        iv = greek.get("implied_volatility", 0.0)
                        
                        abs_delta = abs(delta)
                        abs_gamma = abs(gamma)
                        
                        # A) Basic Greeks filter
                        if abs_delta < 0.30:
                            logger.info(f"REJECT {option_symbol}: Delta too low ({delta:.3f}) after validation")
                            return []  # Not in a loop, so return empty list
                        if abs_gamma > 0.15:
                            logger.info(f"REJECT {option_symbol}: Gamma too high ({gamma:.4f}) after validation")
                            return []  # Not in a loop, so return empty list
                        
                        # B) Advanced: High-conviction boost
                        confidence_multiplier = 1.0
                        is_high_conviction = False
                        is_low_iv = False
                        
                        if abs_delta > 0.70 and abs_gamma < 0.05:
                            is_high_conviction = True
                            confidence_multiplier = 1.5
                            logger.info(f"✅ HIGH-CONVICTION {option_symbol}: delta={delta:.3f}, gamma={gamma:.4f}")
                        elif abs_delta > 0.50 and abs_gamma < 0.08:
                            confidence_multiplier = 1.2
                        
                        # IV percentile boost
                        if iv_percentile is not None and iv_percentile < self.iv_percentile_buy_threshold:
                            is_low_iv = True
                            confidence_multiplier *= 1.3  # 30% boost for cheap premium
                            logger.info(f"✅ LOW IV BOOST {option_symbol}: IV percentile={iv_percentile:.1f}% (cheap premium)")
                        
                        # C) Auto-regime adjustment
                        from core.agents.base import get_enum_val
                        regime_type = get_enum_val(signal.regime_type)
                        volatility_level = get_enum_val(signal.volatility_level)
                        
                        regime_adjusted_confidence = signal.confidence * confidence_multiplier
                        
                        if regime_type == "trend" and abs_delta < 0.40:
                            logger.info(f"REJECT {option_symbol}: Trend regime requires delta >= 0.40")
                            return []  # Not in a loop, so return empty list
                        elif regime_type == "compression" and abs_delta < 0.25:
                            logger.info(f"REJECT {option_symbol}: Compression regime requires delta >= 0.25")
                            return []  # Not in a loop, so return empty list
                        elif regime_type == "expansion" and abs_delta < 0.30:
                            logger.info(f"REJECT {option_symbol}: Expansion regime requires delta >= 0.30")
                            return []  # Not in a loop, so return empty list
                        
                        if volatility_level == "high" and abs_gamma > 0.10:
                            logger.info(f"REJECT {option_symbol}: High volatility requires gamma <= 0.10")
                            return []  # Not in a loop, so return empty list
                        
                        if regime_adjusted_confidence < self.min_confidence:
                            logger.info(f"REJECT {option_symbol}: Regime-adjusted confidence too low")
                            return []  # Not in a loop, so return empty list
                        
                        logger.info(
                            f"✅ GREEKS + IV FILTER PASSED {option_symbol}: "
                            f"delta={delta:.3f}, gamma={gamma:.4f}, "
                            f"IV percentile={iv_percentile:.1f}% " if iv_percentile is not None else "",
                            f"confidence={regime_adjusted_confidence:.2%}"
                        )
                        
                        iv_info = f", IV percentile={iv_percentile:.1f}%" if iv_percentile is not None else ""
                        if is_low_iv:
                            iv_info += " [LOW IV - CHEAP PREMIUM]"
                        
                        # Get GEX data from microstructure for display
                        gex_info = ""
                        try:
                            microstructure = MarketMicrostructure()
                            gex_data_selector = microstructure.get(self.symbol)
                            if gex_data_selector.get('gex_coverage', 0) > 0:
                                gex_regime_display = gex_data_selector.get('gex_regime', 'NEUTRAL')
                                gex_strength_display = gex_data_selector.get('gex_strength', 0.0)
                                gex_info = f", GEX={gex_regime_display} (${gex_strength_display:.2f}B)"
                                if gex_strength_display > 2.0:
                                    gex_info += " [STRONG GEX]"
                        except Exception:
                            pass  # GEX info is optional
                        
                        reason_text = (
                            f"PUT {best_contract.get('strike_price', 'unknown')} exp {expiration}: "
                            f"delta {delta:.2f}, IV {iv:.2%}{iv_info}{gex_info}"
                            f"{' [HIGH-CONVICTION]' if is_high_conviction else ''}"
                        )
                        return [
                            self._build_intent(
                                direction=TradeDirection.LONG,  # Buying PUT options
                                size=1.0,
                                confidence=regime_adjusted_confidence,  # Use adjusted confidence
                                reason=reason_text,
                                metadata={
                                    "option_symbol": option_symbol,
                                    "option_type": "put",
                                    "strike": best_contract.get("strike_price"),
                                    "expiration": expiration,
                                    "dte": dte,
                                    "delta": delta,
                                    "gamma": gamma,
                                    "theta": theta,
                                    "iv": iv,
                                    "iv_percentile": iv_percentile,
                                    "high_conviction": is_high_conviction,
                                    "low_iv": is_low_iv,
                                    "greeks_filter_applied": True,
                                    "iv_percentile_filter_applied": iv_percentile is not None,
                                },
                                instrument_type="option",
                                option_type="put",
                                moneyness="atm",
                                time_to_expiry_days=dte,
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
                
                # ============================================================
                # STEP 5: IV RANK/PERCENTILE FILTER (INSTITUTIONAL EDGE #2)
                # ============================================================
                # This is the #1 edge in options trading:
                # - IV Percentile < 20% = IV is low (good time to BUY options)
                # - IV Percentile > 80% = IV is high (good time to SELL premium)
                
                iv_percentile = None
                iv_rank = None
                
                # Calculate IV percentile if options data feed is available
                if self.options_data_feed and iv > 0:
                    try:
                        iv_percentile = self.options_data_feed.calculate_iv_percentile(
                            underlying_symbol=self.symbol,
                            current_iv=iv,
                            lookback_days=252,  # 1 year
                            option_type="put",  # We're evaluating PUT options in this context
                        )
                        if iv_percentile is not None:
                            # Store IV percentile as instance attribute for GEX v2 logic
                            self.iv_percentile = iv_percentile
                            logger.debug(
                                f"IV Percentile for {option_symbol}: {iv_percentile:.1f}% "
                                f"(current IV={iv:.2%})"
                            )
                    except Exception as e:
                        logger.debug(f"Could not calculate IV percentile: {e}")
                        self.iv_percentile = None
                
                # Apply IV percentile filter
                if iv_percentile is not None:
                    # For buying options (long calls/puts): prefer low IV
                    # For selling premium: prefer high IV
                    # Since we're buying options here, we want low IV percentile
                    if iv_percentile > self.iv_percentile_sell_threshold:
                        # IV is very high (>80th percentile) - not good for buying options
                        # This is a premium-selling opportunity, not a buying opportunity
                        logger.debug(
                            f"REJECT {option_symbol}: IV percentile too high ({iv_percentile:.1f}%) "
                            f"- better for selling premium, not buying"
                        )
                        continue
                    elif iv_percentile < self.iv_percentile_buy_threshold:
                        # IV is very low (<20th percentile) - excellent for buying options
                        # Boost confidence for cheap premium
                        logger.info(
                            f"✅ LOW IV OPPORTUNITY {option_symbol}: "
                            f"IV percentile={iv_percentile:.1f}% (cheap premium) - confidence boost"
                        )
                        # Will apply confidence boost later
                    elif iv_percentile > 50.0:
                        # IV is above median - less attractive for buying
                        logger.debug(
                            f"REJECT {option_symbol}: IV percentile above median ({iv_percentile:.1f}%) "
                            f"- premium is expensive"
                        )
                        continue
                
                # ============================================================
                # STEP 6: GEX PROXY FILTER (INSTITUTIONAL EDGE #3)
                # ============================================================
                # Gamma Exposure (GEX) measures dealer positioning:
                # - POSITIVE GEX: Dealers long gamma → market pins, volatility dies → good for longs
                # - NEGATIVE GEX: Dealers short gamma → volatility explosions → REJECT ALL TRADES
                #
                # This is used by every major volatility fund (Citadel, Jane Street, Optiver, SIG).
                
                gex_data = None
                if self.options_data_feed and options_chain:
                    try:
                        # Prepare chain data for GEX calculation
                        chain_for_gex = []
                        for opt in options_chain[:100]:  # Sample up to 100 contracts for speed
                            option_symbol_gex = opt.get("symbol", "")
                            if not option_symbol_gex:
                                continue
                            
                            # Get quote and Greeks for GEX calculation
                            quote_gex = self.options_data_feed.get_option_quote(option_symbol_gex)
                            greeks_gex = self.options_data_feed.get_option_greeks(option_symbol_gex)
                            
                            if quote_gex and greeks_gex:
                                chain_for_gex.append({
                                    'strike_price': opt.get('strike_price', 0),
                                    'option_type': opt.get('option_type', 'put'),
                                    'symbol': option_symbol_gex,
                                    'gamma': greeks_gex.get('gamma', 0),
                                    'open_interest': quote_gex.get('open_interest', 0),
                                })
                        
                        if chain_for_gex:
                            gex_data = self.options_data_feed.calculate_gex_proxy(
                                chain_data=chain_for_gex,
                                underlying_price=current_price,
                            )
                            
                            if gex_data:
                                logger.debug(
                                    f"GEX Proxy for {self.symbol}: "
                                    f"regime={gex_data['gex_regime']}, "
                                    f"strength=${gex_data['gex_strength']:.2f}B, "
                                    f"total=${gex_data['total_gex_dollar']:,.0f}"
                                )
                    except Exception as e:
                        logger.debug(f"Could not calculate GEX proxy: {e}")
                
                # GEX Proxy Filter (Soft Regime Modifier - Not Hard Reject)
                # ======================
                # GEX v2 CONFIDENCE LAYER
                # ======================
                # Try multiple sources for GEX data (priority order):
                # 1. RegimeSignal (from Market Microstructure Snapshot) - preferred
                # 2. MarketMicrostructure singleton - real-time updated
                # 3. Inline calculated gex_data - fallback
                
                gex_regime = None
                gex_strength = None
                total_gex_dollar = None
                
                # Priority 1: RegimeSignal (from scheduler's Market Microstructure Snapshot)
                if hasattr(signal, 'gex_regime') and signal.gex_regime:
                    gex_regime = signal.gex_regime
                    gex_strength = signal.gex_strength
                    total_gex_dollar = signal.total_gex_dollar
                    logger.debug(
                        f"[GEX] Using GEX from RegimeSignal: regime={gex_regime}, "
                        f"strength={gex_strength:.2f}B, total=${total_gex_dollar:,.0f}"
                    )
                else:
                    # Priority 2: MarketMicrostructure singleton (real-time updated)
                    microstructure = MarketMicrostructure()
                    gex_from_micro = microstructure.get(self.symbol)  # Use self.symbol, not symbol
                    if gex_from_micro.get('gex_coverage', 0) > 0:
                        gex_regime = gex_from_micro['gex_regime']
                        gex_strength = gex_from_micro['gex_strength']
                        total_gex_dollar = gex_from_micro['total_gex_dollar']
                        logger.debug(
                            f"[GEX] Using GEX from MarketMicrostructure: regime={gex_regime}, "
                            f"strength={gex_strength:.2f}B"
                        )
                    elif gex_data:
                        # Priority 3: Fallback to inline calculated GEX
                        gex_regime = gex_data.get('gex_regime')
                        gex_strength = gex_data.get('gex_strength')
                        total_gex_dollar = gex_data.get('total_gex_dollar')
                        logger.debug(
                            f"[GEX] Using inline calculated GEX: regime={gex_regime}, "
                            f"strength={gex_strength:.2f}B"
                        )
                
                # ======================
                # GEX v2 CONFIDENCE LAYER
                # ======================
                gex_confidence_multiplier = 1.0
                if gex_strength is not None and gex_strength > 1.0:
                    # POSITIVE GEX → Pinning → Damp
                    if gex_regime == "POSITIVE" and gex_strength > 1.5:
                        gex_confidence_multiplier = 0.75
                        logger.info(
                            f"[GEX DAMPEN] POSITIVE {gex_strength:.2f}B → pinning risk → confidence -25%"
                        )
                    # NEGATIVE GEX → Expansion
                    elif gex_regime == "NEGATIVE":
                        if iv_percentile is not None and iv_percentile < 25:
                            gex_confidence_multiplier = 1.30
                            logger.info(
                                f"[GEX BOOST] NEGATIVE GEX + cheap IV → volatility expansion edge → +30%"
                            )
                        else:
                            gex_confidence_multiplier = 0.80
                            logger.info(
                                f"[GEX CAUTION] NEGATIVE GEX but IV high → -20%"
                            )
                
                # Clamp
                gex_confidence_multiplier = max(0.01, min(gex_confidence_multiplier, 2.0))
                
                # Fallback: Use absolute IV range if percentile not available
                if iv_percentile is None:
                    if iv < (self.min_iv_percentile / 100.0) or iv > (self.max_iv_percentile / 100.0):
                        logger.debug(f"REJECT {option_symbol}: IV out of range ({iv:.2%})")
                        continue
                
                # ============================================================
                # STEP 4: GREEKS-BASED REGIME FILTER (INSTITUTIONAL-GRADE)
                # ============================================================
                # This filter uses Greeks to validate trade quality based on:
                # 1. Delta conviction (directional strength)
                # 2. Gamma risk (volatility sensitivity)
                # 3. Theta decay (time decay risk)
                # 4. Regime-specific thresholds
                
                # Get current regime for adaptive filtering
                from core.agents.base import get_enum_val
                regime_type = get_enum_val(signal.regime_type)
                volatility_level = get_enum_val(signal.volatility_level)
                
                # A) BASIC GREEKS FILTER - Core validation
                # High delta = strong directional conviction
                # Low gamma = lower volatility risk
                # Reasonable theta = manageable time decay
                
                abs_delta = abs(delta)
                abs_gamma = abs(gamma)
                abs_theta = abs(theta)
                
                # Basic delta conviction check
                if abs_delta < 0.30:
                    logger.debug(f"REJECT {option_symbol}: Delta too low ({delta:.3f}) - weak directional conviction")
                    continue
                
                # Basic gamma risk check (high gamma = dangerous)
                if abs_gamma > 0.15:
                    logger.debug(f"REJECT {option_symbol}: Gamma too high ({gamma:.4f}) - excessive volatility risk")
                    continue
                
                # Basic theta decay check
                if mid > 0:
                    theta_decay_pct = abs_theta / mid if theta < 0 else 0.0
                    if theta_decay_pct > self.option_risk_profile.max_theta_decay_allowed:
                        logger.debug(f"REJECT {option_symbol}: Theta decay too high ({theta_decay_pct:.2%})")
                        continue
                
                # B) ADVANCED GREEKS FILTER - High-conviction boost
                # Delta > 0.7 + low gamma = extremely strong trend conviction
                # This is the "institutional edge" - most bots ignore this
                
                high_conviction = False
                confidence_multiplier = 1.0
                
                if abs_delta > 0.70 and abs_gamma < 0.05:
                    # Extremely high directional conviction with low gamma risk
                    high_conviction = True
                    confidence_multiplier = 1.5  # 50% confidence boost
                    logger.info(
                        f"✅ HIGH-CONVICTION OPTION {option_symbol}: "
                        f"delta={delta:.3f} (strong), gamma={gamma:.4f} (low risk), "
                        f"confidence boost: {confidence_multiplier}x"
                    )
                elif abs_delta > 0.50 and abs_gamma < 0.08:
                    # Good conviction with manageable gamma
                    confidence_multiplier = 1.2  # 20% confidence boost
                    logger.debug(f"✅ Good-conviction option {option_symbol}: delta={delta:.3f}, gamma={gamma:.4f}")
                
                # C) AUTO-REGIME GREEKS FILTER - Adaptive thresholds per regime
                # Different regimes require different Greeks profiles
                
                # Start with base confidence and apply Greeks multiplier
                regime_adjusted_confidence = signal.confidence * confidence_multiplier
                
                # Apply GEX confidence modifier (calculated earlier in the loop)
                regime_adjusted_confidence *= gex_confidence_multiplier
                
                if regime_type == "trend":
                    # In TREND regime: prefer high delta, low gamma
                    # We want strong directional plays
                    if abs_delta < 0.40:
                        logger.debug(f"REJECT {option_symbol}: Trend regime requires delta >= 0.40, got {delta:.3f}")
                        continue
                    # Boost confidence for high-delta options in trends
                    if abs_delta > 0.60:
                        regime_adjusted_confidence *= 1.1
                
                elif regime_type == "compression":
                    # In COMPRESSION: prefer lower delta, higher gamma (for volatility plays)
                    # But still need some conviction
                    if abs_delta < 0.25:
                        logger.debug(f"REJECT {option_symbol}: Compression regime requires delta >= 0.25, got {delta:.3f}")
                        continue
                    # In compression, we might want to sell premium (negative theta)
                    # For now, we'll allow both but note it
                    if theta > 0:  # Positive theta = selling premium
                        regime_adjusted_confidence *= 1.15  # Boost for premium selling in compression
                
                elif regime_type == "expansion":
                    # In EXPANSION: prefer moderate delta, moderate gamma
                    # Volatility is expanding, so gamma risk is acceptable
                    if abs_delta < 0.30:
                        logger.debug(f"REJECT {option_symbol}: Expansion regime requires delta >= 0.30, got {delta:.3f}")
                        continue
                    # Higher gamma is OK in expansion (volatility is the play)
                    if abs_gamma > 0.12:
                        logger.debug(f"REJECT {option_symbol}: Expansion regime: gamma too high ({gamma:.4f})")
                        continue
                
                # Volatility-level adjustments
                if volatility_level == "high":
                    # High volatility: prefer lower gamma (less risk)
                    if abs_gamma > 0.10:
                        logger.debug(f"REJECT {option_symbol}: High volatility requires gamma <= 0.10, got {gamma:.4f}")
                        continue
                elif volatility_level == "low":
                    # Low volatility: can accept higher gamma (volatility expansion play)
                    if abs_gamma > 0.15:
                        logger.debug(f"REJECT {option_symbol}: Low volatility: gamma too high ({gamma:.4f})")
                        continue
                
                # Final confidence check with regime-adjusted confidence
                if regime_adjusted_confidence < self.min_confidence:
                    logger.debug(
                        f"REJECT {option_symbol}: Regime-adjusted confidence too low: "
                        f"{regime_adjusted_confidence:.2%} < {self.min_confidence:.2%}"
                    )
                    continue
                
                # Log successful Greeks filter pass
                logger.info(
                    f"✅ GREEKS FILTER PASSED {option_symbol}: "
                    f"delta={delta:.3f}, gamma={gamma:.4f}, theta={theta:.4f}, "
                    f"regime={regime_type}, vol={volatility_level}, "
                    f"confidence={regime_adjusted_confidence:.2%} "
                    f"({'HIGH-CONVICTION' if high_conviction else 'standard'})"
                )
                
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
                    "gamma": gamma,
                    "theta": theta,
                    "vega": greeks.get("vega", 0.0),
                    "iv": iv,
                    "iv_percentile": iv_percentile,  # Store IV percentile for sorting
                    "gex_data": gex_data,  # Store GEX data for sorting
                    "mid_price": mid,
                    "estimated_profit_pct": estimated_profit_pct,
                    "adjusted_confidence": regime_adjusted_confidence,  # Store final adjusted confidence
                })
            
            # Sort by multiple factors (prioritize best opportunities)
            # Priority order (The Holy Grail Filter Chain):
            # 1. High-conviction (delta > 0.7, gamma < 0.05)
            # 2. Positive GEX (dealers long gamma = pinning)
            # 3. Low IV percentile (< 20%) - cheap premium
            # 4. Profit potential
            suitable_options.sort(
                key=lambda x: (
                    # Primary: High-conviction flag
                    not (abs(x["delta"]) > 0.70 and abs(x.get("gamma", 0)) < 0.05),
                    # Secondary: Positive GEX (dealers long gamma)
                    not (x.get("gex_data") and x["gex_data"].get("gex_regime") == "POSITIVE" and x["gex_data"].get("gex_strength", 0) > 2.0),
                    # Tertiary: Low IV percentile (cheap premium)
                    x.get("iv_percentile", 100.0) if x.get("iv_percentile") is not None else 100.0,
                    # Quaternary: Profit potential (negative for reverse sort)
                    -x["estimated_profit_pct"]
                )
            )
            
            # Return top opportunity
            if suitable_options:
                best_option = suitable_options[0]
                
                # Use the stored adjusted confidence (already includes Greeks, GEX, IV, and regime adjustments)
                # This avoids recalculating and ensures consistency with the filter chain
                final_confidence = min(1.0, best_option.get("adjusted_confidence", signal.confidence))
                
                # Extract values for logging/reason string
                abs_delta = abs(best_option["delta"])
                abs_gamma = abs(best_option.get("gamma", 0))
                is_high_conviction = abs_delta > 0.70 and abs_gamma < 0.05
                iv_percentile = best_option.get("iv_percentile")
                is_low_iv = iv_percentile is not None and iv_percentile < self.iv_percentile_buy_threshold
                gex_data = best_option.get("gex_data")
                has_strong_gex = gex_data and gex_data.get("gex_regime") == "POSITIVE" and gex_data.get("gex_strength", 0) > 2.0
                
                # Build reason string with full filter chain info
                iv_info = ""
                if iv_percentile is not None:
                    iv_info = f", IV percentile={iv_percentile:.1f}%"
                    if is_low_iv:
                        iv_info += " [LOW IV - CHEAP PREMIUM]"
                
                gex_info = ""
                # Use GEX from RegimeSignal if available, otherwise use calculated
                gex_regime_display = None
                gex_strength_display = None
                
                if hasattr(signal, 'gex_regime') and signal.gex_regime:
                    gex_regime_display = signal.gex_regime
                    gex_strength_display = signal.gex_strength
                elif gex_data:
                    gex_regime_display = gex_data.get("gex_regime")
                    gex_strength_display = gex_data.get("gex_strength")
                
                if gex_regime_display and gex_strength_display is not None:
                    gex_info = f", GEX={gex_regime_display} (${gex_strength_display:.2f}B)"
                    if gex_regime_display == "POSITIVE" and gex_strength_display > 1.5:
                        gex_info += " [PINNING]"
                    elif gex_regime_display == "NEGATIVE" and gex_strength_display > 1.5:
                        gex_info += " [SHORT-GAMMA BOOST]"
                
                reason = (
                    f"PUT {best_option['strike']} exp {best_option['expiration']}: "
                    f"delta {best_option['delta']:.2f}, IV {best_option['iv']:.2%}{iv_info}{gex_info}, "
                    f"profit potential {best_option['estimated_profit_pct']:.1%}"
                    f"{' [HIGH-CONVICTION]' if is_high_conviction else ''}"
                )
                
                return [
                    self._build_intent(
                        direction=TradeDirection.LONG,  # Buying PUT options
                        size=1.0,  # Number of contracts
                        confidence=final_confidence,  # Use regime-adjusted confidence
                        reason=reason,
                        metadata={
                            "option_symbol": best_option["symbol"],
                            "option_type": "put",
                            "strike": best_option["strike"],
                            "expiration": best_option["expiration"],
                            "dte": best_option["dte"],
                            "delta": best_option["delta"],
                            "gamma": best_option.get("gamma", 0),
                            "theta": best_option.get("theta", 0),
                            "iv": best_option["iv"],
                            "iv_percentile": iv_percentile,
                            "gex_data": gex_data,  # Full GEX data for analytics
                            "gex_regime": gex_data.get("gex_regime") if gex_data else None,
                            "gex_strength": gex_data.get("gex_strength") if gex_data else None,
                            "entry_price": best_option["mid_price"],
                            "estimated_profit_pct": best_option["estimated_profit_pct"],
                            "high_conviction": is_high_conviction,
                            "low_iv": is_low_iv,
                            "strong_gex": has_strong_gex,
                            "greeks_filter_applied": True,
                            "iv_percentile_filter_applied": iv_percentile is not None,
                            "gex_filter_applied": gex_data is not None,
                        },
                        instrument_type="option",
                        option_type="put",
                        moneyness="atm",  # Will be calculated from strike
                        time_to_expiry_days=best_option["dte"],
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
        
        # Helper to safely get enum value
        def get_enum_val(e):
            return e.value if hasattr(e, 'value') and not isinstance(e, str) else str(e)
        
        trend_val = get_enum_val(signal.trend_direction)
        regime_val = get_enum_val(signal.regime_type)
        vol_val = get_enum_val(signal.volatility_level)
        
        # Check trend agent signal
        if self.trend_agent_signal:
            if self.trend_agent_signal.direction == TradeDirection.SHORT:
                if trend_val == "down":
                    alignment_count += 1
                    alignment_details.append("trend_agent: SHORT aligned with DOWN trend")
                else:
                    alignment_details.append(f"trend_agent: SHORT but trend is {trend_val}")
            else:
                direction_str = get_enum_val(self.trend_agent_signal.direction)
                alignment_details.append(f"trend_agent: {direction_str} (not SHORT)")
        else:
            alignment_details.append("trend_agent: no signal")
        
        # Check mean reversion agent signal
        if self.mean_reversion_agent_signal:
            if regime_val == "mean_reversion":
                alignment_count += 1
                alignment_details.append("mean_reversion_agent: aligned with MR regime")
            else:
                alignment_details.append(f"mean_reversion_agent: regime is {regime_val} (not MR)")
        else:
            alignment_details.append("mean_reversion_agent: no signal")
        
        # Check volatility agent signal
        if self.volatility_agent_signal:
            if vol_val in ["medium", "high"]:
                alignment_count += 1
                alignment_details.append(f"volatility_agent: aligned with {vol_val} volatility")
            else:
                alignment_details.append(f"volatility_agent: volatility is {vol_val} (not MEDIUM/HIGH)")
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

