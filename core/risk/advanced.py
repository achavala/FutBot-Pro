from __future__ import annotations

from dataclasses import dataclass
from typing import Deque, Dict, Optional

from collections import deque

import numpy as np

from core.regime.types import RegimeType, VolatilityLevel


@dataclass
class AdvancedRiskConfig:
    """Advanced risk management configuration."""

    # Volatility scaling
    enable_volatility_scaling: bool = True
    vol_scaling_factor: float = 0.5  # Reduce size by 50% per vol level increase
    base_volatility_level: VolatilityLevel = VolatilityLevel.MEDIUM

    # Drawdown limits
    max_drawdown_pct: float = 0.15  # 15% max drawdown
    soft_drawdown_pct: float = 0.10  # 10% soft stop (throttle)
    drawdown_window: int = 100  # Lookback for drawdown calculation

    # Circuit breakers
    enable_circuit_breakers: bool = True
    max_losses_in_window: int = 5
    loss_window_size: int = 20
    circuit_breaker_cooldown: int = 50  # Bars to wait after circuit breaker

    # Regime-aware position caps
    trend_max_position_pct: float = 0.15  # 15% in trend regimes
    mean_reversion_max_position_pct: float = 0.10  # 10% in MR regimes
    compression_max_position_pct: float = 0.05  # 5% in compression
    expansion_max_position_pct: float = 0.12  # 12% in expansion

    # Portfolio VaR
    enable_var: bool = True
    var_confidence: float = 0.95  # 95% VaR
    var_window: int = 100
    max_var_exposure: float = 0.02  # Max 2% VaR exposure per trade

    # Symbol-level risk budgets
    max_symbol_exposure_pct: float = 0.20  # Max 20% per symbol
    max_correlation_exposure: float = 0.30  # Max 30% across correlated symbols

    # Multi-layer stops
    hard_stop_loss_pct: float = 0.25  # 25% hard stop
    soft_stop_loss_pct: float = 0.15  # 15% soft stop (reduce size)


