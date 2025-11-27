from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import yaml

from core.regime.types import RegimeType, VolatilityLevel


class PolicyConfigManager:
    """Manages loading and saving adaptive policy weights to/from YAML."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config/adaptive_weights.yaml")
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def load_weights(
        self,
    ) -> tuple[Dict[str, float], Dict[RegimeType, float], Dict[VolatilityLevel, float], Dict[str, float]]:
        """Load weights from YAML file."""
        if not self.config_path.exists():
            return self._default_weights()

        with open(self.config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        agent_weights = data.get("agent_weights", {})
        regime_weights = {RegimeType(k): v for k, v in data.get("regime_weights", {}).items()}
        volatility_weights = {VolatilityLevel(k): v for k, v in data.get("volatility_weights", {}).items()}
        structure_weights = data.get("structure_weights", {})

        return agent_weights, regime_weights, volatility_weights, structure_weights

    def save_weights(
        self,
        agent_weights: Dict[str, float],
        regime_weights: Dict[RegimeType, float],
        volatility_weights: Dict[VolatilityLevel, float],
        structure_weights: Dict[str, float],
    ) -> None:
        """Save weights to YAML file."""
        data = {
            "agent_weights": agent_weights,
            "regime_weights": {k.value: v for k, v in regime_weights.items()},
            "volatility_weights": {k.value: v for k, v in volatility_weights.items()},
            "structure_weights": structure_weights,
        }
        with open(self.config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def _default_weights(
        self,
    ) -> tuple[Dict[str, float], Dict[RegimeType, float], Dict[VolatilityLevel, float], Dict[str, float]]:
        """Return default weight configuration."""
        agent_weights = {
            "trend_agent": 1.0,
            "mean_reversion_agent": 0.9,
            "volatility_agent": 0.8,
            "fvg_agent": 1.1,
        }
        regime_weights = {
            RegimeType.TREND: 1.2,
            RegimeType.MEAN_REVERSION: 1.2,
            RegimeType.COMPRESSION: 0.8,
            RegimeType.EXPANSION: 1.0,
            RegimeType.NEUTRAL: 1.0,
        }
        volatility_weights = {
            VolatilityLevel.LOW: 1.0,
            VolatilityLevel.MEDIUM: 1.0,
            VolatilityLevel.HIGH: 0.9,
        }
        structure_weights = {"aligned": 1.2, "conflict": 0.8, "none": 1.0}
        return agent_weights, regime_weights, volatility_weights, structure_weights

