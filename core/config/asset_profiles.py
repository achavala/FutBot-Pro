"""Asset profile configuration for symbols."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Asset type enumeration."""
    
    EQUITY = "equity"
    CRYPTO = "crypto"
    FOREX = "forex"
    FUTURES = "futures"


@dataclass
class AssetProfile:
    """Risk and trading profile for a symbol."""
    
    symbol: str
    asset_type: AssetType
    risk_per_trade_pct: float = 1.0  # % of capital to risk per trade
    take_profit_pct: float = 0.30  # Take profit at this % gain
    stop_loss_pct: float = 0.20  # Stop loss at this % loss
    trailing_stop_pct: float = 1.5  # Trailing stop % from peak
    min_hold_bars: int = 5  # Minimum bars to hold position
    max_hold_bars: int = 200  # Maximum bars to hold position
    fixed_investment_amount: Optional[float] = None  # Fixed $ amount per trade (overrides risk_per_trade_pct)
    exit_on_regime_change: bool = True  # Exit if regime becomes unfavorable
    exit_on_bias_flip: bool = True  # Exit if bias flips opposite direction
    
    def __post_init__(self):
        """Validate profile values."""
        if self.risk_per_trade_pct <= 0 or self.risk_per_trade_pct > 10:
            raise ValueError(f"risk_per_trade_pct must be between 0 and 10, got {self.risk_per_trade_pct}")
        if self.take_profit_pct <= 0:
            raise ValueError(f"take_profit_pct must be positive, got {self.take_profit_pct}")
        if self.stop_loss_pct <= 0:
            raise ValueError(f"stop_loss_pct must be positive, got {self.stop_loss_pct}")


class AssetProfileConfig(BaseModel):
    """Pydantic model for asset profile configuration."""
    
    symbol: str = Field(..., description="Trading symbol")
    asset_type: AssetType = Field(..., description="Asset type (equity, crypto, etc.)")
    risk_per_trade_pct: float = Field(1.0, ge=0.0, le=10.0, description="% of capital to risk per trade")
    take_profit_pct: float = Field(0.30, gt=0.0, description="Take profit at this % gain")
    stop_loss_pct: float = Field(0.20, gt=0.0, description="Stop loss at this % loss")
    trailing_stop_pct: float = Field(1.5, gt=0.0, description="Trailing stop % from peak")
    min_hold_bars: int = Field(5, ge=0, description="Minimum bars to hold position")
    max_hold_bars: int = Field(200, ge=1, description="Maximum bars to hold position")
    fixed_investment_amount: Optional[float] = Field(None, gt=0.0, description="Fixed $ amount per trade")
    exit_on_regime_change: bool = Field(True, description="Exit if regime becomes unfavorable")
    exit_on_bias_flip: bool = Field(True, description="Exit if bias flips opposite direction")


@dataclass
class OptionRiskProfile:
    """Options-specific risk parameters."""
    
    # Testing mode flag
    testing_mode: bool = False  # If True, use relaxed filters for testing
    
    # Spread and liquidity
    max_spread_pct: float = 10.0  # Max bid-ask spread as % of mid price
    min_open_interest: int = 100  # Minimum open interest
    min_volume: int = 10  # Minimum daily volume
    
    # Greeks and risk
    max_theta_decay_allowed: float = 0.05  # Max theta decay per day as % of premium
    delta_range: Tuple[float, float] = (-0.50, -0.10)  # For PUTs: negative delta range
    expiration_range_days: Tuple[int, int] = (7, 45)  # Min/max days to expiration
    
    # Risk limits
    max_loss_pct_per_trade: float = 50.0  # Max loss as % of premium paid
    max_intraday_volatility_allowed: float = 0.15  # Max underlying volatility (15%)
    
    # Position sizing
    max_premium_per_trade: float = 1000.0  # Max premium to pay per trade
    max_contracts_per_trade: int = 10  # Max contracts per trade
    
    # Time-based restrictions
    min_dte_for_entry: int = 0  # Minimum days to expiration to enter (0 = allow 0DTE)
    max_dte_for_entry: int = 45  # Maximum days to expiration to enter
    # PERFORMANCE: Enable 0DTE trading for aggressive strategies
    exit_before_exp_days: int = 3  # Exit position N days before expiration
    
    # IV and skew
    min_iv_percentile: float = 30.0  # Minimum IV percentile
    max_iv_percentile: float = 90.0  # Maximum IV percentile
    avoid_iv_crush_events: bool = True  # Avoid trading before earnings/events
    
    def __post_init__(self):
        """Validate parameters."""
        # If testing mode, apply VERY relaxed defaults (for debugging)
        if self.testing_mode:
            if self.max_spread_pct == 10.0:  # Only override if using default
                self.max_spread_pct = 40.0  # Very loose for testing
            if self.min_open_interest == 100:  # Only override if using default
                self.min_open_interest = 1  # Very loose
            if self.min_volume == 10:  # Only override if using default
                self.min_volume = 0  # No volume requirement
            if self.min_iv_percentile == 30.0:  # Only override if using default
                self.min_iv_percentile = 0.0  # No IV filter in testing
            if self.max_iv_percentile == 90.0:  # Only override if using default
                self.max_iv_percentile = 100.0  # No IV filter in testing
            if self.min_dte_for_entry == 7:  # Only override if using default
                self.min_dte_for_entry = 1  # Very loose
            if self.max_dte_for_entry == 45:  # Only override if using default
                self.max_dte_for_entry = 90  # Very loose
            if self.max_theta_decay_allowed == 0.05:  # Only override if using default
                self.max_theta_decay_allowed = 1.0  # Very high (basically disable)
        
        if self.max_spread_pct <= 0 or self.max_spread_pct > 50:
            raise ValueError(f"max_spread_pct must be between 0 and 50, got {self.max_spread_pct}")
        if self.min_open_interest < 0:
            raise ValueError(f"min_open_interest must be >= 0, got {self.min_open_interest}")
        if self.min_volume < 0:
            raise ValueError(f"min_volume must be >= 0, got {self.min_volume}")
        if not (-1.0 <= self.delta_range[0] < self.delta_range[1] <= 1.0):
            raise ValueError(f"delta_range must be valid range, got {self.delta_range}")


