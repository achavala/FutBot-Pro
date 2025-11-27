"""Tests for asset profile system."""

import pytest
from core.config.asset_profiles import AssetProfile, AssetProfileManager, AssetType, AssetProfileConfig


def test_asset_profile_creation():
    """Test creating asset profiles."""
    profile = AssetProfile(
        symbol="QQQ",
        asset_type=AssetType.EQUITY,
        risk_per_trade_pct=1.0,
        take_profit_pct=0.30,
        stop_loss_pct=0.20,
    )
    assert profile.symbol == "QQQ"
    assert profile.asset_type == AssetType.EQUITY
    assert profile.take_profit_pct == 0.30
    assert profile.stop_loss_pct == 0.20


def test_crypto_profile_creation():
    """Test creating crypto asset profiles."""
    profile = AssetProfile(
        symbol="BTC/USD",
        asset_type=AssetType.CRYPTO,
        risk_per_trade_pct=0.5,
        take_profit_pct=0.50,
        stop_loss_pct=0.25,
    )
    assert profile.symbol == "BTC/USD"
    assert profile.asset_type == AssetType.CRYPTO
    assert profile.take_profit_pct == 0.50
    assert profile.stop_loss_pct == 0.25


def test_asset_profile_manager_defaults():
    """Test asset profile manager returns defaults."""
    manager = AssetProfileManager()
    
    # Test equity default
    qqq_profile = manager.get_profile("QQQ")
    assert qqq_profile.asset_type == AssetType.EQUITY
    assert qqq_profile.take_profit_pct == 0.30
    assert qqq_profile.stop_loss_pct == 0.20
    
    # Test crypto default
    btc_profile = manager.get_profile("BTC/USD")
    assert btc_profile.asset_type == AssetType.CRYPTO
    assert btc_profile.take_profit_pct == 0.50
    assert btc_profile.stop_loss_pct == 0.25


def test_asset_type_detection():
    """Test automatic asset type detection."""
    manager = AssetProfileManager()
    
    # Equity detection
    assert manager._detect_asset_type("QQQ") == AssetType.EQUITY
    assert manager._detect_asset_type("SPY") == AssetType.EQUITY
    assert manager._detect_asset_type("AAPL") == AssetType.EQUITY
    
    # Crypto detection
    assert manager._detect_asset_type("BTC/USD") == AssetType.CRYPTO
    assert manager._detect_asset_type("ETH/USD") == AssetType.CRYPTO
    assert manager._detect_asset_type("BTCUSD") == AssetType.CRYPTO


def test_load_from_config():
    """Test loading profiles from config dictionary."""
    manager = AssetProfileManager()
    
    config = {
        "QQQ": {
            "asset_type": "equity",
            "risk_per_trade_pct": 1.0,
            "take_profit_pct": 0.30,
            "stop_loss_pct": 0.20,
        },
        "BTC/USD": {
            "asset_type": "crypto",
            "risk_per_trade_pct": 0.5,
            "take_profit_pct": 0.50,
            "stop_loss_pct": 0.25,
        },
    }
    
    manager.load_from_config(config)
    
    qqq_profile = manager.get_profile("QQQ")
    assert qqq_profile.take_profit_pct == 0.30
    
    btc_profile = manager.get_profile("BTC/USD")
    assert btc_profile.take_profit_pct == 0.50


def test_pydantic_model():
    """Test Pydantic model for asset profile config."""
    config = AssetProfileConfig(
        symbol="QQQ",
        asset_type=AssetType.EQUITY,
        take_profit_pct=0.30,
        stop_loss_pct=0.20,
    )
    
    profile = config.to_asset_profile()
    assert profile.symbol == "QQQ"
    assert profile.take_profit_pct == 0.30

