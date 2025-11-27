from __future__ import annotations

from typing import Dict, Optional

from ui.bot_manager import BotManager


def generate_prometheus_metrics(bot_manager: Optional[BotManager]) -> str:
    """Generate Prometheus-formatted metrics."""
    if not bot_manager:
        return "# Bot manager not initialized\n"

    metrics = []

    # Portfolio metrics
    portfolio_stats = bot_manager.get_portfolio_stats()
    metrics.append(f"futbot_cumulative_pnl {portfolio_stats.get('total_return_pct', 0.0)}")
    metrics.append(f"futbot_current_capital {portfolio_stats.get('current_capital', 0.0)}")
    metrics.append(f"futbot_total_value {portfolio_stats.get('total_value', 0.0)}")
    metrics.append(f"futbot_max_drawdown {portfolio_stats.get('max_drawdown', 0.0)}")
    metrics.append(f"futbot_win_rate {portfolio_stats.get('win_rate', 0.0)}")
    metrics.append(f"futbot_total_trades {portfolio_stats.get('total_trades', 0)}")
    metrics.append(f"futbot_open_positions {portfolio_stats.get('open_positions', 0)}")

    # Risk metrics
    risk_status = bot_manager.get_risk_status()
    metrics.append(f'futbot_kill_switch_engaged {1 if risk_status.get("kill_switch_engaged", False) else 0}')
    metrics.append(f"futbot_daily_pnl {risk_status.get('daily_pnl', 0.0)}")
    metrics.append(f"futbot_loss_streak {risk_status.get('loss_streak', 0)}")
    metrics.append(f'futbot_can_trade {1 if risk_status.get("can_trade", False) else 0}')

    # Advanced risk metrics
    if "advanced_risk" in risk_status:
        adv_risk = risk_status["advanced_risk"]
        metrics.append(f"futbot_current_drawdown_pct {adv_risk.get('current_drawdown_pct', 0.0)}")
        metrics.append(f"futbot_daily_pnl_pct {adv_risk.get('daily_pnl_pct', 0.0)}")
        metrics.append(f'futbot_circuit_breaker_active {1 if adv_risk.get("circuit_breaker_active", False) else 0}')
        metrics.append(f"futbot_recent_loss_count {adv_risk.get('recent_loss_count', 0)}")
        metrics.append(f"futbot_var_95 {adv_risk.get('var_95', 0.0)}")

    # Agent metrics
    agent_fitness = bot_manager.get_agent_fitness()
    for agent_name, fitness in agent_fitness.items():
        metrics.append(f'futbot_agent_fitness_short{{agent="{agent_name}"}} {fitness.get("short_term", 0.0)}')
        metrics.append(f'futbot_agent_fitness_long{{agent="{agent_name}"}} {fitness.get("long_term", 0.0)}')

    # Regime metrics
    regime = bot_manager.get_current_regime()
    if regime:
        metrics.append(f'futbot_regime_confidence{{regime="{regime.get("regime_type", "unknown")}"}} {regime.get("confidence", 0.0)}')

    # Live trading status
    if bot_manager.mode == "live" and bot_manager.live_loop:
        live_status = bot_manager.get_live_status()
        metrics.append(f'futbot_live_running {1 if live_status.get("is_running", False) else 0}')
        metrics.append(f'futbot_live_paused {1 if live_status.get("is_paused", False) else 0}')
        metrics.append(f"futbot_bar_count {live_status.get('bar_count', 0)}")

    # System health
    health = bot_manager.get_health_status()
    metrics.append(f'futbot_system_healthy {1 if health.get("portfolio_healthy", False) else 0}')
    metrics.append(f'futbot_system_running {1 if health.get("is_running", False) else 0}')

    return "\n".join(metrics) + "\n"


def generate_json_metrics(bot_manager: Optional[BotManager]) -> Dict:
    """Generate JSON-formatted metrics."""
    if not bot_manager:
        return {"error": "Bot manager not initialized"}

    return {
        "portfolio": bot_manager.get_portfolio_stats(),
        "risk": bot_manager.get_risk_status(),
        "agents": bot_manager.get_agent_fitness(),
        "regime": bot_manager.get_current_regime(),
        "health": bot_manager.get_health_status(),
        "live_status": bot_manager.get_live_status() if bot_manager.mode == "live" else None,
    }

