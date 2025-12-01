from __future__ import annotations

import base64
import io
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import matplotlib
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

matplotlib.use("Agg")  # Non-interactive backend


def plot_equity_curve(equity_curve: List[float], initial_capital: float) -> str:
    """Generate equity curve plot as base64 encoded PNG."""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(equity_curve, linewidth=2, color="#2E86AB")
    ax.axhline(y=initial_capital, color="gray", linestyle="--", alpha=0.5, label="Initial Capital")
    ax.set_xlabel("Bar Index", fontsize=12)
    ax.set_ylabel("Portfolio Value ($)", fontsize=12)
    ax.set_title("Equity Curve", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend()

    # Calculate and display stats
    if equity_curve:
        final_value = equity_curve[-1]
        total_return = ((final_value - initial_capital) / initial_capital) * 100
        ax.text(
            0.02,
            0.98,
            f"Total Return: {total_return:.2f}%",
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def plot_drawdown(equity_curve: List[float], initial_capital: float) -> str:
    """Generate drawdown chart as base64 encoded PNG."""
    if not equity_curve:
        return ""

    # Calculate drawdown
    peak = initial_capital
    drawdowns = []
    for value in equity_curve:
        if value > peak:
            peak = value
        dd = ((peak - value) / peak) * 100.0 if peak > 0 else 0.0
        drawdowns.append(dd)

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(range(len(drawdowns)), drawdowns, 0, color="#E63946", alpha=0.6)
    ax.plot(drawdowns, linewidth=1, color="#E63946")
    ax.set_xlabel("Bar Index", fontsize=12)
    ax.set_ylabel("Drawdown (%)", fontsize=12)
    ax.set_title("Drawdown Chart", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)

    # Display max drawdown
    max_dd = max(drawdowns) if drawdowns else 0.0
    ax.text(
        0.02,
        0.98,
        f"Max Drawdown: {max_dd:.2f}%",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def plot_agent_fitness_evolution(agent_fitness_history: Dict[str, List[float]]) -> str:
    """Generate agent fitness evolution chart."""
    if not agent_fitness_history:
        return ""

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"]
    for idx, (agent_name, fitness_values) in enumerate(agent_fitness_history.items()):
        if fitness_values:
            ax.plot(fitness_values, label=agent_name, linewidth=2, color=colors[idx % len(colors)])

    ax.set_xlabel("Update Cycle", fontsize=12)
    ax.set_ylabel("Fitness Score", fontsize=12)
    ax.set_title("Agent Fitness Evolution", fontsize=14, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def plot_regime_distribution(regime_counts: Dict[str, int]) -> str:
    """Generate regime distribution pie chart."""
    if not regime_counts:
        return ""

    fig, ax = plt.subplots(figsize=(8, 8))
    labels = list(regime_counts.keys())
    sizes = list(regime_counts.values())
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E"]

    ax.pie(sizes, labels=labels, autopct="%1.1f%%", startangle=90, colors=colors[: len(labels)])
    ax.set_title("Regime Distribution", fontsize=14, fontweight="bold")

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def plot_volatility_pnl_heatmap(volatility_pnl: Dict[str, Dict[str, float]]) -> str:
    """Generate volatility bucket PnL heatmap."""
    if not volatility_pnl:
        return ""

    # Prepare data for heatmap
    regimes = list(volatility_pnl.keys())
    vol_levels = ["low", "medium", "high"]
    data = []
    for regime in regimes:
        row = [volatility_pnl[regime].get(vol, 0.0) for vol in vol_levels]
        data.append(row)

    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(data, cmap="RdYlGn", aspect="auto")

    ax.set_xticks(range(len(vol_levels)))
    ax.set_xticklabels(vol_levels)
    ax.set_yticks(range(len(regimes)))
    ax.set_yticklabels(regimes)
    ax.set_xlabel("Volatility Level", fontsize=12)
    ax.set_ylabel("Regime", fontsize=12)
    ax.set_title("PnL by Regime × Volatility", fontsize=14, fontweight="bold")

    # Add text annotations
    for i in range(len(regimes)):
        for j in range(len(vol_levels)):
            text = ax.text(j, i, f"{data[i][j]:.2f}", ha="center", va="center", color="black", fontsize=10)

    plt.colorbar(im, ax=ax, label="PnL")
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def plot_weight_evolution(weight_history: Dict[str, List[float]]) -> str:
    """Generate adaptive weight evolution chart."""
    if not weight_history:
        return ""

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#6A994E"]
    for idx, (name, weights) in enumerate(weight_history.items()):
        if weights:
            ax.plot(weights, label=name, linewidth=2, color=colors[idx % len(colors)])

    ax.set_xlabel("Update Cycle", fontsize=12)
    ax.set_ylabel("Weight", fontsize=12)
    ax.set_title("Adaptive Weight Evolution", fontsize=14, fontweight="bold")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def render_options_equity_curve(equity_history: List[Tuple[datetime, float]], initial_capital: float) -> str:
    """Generate options equity curve plot as base64 encoded PNG."""
    if not equity_history:
        # Generate placeholder "No options trades yet" image
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No options trades yet", ha="center", va="center", 
                fontsize=16, color="gray", transform=ax.transAxes)
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Options Equity ($)", fontsize=12)
        ax.set_title("Options Equity Curve", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_base64
    
    # Extract timestamps and equity values
    timestamps = [t[0] for t in equity_history]
    equity_values = [t[1] for t in equity_history]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(timestamps, equity_values, linewidth=2, color="#9D4EDD")  # Purple for options
    ax.axhline(y=initial_capital, color="gray", linestyle="--", alpha=0.5, label="Initial Capital")
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Options Equity ($)", fontsize=12)
    ax.set_title("Options Equity Curve", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    # Rotate x-axis labels for readability
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    
    # Calculate and display stats
    if equity_values:
        final_value = equity_values[-1]
        total_return = ((final_value - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0
        ax.text(
            0.02,
            0.98,
            f"Total Return: {total_return:.2f}%",
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def render_options_drawdown(equity_history: List[Tuple[datetime, float]], initial_capital: float) -> str:
    """Generate options drawdown chart as base64 encoded PNG."""
    if not equity_history:
        # Generate placeholder
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "No options trades yet", ha="center", va="center", 
                fontsize=16, color="gray", transform=ax.transAxes)
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Drawdown (%)", fontsize=12)
        ax.set_title("Options Drawdown", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_base64
    
    # Extract equity values
    equity_values = [t[1] for t in equity_history]
    timestamps = [t[0] for t in equity_history]
    
    # Calculate drawdown
    peak = initial_capital
    drawdowns = []
    for value in equity_values:
        if value > peak:
            peak = value
        dd = ((peak - value) / peak) * 100.0 if peak > 0 else 0.0
        drawdowns.append(dd)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(range(len(drawdowns)), drawdowns, 0, color="#9D4EDD", alpha=0.6)
    ax.plot(drawdowns, linewidth=1, color="#9D4EDD")
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Drawdown (%)", fontsize=12)
    ax.set_title("Options Drawdown", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3)
    
    # Rotate x-axis labels
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    
    # Display max drawdown
    max_dd = max(drawdowns) if drawdowns else 0.0
    ax.text(
        0.02,
        0.98,
        f"Max Drawdown: {max_dd:.2f}%",
        transform=ax.transAxes,
        fontsize=10,
        verticalalignment="top",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def render_options_pnl_by_symbol(pnl_by_symbol: Dict[str, float]) -> str:
    """Generate bar chart of cumulative options P&L by symbol."""
    if not pnl_by_symbol:
        # Generate placeholder
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, "No options trades yet", ha="center", va="center", 
                fontsize=16, color="gray", transform=ax.transAxes)
        ax.set_xlabel("Symbol", fontsize=12)
        ax.set_ylabel("Cumulative P&L ($)", fontsize=12)
        ax.set_title("Options P&L by Symbol", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_base64
    
    symbols = list(pnl_by_symbol.keys())
    pnl_values = list(pnl_by_symbol.values())
    
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#10b981" if pnl >= 0 else "#ef4444" for pnl in pnl_values]  # Green for positive, red for negative
    bars = ax.bar(symbols, pnl_values, color=colors, alpha=0.7)
    
    # Add value labels on bars
    for bar, value in zip(bars, pnl_values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'${value:,.2f}',
                ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=10, fontweight='bold')
    
    ax.set_xlabel("Symbol", fontsize=12)
    ax.set_ylabel("Cumulative P&L ($)", fontsize=12)
    ax.set_title("Options P&L by Symbol", fontsize=14, fontweight="bold")
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def render_options_vs_stock_equity(
    stock_equity_curve: List[float],
    options_equity_history: List[Tuple[datetime, float]],
    stock_initial_capital: float,
    options_initial_capital: float,
) -> str:
    """Generate comparison chart of options vs stock equity curves (normalized to 1.0 at start)."""
    if not stock_equity_curve or not options_equity_history:
        # Generate placeholder
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.text(0.5, 0.5, "Insufficient data for comparison", ha="center", va="center", 
                fontsize=16, color="gray", transform=ax.transAxes)
        ax.set_xlabel("Time", fontsize=12)
        ax.set_ylabel("Normalized Equity", fontsize=12)
        ax.set_title("Options vs Stock Equity Comparison", fontsize=14, fontweight="bold")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        plt.close(fig)
        return img_base64
    
    # Normalize both to 1.0 at start
    stock_normalized = [v / stock_initial_capital for v in stock_equity_curve] if stock_initial_capital > 0 else stock_equity_curve
    options_equity_values = [t[1] for t in options_equity_history]
    options_normalized = [v / options_initial_capital for v in options_equity_values] if options_initial_capital > 0 else options_equity_values
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(stock_normalized, linewidth=2, color="#2E86AB", label="Stock Equity", alpha=0.8)
    if options_equity_history:
        timestamps = [t[0] for t in options_equity_history]
        # For comparison, we'll use indices if timestamps don't align
        ax.plot(range(len(options_normalized)), options_normalized, linewidth=2, 
                color="#9D4EDD", label="Options Equity", alpha=0.8)
    ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5, label="Baseline (1.0)")
    ax.set_xlabel("Time", fontsize=12)
    ax.set_ylabel("Normalized Equity", fontsize=12)
    ax.set_title("Options vs Stock Equity Comparison", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return img_base64


def create_interactive_dashboard(
    equity_curve: List[float],
    drawdowns: List[float],
    agent_fitness: Dict[str, List[float]],
    regime_counts: Dict[str, int],
) -> str:
    """Create an interactive Plotly dashboard HTML."""
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Equity Curve", "Drawdown", "Agent Fitness", "Regime Distribution"),
        specs=[[{"secondary_y": False}, {"secondary_y": False}], [{"secondary_y": False}, {"type": "pie"}]],
    )

    # Equity curve
    if equity_curve:
        fig.add_trace(go.Scatter(y=equity_curve, mode="lines", name="Equity", line=dict(color="#2E86AB")), row=1, col=1)

    # Drawdown
    if drawdowns:
        fig.add_trace(
            go.Scatter(y=drawdowns, mode="lines", fill="tozeroy", name="Drawdown", line=dict(color="#E63946")),
            row=1,
            col=2,
        )

    # Agent fitness
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D"]
    for idx, (agent, fitness) in enumerate(agent_fitness.items()):
        if fitness:
            fig.add_trace(
                go.Scatter(y=fitness, mode="lines", name=agent, line=dict(color=colors[idx % len(colors)])),
                row=2,
                col=1,
            )

    # Regime distribution
    if regime_counts:
        fig.add_trace(
            go.Pie(labels=list(regime_counts.keys()), values=list(regime_counts.values()), name="Regimes"),
            row=2,
            col=2,
        )

    fig.update_layout(height=800, title_text="FutBot Performance Dashboard", showlegend=True)
    return fig.to_html(include_plotlyjs="cdn")

