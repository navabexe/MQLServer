import mt5

from src.api.dependencies import get_mt5_client
from src.data.mt5_client import MT5Client
from src.utils.logger import logger
from src.utils.helpers import get_pip_value
from typing import Dict

class StopLossManager:
    def __init__(self):
        self.in_memory_risk = {}

    def make_risk_free(self, ticket_id: int, mt5_client: MT5Client = get_mt5_client()) -> Dict[str, str | int | float]:
        """Set stop loss to entry price to make the position risk-free, and adjust further if already risk-free."""
        positions = mt5_client.get_positions()
        position = next((p for p in positions if p.ticket == ticket_id), None)
        if not position:
            logger.error(f"Position with ticket ID {ticket_id} not found")
            return {"status": "error", "message": f"Position with ticket ID {ticket_id} not found"}

        entry_price = position.price_open
        stop_loss = position.sl
        current_price = position.price_current
        position_type = position.type
        pip_value = get_pip_value(position.symbol)
        pip_movement = 10 * pip_value  # Default movement in pips

        # Store initial risk if not already stored
        if ticket_id not in self.in_memory_risk:
            if stop_loss == 0:
                if position_type == mt5.ORDER_TYPE_BUY and current_price > entry_price:
                    stop_loss = entry_price
                elif position_type == mt5.ORDER_TYPE_SELL and current_price < entry_price:
                    stop_loss = entry_price
                else:
                    logger.error(f"Position is not in profit for ticket ID {ticket_id}")
                    return {
                        "status": "error",
                        "message": f"Position is not in profit for ticket ID {ticket_id}. Stop loss not adjusted."
                    }
            self.in_memory_risk[ticket_id] = abs(entry_price - stop_loss)

        risk_amount = self.in_memory_risk.get(ticket_id, pip_movement)

        # Calculate new stop loss
        if position_type == mt5.ORDER_TYPE_BUY:
            # If stop loss is already at or above entry price, move it further towards profit
            if stop_loss >= entry_price:
                new_stop_loss = stop_loss + risk_amount
            else:
                new_stop_loss = entry_price  # First time making risk-free

            # Ensure new stop loss doesn't exceed a safe threshold below current price
            safe_threshold = current_price - (pip_value * 5)  # 5 pips below current price
            if new_stop_loss >= safe_threshold:
                logger.warning(f"New stop loss {new_stop_loss} too close to current price {current_price}, setting to safe threshold")
                new_stop_loss = safe_threshold

        elif position_type == mt5.ORDER_TYPE_SELL:
            # If stop loss is already at or below entry price, move it further towards profit
            if stop_loss <= entry_price:
                new_stop_loss = stop_loss - risk_amount
            else:
                new_stop_loss = entry_price  # First time making risk-free

            # Ensure new stop loss doesn't go below a safe threshold above current price
            safe_threshold = current_price + (pip_value * 5)  # 5 pips above current price
            if new_stop_loss <= safe_threshold:
                logger.warning(f"New stop loss {new_stop_loss} too close to current price {current_price}, setting to safe threshold")
                new_stop_loss = safe_threshold
        else:
            logger.error(f"Invalid position type for ticket ID {ticket_id}")
            return {"status": "error", "message": "Invalid position type"}

        # Update stop loss
        if mt5_client.modify_order(ticket_id, new_stop_loss, position.tp):
            logger.info(f"Stop loss for ticket ID {ticket_id} updated to {new_stop_loss}")
            return {
                "status": "success",
                "message": f"Stop loss updated successfully to {new_stop_loss}",
                "ticket_id": ticket_id,
                "new_stop_loss": new_stop_loss
            }
        logger.error(f"Failed to update stop loss for ticket ID {ticket_id}")
        return {"status": "error", "message": "Failed to update stop loss"}