class AdvancedRiskManager:
    """Advanced risk management with multiple protection layers."""

    def __init__(self, initial_capital: float, config: Optional[AdvancedRiskConfig] = None):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.config = config or AdvancedRiskConfig()

        # Drawdown tracking
        self.equity_history: Deque[float] = deque(maxlen=self.config.drawdown_window)
        self.equity_history.append(initial_capital)
        self.peak_equity = initial_capital

        # Circuit breaker state
        self.recent_losses: Deque[bool] = deque(maxlen=self.config.loss_window_size)
        self.circuit_breaker_active = False
        self.circuit_breaker_until_bar = 0

        # VaR calculation
        self.returns_history: Deque[float] = deque(maxlen=self.config.var_window)

        # Daily tracking
        self.daily_pnl: float = 0.0
        self.daily_loss_limit_pct: float = 0.03  # 3% daily loss limit

    def update_equity(self, current_equity: float) -> None:
        """Update equity history for drawdown calculation."""
        self.equity_history.append(current_equity)
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

        # Calculate return for VaR
        if len(self.equity_history) > 1:
            prev_equity = self.equity_history[-2]
            if prev_equity > 0:
                ret = (current_equity - prev_equity) / prev_equity
                self.returns_history.append(ret)

    def update_pnl(self, pnl: float) -> None:
        """Update PnL and track losses for circuit breakers."""
        self.current_capital += pnl
        self.daily_pnl += pnl

        # Track losses for circuit breaker
        is_loss = pnl < 0
        self.recent_losses.append(is_loss)

    def reset_daily(self) -> None:
        """Reset daily tracking."""
        self.daily_pnl = 0.0

    def get_current_drawdown(self) -> float:
        """Calculate current drawdown percentage."""
        if not self.equity_history:
            return 0.0
        current = self.equity_history[-1]
        if self.peak_equity == 0:
            return 0.0
        return ((self.peak_equity - current) / self.peak_equity) * 100.0

    def check_drawdown_limits(self) -> tuple[bool, str]:
        """Check if drawdown limits are exceeded. Returns (should_stop, reason)."""
        current_dd = self.get_current_drawdown()

        if current_dd >= self.config.max_drawdown_pct:
            return True, f"Hard drawdown limit exceeded: {current_dd:.2f}% >= {self.config.max_drawdown_pct}%"

        if current_dd >= self.config.soft_drawdown_pct:
            return False, f"Soft drawdown limit: {current_dd:.2f}% >= {self.config.soft_drawdown_pct}% (throttling)"

        return False, ""

    def check_circuit_breaker(self, current_bar: int) -> tuple[bool, str]:
        """Check if circuit breaker should activate. Returns (is_active, reason)."""
        if not self.config.enable_circuit_breakers:
            return False, ""

        # Check if still in cooldown
        if self.circuit_breaker_active and current_bar < self.circuit_breaker_until_bar:
            return True, f"Circuit breaker active until bar {self.circuit_breaker_until_bar}"

        # Reset if cooldown expired
        if self.circuit_breaker_active and current_bar >= self.circuit_breaker_until_bar:
            self.circuit_breaker_active = False

        # Check loss streak
        recent_loss_count = sum(self.recent_losses)
        if recent_loss_count >= self.config.max_losses_in_window:
            self.circuit_breaker_active = True
            self.circuit_breaker_until_bar = current_bar + self.config.circuit_breaker_cooldown
            return True, f"Circuit breaker: {recent_loss_count} losses in last {len(self.recent_losses)} trades"

        return False, ""

    def calculate_var(self) -> float:
        """Calculate Value at Risk (VaR) at configured confidence level."""
        if not self.config.enable_var or len(self.returns_history) < 20:
            return 0.0

        returns_array = np.array(self.returns_history)
        var_percentile = (1 - self.config.var_confidence) * 100
        var = np.percentile(returns_array, var_percentile)

        # Convert to dollar amount
        var_dollar = abs(var * self.current_capital)
        return var_dollar

    def volatility_scaled_size(
        self, base_size: float, current_volatility: VolatilityLevel, base_volatility: VolatilityLevel
    ) -> float:
        """Scale position size based on volatility."""
        if not self.config.enable_volatility_scaling:
            return base_size

        vol_levels = {VolatilityLevel.LOW: 0, VolatilityLevel.MEDIUM: 1, VolatilityLevel.HIGH: 2}
        current_vol = vol_levels.get(current_volatility, 1)
        base_vol = vol_levels.get(base_volatility, 1)
        vol_diff = current_vol - base_vol

        # Reduce size by scaling factor for each volatility level above base
        if vol_diff > 0:
            scale = (1 - self.config.vol_scaling_factor) ** vol_diff
        else:
            scale = 1.0

        return base_size * scale

    def regime_aware_position_cap(self, regime_type: RegimeType) -> float:
        """Get maximum position size percentage based on regime."""
        caps = {
            RegimeType.TREND: self.config.trend_max_position_pct,
            RegimeType.MEAN_REVERSION: self.config.mean_reversion_max_position_pct,
            RegimeType.COMPRESSION: self.config.compression_max_position_pct,
            RegimeType.EXPANSION: self.config.expansion_max_position_pct,
            RegimeType.NEUTRAL: 0.10,  # Default 10%
        }
        return caps.get(regime_type, 0.10)

    def check_daily_loss_limit(self) -> tuple[bool, str]:
        """Check if daily loss limit is exceeded."""
        loss_pct = abs(self.daily_pnl) / self.initial_capital if self.daily_pnl < 0 else 0.0
        if loss_pct >= self.daily_loss_limit_pct:
            return True, f"Daily loss limit exceeded: {loss_pct*100:.2f}% >= {self.daily_loss_limit_pct*100}%"
        return False, ""

    def compute_advanced_position_size(
        self,
        base_size: float,
        price: float,
        confidence: float,
        regime_type: RegimeType,
        volatility_level: VolatilityLevel,
        current_bar: int,
    ) -> tuple[float, str]:
        """
        Compute position size with all advanced risk controls.
        Returns (adjusted_size, reason).
        """
        # Start with base size
        size = base_size

        # Check hard stops first
        hard_stop, reason = self.check_drawdown_limits()
        if hard_stop:
            return 0.0, reason

        # Check circuit breaker
        circuit_active, circuit_reason = self.check_circuit_breaker(current_bar)
        if circuit_active:
            return 0.0, circuit_reason

        # Check daily loss limit
        daily_limit, daily_reason = self.check_daily_loss_limit()
        if daily_limit:
            return 0.0, daily_reason

        # Apply soft drawdown throttle
        soft_stop, soft_reason = self.check_drawdown_limits()
        if soft_stop and not hard_stop:
            size *= 0.5  # Reduce by 50% under soft stop

        # Apply regime-aware cap
        regime_cap_pct = self.regime_aware_position_cap(regime_type)
        max_size_by_regime = (self.current_capital * regime_cap_pct) / price if price > 0 else 0.0
        size = min(size, max_size_by_regime)

        # Apply volatility scaling
        size = self.volatility_scaled_size(size, volatility_level, self.config.base_volatility_level)

        # Apply confidence scaling
        size = size * confidence

        # Check VaR limit
        if self.config.enable_var:
            var = self.calculate_var()
            position_var = abs(size * price * 0.01)  # Rough estimate: 1% move
            if position_var > self.config.max_var_exposure * self.current_capital:
                size = (self.config.max_var_exposure * self.current_capital) / (price * 0.01) if price > 0 else 0.0

        # Apply symbol-level exposure cap
        max_symbol_exposure = (self.current_capital * self.config.max_symbol_exposure_pct) / price if price > 0 else 0.0
        size = min(size, max_symbol_exposure)

        return size, ""

    def can_trade_advanced(
        self,
        confidence: float,
        regime_type: RegimeType,
        volatility_level: VolatilityLevel,
        current_bar: int,
        min_confidence: float = 0.4,
    ) -> tuple[bool, str]:
        """Advanced can_trade check with all risk layers."""
        if confidence < min_confidence:
            return False, f"Confidence too low: {confidence:.2f} < {min_confidence:.2f}"

        # Check hard stops
        hard_stop, reason = self.check_drawdown_limits()
        if hard_stop:
            return False, reason

        # Check circuit breaker
        circuit_active, circuit_reason = self.check_circuit_breaker(current_bar)
        if circuit_active:
            return False, circuit_reason

        # Check daily loss limit
        daily_limit, daily_reason = self.check_daily_loss_limit()
        if daily_limit:
            return False, daily_reason

        return True, ""

    def get_risk_metrics(self) -> Dict[str, any]:
        """Get comprehensive risk metrics."""
        return {
            "current_drawdown_pct": self.get_current_drawdown(),
            "peak_equity": self.peak_equity,
            "current_equity": self.equity_history[-1] if self.equity_history else self.initial_capital,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": (self.daily_pnl / self.initial_capital) * 100.0,
            "circuit_breaker_active": self.circuit_breaker_active,
            "recent_loss_count": sum(self.recent_losses),
            "var_95": self.calculate_var(),
            "var_pct": (self.calculate_var() / self.current_capital) * 100.0 if self.current_capital > 0 else 0.0,
        }

