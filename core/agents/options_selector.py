"""Options contract selection engine - picks optimal contracts based on multiple criteria."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from core.config.asset_profiles import OptionRiskProfile

logger = logging.getLogger(__name__)


class OptionsSelector:
    """
    STEP 6: Contract selection engine.
    
    Picks the best option contract based on:
    - Delta target
    - Expiration target
    - Skew alignment
    - Volatility rank
    - Reward/risk scoring
    """
    
    def __init__(self, risk_profile: OptionRiskProfile):
        self.risk_profile = risk_profile
    
    def select_best_contract(
        self,
        contracts: List[Dict],
        quotes: Dict[str, Dict],
        greeks: Dict[str, Dict],
        target_delta: float,
        target_expiration: Optional[str] = None,
        current_price: float = 0.0,
    ) -> Optional[Dict]:
        """
        Select the best contract from a list of candidates.
        
        Args:
            contracts: List of option contracts
            quotes: Dict mapping option_symbol -> quote data
            greeks: Dict mapping option_symbol -> Greeks data
            target_delta: Target delta (e.g., -0.30 for PUTs)
            target_expiration: Preferred expiration date (YYYY-MM-DD) or None
            current_price: Current underlying price
        
        Returns:
            Best contract dict or None
        """
        if not contracts:
            return None
        
        scored_contracts = []
        
        for contract in contracts:
            option_symbol = contract.get("symbol", "")
            if not option_symbol:
                continue
            
            quote = quotes.get(option_symbol)
            greek = greeks.get(option_symbol)
            
            if not quote or not greek:
                continue
            
            # Score this contract
            score, reasons = self._score_contract(
                contract=contract,
                quote=quote,
                greek=greek,
                target_delta=target_delta,
                target_expiration=target_expiration,
                current_price=current_price,
            )
            
            if score > 0:
                scored_contracts.append({
                    "contract": contract,
                    "quote": quote,
                    "greek": greek,
                    "score": score,
                    "reasons": reasons,
                })
        
        if not scored_contracts:
            return None
        
        # Sort by score (highest first)
        scored_contracts.sort(key=lambda x: x["score"], reverse=True)
        
        best = scored_contracts[0]
        logger.info(
            f"Selected contract: {best['contract'].get('symbol')} "
            f"(score: {best['score']:.2f}, reasons: {', '.join(best['reasons'])})"
        )
        
        return {
            **best["contract"],
            "quote": best["quote"],
            "greeks": best["greek"],
            "selection_score": best["score"],
            "selection_reasons": best["reasons"],
        }
    
    def _score_contract(
        self,
        contract: Dict,
        quote: Dict,
        greek: Dict,
        target_delta: float,
        target_expiration: Optional[str],
        current_price: float,
    ) -> Tuple[float, List[str]]:
        """
        Score a contract based on multiple criteria.
        
        Returns:
            (score, list of reasons)
        """
        score = 0.0
        reasons = []
        
        # 1. Delta alignment (closer to target = better)
        delta = greek.get("delta", 0.0)
        delta_diff = abs(delta - target_delta)
        delta_score = max(0, 1.0 - (delta_diff / 0.20))  # Penalize if > 0.20 away
        score += delta_score * 30.0  # 30% weight
        if delta_score > 0.8:
            reasons.append("delta_aligned")
        
        # 2. Expiration alignment (closer to target = better)
        expiration = contract.get("expiration_date", "")
        if target_expiration:
            try:
                target_date = datetime.strptime(target_expiration, "%Y-%m-%d")
                contract_date = datetime.strptime(expiration, "%Y-%m-%d")
                days_diff = abs((contract_date - target_date).days)
                exp_score = max(0, 1.0 - (days_diff / 30.0))  # Penalize if > 30 days away
                score += exp_score * 20.0  # 20% weight
                if exp_score > 0.8:
                    reasons.append("expiration_aligned")
            except:
                pass
        else:
            # No target expiration - prefer mid-range DTE
            try:
                contract_date = datetime.strptime(expiration, "%Y-%m-%d")
                dte = (contract_date - datetime.now()).days
                # Prefer 14-30 DTE (sweet spot)
                if 14 <= dte <= 30:
                    score += 20.0
                    reasons.append("optimal_dte")
                elif 7 <= dte < 14 or 30 < dte <= 45:
                    score += 10.0
                    reasons.append("good_dte")
            except:
                pass
        
        # 3. Liquidity score (higher OI and volume = better)
        open_interest = int(quote.get("open_interest", 0))
        volume = int(quote.get("volume", 0))
        
        oi_score = min(1.0, open_interest / 1000.0)  # Normalize to 1000 OI
        volume_score = min(1.0, volume / 100.0)  # Normalize to 100 volume
        
        score += (oi_score + volume_score) / 2 * 15.0  # 15% weight
        if oi_score > 0.5 and volume_score > 0.5:
            reasons.append("high_liquidity")
        
        # 4. Spread score (tighter spread = better)
        bid = float(quote.get("bid", 0))
        ask = float(quote.get("ask", 0))
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            spread_pct = ((ask - bid) / mid * 100) if mid > 0 else 100.0
            spread_score = max(0, 1.0 - (spread_pct / self.risk_profile.max_spread_pct))
            score += spread_score * 15.0  # 15% weight
            if spread_score > 0.8:
                reasons.append("tight_spread")
        
        # 5. Reward/risk score
        # Estimate profit potential vs risk
        if bid > 0 and ask > 0:
            mid = (bid + ask) / 2
            strike = float(contract.get("strike_price", 0))
            
            # For PUTs: profit if price goes down
            if current_price > 0 and strike > 0:
                # Estimate profit if underlying moves down 5%
                price_move_pct = 0.05
                delta = greek.get("delta", 0.0)
                estimated_profit = abs(delta) * price_move_pct * current_price
                estimated_profit_pct = (estimated_profit / mid * 100) if mid > 0 else 0
                
                # Risk is the premium paid
                risk_pct = 100.0  # Can lose 100% of premium
                
                # Reward/risk ratio
                if risk_pct > 0:
                    rr_ratio = estimated_profit_pct / risk_pct
                    rr_score = min(1.0, rr_ratio / 2.0)  # Prefer RR > 2.0
                    score += rr_score * 20.0  # 20% weight
                    if rr_ratio > 1.5:
                        reasons.append(f"good_rr_{rr_ratio:.1f}")
        
        return score, reasons

