from __future__ import annotations

import base64
import io
from typing import Dict, List, Optional

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