class OptionRiskProfileConfig(BaseModel):
    """Pydantic model for options risk profile configuration."""
    
    testing_mode: bool = Field(False, description="Testing mode with relaxed filters")
    max_spread_pct: float = Field(10.0, gt=0, le=50, description="Max bid-ask spread %")
    min_open_interest: int = Field(100, ge=0, description="Minimum open interest")
    min_volume: int = Field(10, ge=0, description="Minimum daily volume")
    max_theta_decay_allowed: float = Field(0.05, gt=0, le=1.0, description="Max theta decay per day %")
    delta_range_min: float = Field(-0.50, ge=-1.0, le=1.0, description="Min delta (for PUTs, negative)")
    delta_range_max: float = Field(-0.10, ge=-1.0, le=1.0, description="Max delta")
    expiration_range_days_min: int = Field(7, ge=1, description="Min days to expiration")
    expiration_range_days_max: int = Field(45, ge=1, description="Max days to expiration")
    max_loss_pct_per_trade: float = Field(50.0, gt=0, le=100, description="Max loss % of premium")
    max_intraday_volatility_allowed: float = Field(0.15, gt=0, le=1.0, description="Max underlying volatility")
    max_premium_per_trade: float = Field(1000.0, gt=0, description="Max premium per trade")
    max_contracts_per_trade: int = Field(10, ge=1, description="Max contracts per trade")
    min_dte_for_entry: int = Field(7, ge=1, description="Min DTE to enter")
    max_dte_for_entry: int = Field(45, ge=1, description="Max DTE to enter")
    exit_before_exp_days: int = Field(3, ge=0, description="Exit N days before expiration")
    min_iv_percentile: float = Field(30.0, ge=0, le=100, description="Min IV percentile")
    max_iv_percentile: float = Field(90.0, ge=0, le=100, description="Max IV percentile")
    avoid_iv_crush_events: bool = Field(True, description="Avoid trading before events")
    
    def to_option_risk_profile(self) -> OptionRiskProfile:
        """Convert to dataclass."""
        return OptionRiskProfile(
            testing_mode=self.testing_mode,
            max_spread_pct=self.max_spread_pct,
            min_open_interest=self.min_open_interest,
            min_volume=self.min_volume,
            max_theta_decay_allowed=self.max_theta_decay_allowed,
            delta_range=(self.delta_range_min, self.delta_range_max),
            expiration_range_days=(self.expiration_range_days_min, self.expiration_range_days_max),
            max_loss_pct_per_trade=self.max_loss_pct_per_trade,
            max_intraday_volatility_allowed=self.max_intraday_volatility_allowed,
            max_premium_per_trade=self.max_premium_per_trade,
            max_contracts_per_trade=self.max_contracts_per_trade,
            min_dte_for_entry=self.min_dte_for_entry,
            max_dte_for_entry=self.max_dte_for_entry,
            exit_before_exp_days=self.exit_before_exp_days,
            min_iv_percentile=self.min_iv_percentile,
            max_iv_percentile=self.max_iv_percentile,
            avoid_iv_crush_events=self.avoid_iv_crush_events,
        )
    
    def to_asset_profile(self) -> AssetProfile:
        """Convert to AssetProfile dataclass."""
        return AssetProfile(
            symbol=self.symbol,
            asset_type=self.asset_type,
            risk_per_trade_pct=self.risk_per_trade_pct,
            take_profit_pct=self.take_profit_pct,
            stop_loss_pct=self.stop_loss_pct,
            trailing_stop_pct=self.trailing_stop_pct,
            min_hold_bars=self.min_hold_bars,
            max_hold_bars=self.max_hold_bars,
            fixed_investment_amount=self.fixed_investment_amount,
            exit_on_regime_change=self.exit_on_regime_change,
            exit_on_bias_flip=self.exit_on_bias_flip,
        )


