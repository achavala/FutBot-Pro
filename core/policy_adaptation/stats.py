from __future__ import annotations

from typing import Deque


def ema_smooth(old_value: float, new_value: float, alpha: float) -> float:
    """Exponential moving average smoothing."""
    return old_value * (1 - alpha) + new_value * alpha


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value between min and max."""
    return max(min_val, min(value, max_val))


def compute_ema_from_deque(values: Deque[float], decay: float) -> float:
    """Compute EMA from a deque of values using decay factor."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    result = values[0]
    for val in list(values)[1:]:
        result = result * decay + val * (1 - decay)
    return result


def percentage_change(old_val: float, new_val: float) -> float:
    """Compute percentage change between two values."""
    if old_val == 0:
        return 0.0 if new_val == 0 else float("inf")
    return abs((new_val - old_val) / old_val)

