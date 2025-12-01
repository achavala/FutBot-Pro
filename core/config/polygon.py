"""Polygon API settings configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class PolygonSettings(BaseModel):
    """Polygon/Massive API settings."""
    
    api_key: str
    rest_url: str = "https://api.massive.com"  # Updated to Massive API (Polygon migrated)
    rate_limit_per_min: int = 5
    
    @classmethod
    def load(cls) -> PolygonSettings:
        """
        Load Polygon settings from config file or environment variable.
        
        Priority:
        1. config/settings.yaml
        2. POLYGON_API_KEY environment variable
        
        Returns:
            PolygonSettings instance
            
        Raises:
            RuntimeError: If API key not found
        """
        # 1. Try config/settings.yaml (your main config)
        yaml_path = Path("config/settings.yaml")
        if yaml_path.exists():
            try:
                import yaml
                with open(yaml_path, "r") as f:
                    data = yaml.safe_load(f)
                    if data and "polygon" in data:
                        polygon_data = data["polygon"]
                        if "api_key" in polygon_data:
                            return cls(
                                api_key=polygon_data["api_key"],
                                rest_url=polygon_data.get("rest_url", "https://api.massive.com"),
                                rate_limit_per_min=polygon_data.get("rate_limit_per_min", 5)
                            )
            except Exception as e:
                # If YAML parsing fails, fall through to env var
                pass
        
        # 2. Try environment variable
        api_key = os.environ.get("POLYGON_API_KEY")
        if api_key:
            return cls(api_key=api_key)
        
        raise RuntimeError(
            "Polygon API key not found. "
            "Please set it in config/settings.yaml (polygon.api_key) "
            "or set POLYGON_API_KEY environment variable."
        )

