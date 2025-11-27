from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


class StateStore:
    """Persistent state storage for live trading."""

    def __init__(self, state_file: Path = Path("state/live_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def save_state(self, state: Dict[str, Any]) -> None:
        """Save state to file."""
        # Convert any non-serializable types
        serializable_state = self._make_serializable(state)
        with open(self.state_file, "w") as f:
            json.dump(serializable_state, f, indent=2, default=str)

    def load_state(self) -> Dict[str, Any]:
        """Load state from file."""
        if not self.state_file.exists():
            return {}

        with open(self.state_file, "r") as f:
            return json.load(f)

    def clear_state(self) -> None:
        """Clear state file."""
        if self.state_file.exists():
            self.state_file.unlink()

    def _make_serializable(self, obj: Any) -> Any:
        """Convert object to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (int, float, str, bool, type(None))):
            return obj
        else:
            return str(obj)

    def update_state(self, updates: Dict[str, Any]) -> None:
        """Update state with new values."""
        current_state = self.load_state()
        current_state.update(updates)
        self.save_state(current_state)

