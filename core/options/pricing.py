"""Synthetic options pricing model (Black-Scholes-Lite)."""

from __future__ import annotations

import math
from typing import Dict

import logging

logger = logging.getLogger(__name__)


class SyntheticOptionsPricer:
    """Simple Black-Scholes-like model for synthetic options pricing."""

    @staticmethod
    def calculate_option_price(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,  # In years
        iv: float,  # Implied volatility (0.15 = 15%)
        option_type: str,  # "call" | "put"
        risk_free_rate: float = 0.05,
    ) -> float:
        """
        Calculate option price using simplified Black-Scholes approximation.
        
        For simplicity, we use a delta-based approximation:
        - For ATM options: price ≈ underlying * sqrt(time) * iv * 0.4
        - For ITM/OTM: adjust by moneyness
        
        Args:
            underlying_price: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            iv: Implied volatility (0.15 = 15%)
            option_type: "call" or "put"
            risk_free_rate: Risk-free rate (default 5%)
        
        Returns:
            Option price (premium)
        """
        if time_to_expiry <= 0:
            # At expiration: intrinsic value only
            if option_type == "call":
                return max(0, underlying_price - strike)
            else:  # put
                return max(0, strike - underlying_price)

        # Moneyness
        moneyness = underlying_price / strike if strike > 0 else 1.0
        
        # Simplified pricing formula
        time_factor = math.sqrt(time_to_expiry)
        iv_factor = iv
        
        # Base extrinsic value (ATM approximation)
        base_extrinsic = underlying_price * time_factor * iv_factor * 0.4
        
        if option_type == "call":
            intrinsic = max(0, underlying_price - strike)
            # Adjust extrinsic based on moneyness
            if moneyness > 1.0:  # ITM
                extrinsic = base_extrinsic * (1.0 + (moneyness - 1.0) * 0.5)
            elif moneyness < 1.0:  # OTM
                extrinsic = base_extrinsic * moneyness
            else:  # ATM
                extrinsic = base_extrinsic
            return intrinsic + extrinsic
        else:  # put
            intrinsic = max(0, strike - underlying_price)
            # Adjust extrinsic based on moneyness
            if moneyness < 1.0:  # ITM
                extrinsic = base_extrinsic * (1.0 + (1.0 - moneyness) * 0.5)
            elif moneyness > 1.0:  # OTM
                extrinsic = base_extrinsic / moneyness
            else:  # ATM
                extrinsic = base_extrinsic
            return intrinsic + extrinsic

    @staticmethod
    def calculate_greeks(
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        iv: float,
        option_type: str,
        current_price: float,
    ) -> Dict[str, float]:
        """
        Calculate simplified Greeks.
        
        Args:
            underlying_price: Current underlying price
            strike: Strike price
            time_to_expiry: Time to expiration in years
            iv: Implied volatility
            option_type: "call" or "put"
            current_price: Current option price
        
        Returns:
            Dictionary with delta, gamma, theta, vega, iv
        """
        moneyness = underlying_price / strike if strike > 0 else 1.0
        
        # Delta: For calls, positive; for puts, negative
        # Simplified: ATM = 0.5, ITM approaches 1.0, OTM approaches 0.0
        if option_type == "call":
            if abs(moneyness - 1.0) < 0.02:  # ATM
                delta = 0.5
            elif moneyness > 1.0:  # ITM
                delta = min(0.95, 0.5 + (moneyness - 1.0) * 2.0)
            else:  # OTM
                delta = max(0.05, 0.5 * moneyness)
        else:  # put
            if abs(moneyness - 1.0) < 0.02:  # ATM
                delta = -0.5
            elif moneyness < 1.0:  # ITM
                delta = max(-0.95, -0.5 - (1.0 - moneyness) * 2.0)
            else:  # OTM
                delta = min(-0.05, -0.5 / moneyness)
        
        # Theta: Time decay (negative for long options)
        # Simplified: ~1-5% per day depending on time to expiry
        if time_to_expiry > 0:
            daily_decay_pct = 0.01 + (0.04 * (1.0 / (1.0 + time_to_expiry * 365)))  # More decay near expiration
            theta = -current_price * daily_decay_pct
        else:
            theta = 0.0
        
        # Gamma: Rate of change of delta (simplified)
        gamma = 0.01 if abs(moneyness - 1.0) < 0.05 else 0.005
        
        # Vega: Sensitivity to volatility (simplified)
        vega = current_price * 0.1  # 10% of price per 1% IV change
        
        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta,
            "vega": vega,
            "iv": iv,
        }

    @staticmethod
    def calculate_strike_from_moneyness(
        underlying_price: float,
        moneyness: str,
        option_type: str,
    ) -> float:
        """
        Calculate strike price from moneyness description.
        
        Args:
            underlying_price: Current underlying price
            moneyness: "atm" | "otm" | "itm"
            option_type: "call" | "put"
        
        Returns:
            Strike price
        """
        if moneyness == "atm":
            return underlying_price
        elif moneyness == "otm":
            # OTM: strike above current price for calls, below for puts
            if option_type == "call":
                return underlying_price * 1.02  # 2% OTM
            else:  # put
                return underlying_price * 0.98  # 2% OTM
        elif moneyness == "itm":
            # ITM: strike below current price for calls, above for puts
            if option_type == "call":
                return underlying_price * 0.98  # 2% ITM
            else:  # put
                return underlying_price * 1.02  # 2% ITM
        else:
            # Default to ATM
            return underlying_price

    @staticmethod
    def calculate_expiration_from_dte(dte: int) -> float:
        """
        Calculate expiration datetime from days to expiry.
        
        Args:
            dte: Days to expiration (0 = today, 1 = tomorrow, etc.)
        
        Returns:
            Time to expiration in years
        """
        return dte / 365.0


