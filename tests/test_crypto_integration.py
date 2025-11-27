"""Tests for crypto integration."""

import pytest
from core.config.asset_profiles import AssetProfileManager, AssetType
from core.live.orchestrator import TradingOrchestrator


def test_orchestrator_symbol_grouping():
    """Test orchestrator groups symbols by asset type."""
    manager = AssetProfileManager()
    
    orchestrator = TradingOrchestrator(
        symbols=["QQQ", "BTC/USD", "SPY", "ETH/USD"],
        asset_profile_manager=manager,
        broker_type="paper",
    )
    
    assert len(orchestrator.equity_symbols) == 2
    assert len(orchestrator.crypto_symbols) == 2
    assert "QQQ" in orchestrator.equity_symbols
    assert "SPY" in orchestrator.equity_symbols
    assert "BTC/USD" in orchestrator.crypto_symbols
    assert "ETH/USD" in orchestrator.crypto_symbols


def test_orchestrator_profile_access():
    """Test orchestrator provides access to asset profiles."""
    manager = AssetProfileManager()
    
    orchestrator = TradingOrchestrator(
        symbols=["QQQ", "BTC/USD"],
        asset_profile_manager=manager,
        broker_type="paper",
    )
    
    qqq_profile = orchestrator.get_profile("QQQ")
    assert qqq_profile.asset_type == AssetType.EQUITY
    
    btc_profile = orchestrator.get_profile("BTC/USD")
    assert btc_profile.asset_type == AssetType.CRYPTO


def test_mixed_symbol_profiles():
    """Test that mixed equity/crypto symbols get correct profiles."""
    manager = AssetProfileManager()
    
    # Load custom config
    config = {
        "QQQ": {
            "asset_type": "equity",
            "take_profit_pct": 0.30,
            "stop_loss_pct": 0.20,
        },
        "BTC/USD": {
            "asset_type": "crypto",
            "take_profit_pct": 0.50,
            "stop_loss_pct": 0.25,
        },
    }
    manager.load_from_config(config)
    
    orchestrator = TradingOrchestrator(
        symbols=["QQQ", "BTC/USD"],
        asset_profile_manager=manager,
        broker_type="paper",
    )
    
    qqq_profile = orchestrator.get_profile("QQQ")
    assert qqq_profile.take_profit_pct == 0.30
    assert qqq_profile.stop_loss_pct == 0.20
    
    btc_profile = orchestrator.get_profile("BTC/USD")
    assert btc_profile.take_profit_pct == 0.50
    assert btc_profile.stop_loss_pct == 0.25