class AssetProfileManager:
    """Manages asset profiles for symbols."""
    
    def __init__(self, profiles: Optional[Dict[str, AssetProfile]] = None):
        """
        Initialize asset profile manager.
        
        Args:
            profiles: Dictionary mapping symbol -> AssetProfile
        """
        self.profiles: Dict[str, AssetProfile] = profiles or {}
        self._default_equity = AssetProfile(
            symbol="DEFAULT_EQUITY",
            asset_type=AssetType.EQUITY,
            risk_per_trade_pct=1.0,
            take_profit_pct=0.30,
            stop_loss_pct=0.20,
        )
        self._default_crypto = AssetProfile(
            symbol="DEFAULT_CRYPTO",
            asset_type=AssetType.CRYPTO,
            risk_per_trade_pct=0.5,  # Lower risk for crypto (more volatile)
            take_profit_pct=0.50,  # Higher profit target for crypto
            stop_loss_pct=0.25,  # Tighter stop loss for crypto
        )
    
    def get_profile(self, symbol: str) -> AssetProfile:
        """
        Get asset profile for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            AssetProfile for symbol, or default based on asset type detection
        """
        # Check explicit profile
        if symbol in self.profiles:
            return self.profiles[symbol]
        
        # Auto-detect asset type and return default
        asset_type = self._detect_asset_type(symbol)
        if asset_type == AssetType.CRYPTO:
            # Create a default crypto profile for this symbol
            return AssetProfile(
                symbol=symbol,
                asset_type=AssetType.CRYPTO,
                risk_per_trade_pct=self._default_crypto.risk_per_trade_pct,
                take_profit_pct=self._default_crypto.take_profit_pct,
                stop_loss_pct=self._default_crypto.stop_loss_pct,
                trailing_stop_pct=self._default_crypto.trailing_stop_pct,
                min_hold_bars=self._default_crypto.min_hold_bars,
                max_hold_bars=self._default_crypto.max_hold_bars,
                fixed_investment_amount=self._default_crypto.fixed_investment_amount,
                exit_on_regime_change=self._default_crypto.exit_on_regime_change,
                exit_on_bias_flip=self._default_crypto.exit_on_bias_flip,
            )
        else:
            # Create a default equity profile for this symbol
            return AssetProfile(
                symbol=symbol,
                asset_type=AssetType.EQUITY,
                risk_per_trade_pct=self._default_equity.risk_per_trade_pct,
                take_profit_pct=self._default_equity.take_profit_pct,
                stop_loss_pct=self._default_equity.stop_loss_pct,
                trailing_stop_pct=self._default_equity.trailing_stop_pct,
                min_hold_bars=self._default_equity.min_hold_bars,
                max_hold_bars=self._default_equity.max_hold_bars,
                fixed_investment_amount=self._default_equity.fixed_investment_amount,
                exit_on_regime_change=self._default_equity.exit_on_regime_change,
                exit_on_bias_flip=self._default_equity.exit_on_bias_flip,
            )
    
    def _detect_asset_type(self, symbol: str) -> AssetType:
        """
        Detect asset type from symbol string.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Detected AssetType
        """
        symbol_upper = symbol.upper()
        
        # Crypto indicators
        crypto_indicators = ["BTC", "ETH", "SOL", "AVAX", "MATIC", "LINK", "UNI", "AAVE", "ALGO", "DOGE", "ADA", "DOT"]
        if any(crypto in symbol_upper for crypto in crypto_indicators) or "/USD" in symbol_upper:
            return AssetType.CRYPTO
        
        # Default to equity
        return AssetType.EQUITY
    
    def add_profile(self, profile: AssetProfile) -> None:
        """Add or update an asset profile."""
        self.profiles[profile.symbol] = profile
    
    def load_from_config(self, config_dict: Dict[str, Dict]) -> None:
        """
        Load profiles from configuration dictionary.
        
        Args:
            config_dict: Dictionary with symbol -> profile config
        """
        for symbol, profile_config in config_dict.items():
            try:
                profile = AssetProfileConfig(**profile_config).to_asset_profile()
                profile.symbol = symbol  # Ensure symbol matches key
                self.add_profile(profile)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load profile for {symbol}: {e}, using defaults")

