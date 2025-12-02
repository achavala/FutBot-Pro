#!/usr/bin/env python3
"""Helper to create Gamma Scalper only agent configuration."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.agents.gamma_scalper_agent import GammaScalperAgent
from core.agents.theta_harvester_agent import ThetaHarvesterAgent
from core.config.asset_profiles import OptionRiskProfile


def create_gamma_only_agents(symbol: str, options_data_feed=None, options_broker_client=None):
    """
    Create agents list with Gamma Scalper only (Theta Harvester disabled).
    
    Returns:
        List of agents (base agents + Gamma Scalper only)
    """
    from core.agents.trend_agent import TrendAgent
    from core.agents.mean_reversion_agent import MeanReversionAgent
    from core.agents.volatility_agent import VolatilityAgent
    from core.agents.fvg_agent import FVGAgent
    
    # Base agents (needed for regime detection)
    base_agents = [
        TrendAgent(symbol=symbol),
        MeanReversionAgent(symbol=symbol),
        VolatilityAgent(symbol=symbol),
        FVGAgent(symbol=symbol),
    ]
    
    # Options risk profile
    option_risk_profile = OptionRiskProfile(
        testing_mode=True,
        min_dte_for_entry=0,
        max_dte_for_entry=45,
        min_iv_percentile=0.0,
        max_iv_percentile=100.0,
        max_spread_pct=20.0,
        min_open_interest=10,
        min_volume=1,
    )
    
    # Gamma Scalper - ENABLED
    gamma_scalper = GammaScalperAgent(
        symbol=symbol,
        options_data_feed=options_data_feed,
        option_risk_profile=option_risk_profile,
        config={"min_confidence": 0.30},
    )
    
    # Theta Harvester - DISABLED (not added to list)
    # theta_harvester = ThetaHarvesterAgent(...)  # Not created
    
    agents = base_agents + [gamma_scalper]
    
    return agents


def create_theta_only_agents(symbol: str, options_data_feed=None, options_broker_client=None):
    """Create agents list with Theta Harvester only (Gamma Scalper disabled)."""
    from core.agents.trend_agent import TrendAgent
    from core.agents.mean_reversion_agent import MeanReversionAgent
    from core.agents.volatility_agent import VolatilityAgent
    from core.agents.fvg_agent import FVGAgent
    
    base_agents = [
        TrendAgent(symbol=symbol),
        MeanReversionAgent(symbol=symbol),
        VolatilityAgent(symbol=symbol),
        FVGAgent(symbol=symbol),
    ]
    
    option_risk_profile = OptionRiskProfile(
        testing_mode=True,
        min_dte_for_entry=0,
        max_dte_for_entry=45,
        min_iv_percentile=0.0,
        max_iv_percentile=100.0,
        max_spread_pct=20.0,
        min_open_interest=10,
        min_volume=1,
    )
    
    # Theta Harvester - ENABLED
    theta_harvester = ThetaHarvesterAgent(
        symbol=symbol,
        options_data_feed=options_data_feed,
        option_risk_profile=option_risk_profile,
        options_broker_client=options_broker_client,
        config={"min_confidence": 0.30},
    )
    
    # Gamma Scalper - DISABLED (not added to list)
    
    agents = base_agents + [theta_harvester]
    
    return agents


def create_all_options_agents(symbol: str, options_data_feed=None, options_broker_client=None):
    """Create agents list with both Gamma Scalper and Theta Harvester."""
    from core.agents.trend_agent import TrendAgent
    from core.agents.mean_reversion_agent import MeanReversionAgent
    from core.agents.volatility_agent import VolatilityAgent
    from core.agents.fvg_agent import FVGAgent
    
    base_agents = [
        MeanReversionAgent(symbol=symbol),
        VolatilityAgent(symbol=symbol),
        FVGAgent(symbol=symbol),
    ]
    
    option_risk_profile = OptionRiskProfile(
        testing_mode=True,
        min_dte_for_entry=0,
        max_dte_for_entry=45,
        min_iv_percentile=0.0,
        max_iv_percentile=100.0,
        max_spread_pct=20.0,
        min_open_interest=10,
        min_volume=1,
    )
    
    # Both agents enabled
    gamma_scalper = GammaScalperAgent(
        symbol=symbol,
        options_data_feed=options_data_feed,
        option_risk_profile=option_risk_profile,
        config={"min_confidence": 0.30},
    )
    
    theta_harvester = ThetaHarvesterAgent(
        symbol=symbol,
        options_data_feed=options_data_feed,
        option_risk_profile=option_risk_profile,
        options_broker_client=options_broker_client,
        config={"min_confidence": 0.30},
    )
    
    agents = base_agents + [gamma_scalper, theta_harvester]
    
    return agents


if __name__ == "__main__":
    print("Gamma-only agent configuration helper")
    print("Usage:")
    print("  from scripts.create_gamma_only_agents import create_gamma_only_agents")
    print("  agents = create_gamma_only_agents('SPY', options_data_feed=feed)")

