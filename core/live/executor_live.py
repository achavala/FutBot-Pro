from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.live.broker_client import BaseBrokerClient
from core.live.types import Order, OrderSide, OrderType, TimeInForce
from core.policy.types import FinalTradeIntent
from core.regime.types import RegimeType, VolatilityLevel


@dataclass
class ExecutionResult:
    """Result of live trade execution."""

    success: bool
    order: Optional[Order] = None
    reason: str = ""
    position_delta_applied: float = 0.0


class LiveTradeExecutor:
    """Executes trade intents via broker client."""

    def __init__(self, broker_client: BaseBrokerClient):
        self.broker_client = broker_client

    def apply_intent(
        self,
        intent: FinalTradeIntent,
        symbol: str,
        current_price: float,
        current_position: float,
        risk_constraints: Optional[dict] = None,
    ) -> ExecutionResult:
        """
        Apply trade intent to broker.

        Args:
            intent: Final trade intent from meta-policy
            symbol: Trading symbol
            current_price: Current market price
            current_position: Current position quantity (positive = long, negative = short)
            risk_constraints: Optional risk constraints dict

        Returns:
            ExecutionResult with order details
        """
        if not intent.is_valid or intent.position_delta == 0:
            return ExecutionResult(success=False, reason="Invalid intent or zero delta")

        # Calculate target position
        target_position = current_position + intent.position_delta

        # Determine order side and quantity
        if target_position > current_position:
            # Need to buy
            side = OrderSide.BUY
            quantity = target_position - current_position
        elif target_position < current_position:
            # Need to sell
            side = OrderSide.SELL
            quantity = current_position - target_position
        else:
            return ExecutionResult(success=False, reason="No position change needed")

        # Apply risk constraints if provided
        reason = ""
        if risk_constraints:
            max_size = risk_constraints.get("max_size", float("inf"))
            if quantity > max_size:
                quantity = max_size
                reason = f"Quantity capped by risk: {quantity}"

        # Submit order
        try:
            # CRITICAL FIX: Pass current_price to broker so it uses correct fill price
            order = self.broker_client.submit_order(
                symbol=symbol,
                side=side,
                quantity=abs(quantity),
                order_type=OrderType.MARKET,  # Use market orders for now
                time_in_force=TimeInForce.DAY,
                current_price=current_price,  # Pass the actual current price
            )

            return ExecutionResult(
                success=True,
                order=order,
                reason=reason or "Order submitted successfully",
                position_delta_applied=quantity if side == OrderSide.BUY else -quantity,
            )
        except Exception as e:
            return ExecutionResult(success=False, reason=f"Order submission failed: {str(e)}")

    def close_position(self, symbol: str, current_position: float, current_price: Optional[float] = None) -> ExecutionResult:
        """Close entire position."""
        if current_position == 0:
            return ExecutionResult(success=False, reason="No position to close")

        side = OrderSide.SELL if current_position > 0 else OrderSide.BUY
        quantity = abs(current_position)

        try:
            # CRITICAL FIX: Pass current_price to broker so it uses correct fill price
            order = self.broker_client.submit_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                order_type=OrderType.MARKET,
                time_in_force=TimeInForce.DAY,
                current_price=current_price,  # Pass current price for paper trading
            )

            return ExecutionResult(
                success=True,
                order=order,
                reason="Position closed",
                position_delta_applied=-current_position,
            )
        except Exception as e:
            return ExecutionResult(success=False, reason=f"Close position failed: {str(e)}")

