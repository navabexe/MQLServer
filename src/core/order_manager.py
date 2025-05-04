import MetaTrader5 as mt5
from typing import Dict, Optional, List
from src.api.dependencies import get_mt5_client
from src.core.state_manager import get_state_manager, StateManager
from src.data.mt5_client import MT5Client
from src.models.order import OrderRequest
from src.models.position import Position
from src.utils.config import MAX_DAILY_ORDERS, MUST_RISK_AMOUNT
from src.utils.helpers import calculate_pips, get_pip_value
from src.utils.logger import logger

class OrderManager:
    def __init__(self):
        self.state_manager = get_state_manager()

    def place_order(self, order: OrderRequest, mt5_client: MT5Client = get_mt5_client()) -> Dict[str, str | int]:
        """Place a new order in MT5."""
        if self.state_manager.successful_orders_count >= MAX_DAILY_ORDERS:
            logger.warning("Maximum daily orders reached")
            return {"status": "error", "message": "Maximum daily orders reached"}

        # Validate prices
        try:
            entry_price = float(order.entry_price)
            stop_loss = float(order.stop_loss)
        except ValueError:
            logger.error("Invalid price format")
            return {"status": "error", "message": "Invalid price format"}

        # Get current market price
        price_info = mt5_client.get_current_price(order.symbol)
        if not price_info:
            return {"status": "error", "message": "Failed to get market price"}

        current_price = price_info["ask"] if order.position_type.startswith("buy") else price_info["bid"]

        # Determine order type
        order_type = self._determine_order_type(order.position_type, current_price, entry_price)
        if order_type is None:
            logger.error("Invalid position type or price settings")
            return {"status": "error", "message": "Invalid position type or price settings"}

        # Calculate lot size and stop loss in USD
        lot_size, report_risk_amount = self._calculate_lot_and_stop_loss(
            order.symbol, entry_price, stop_loss, MUST_RISK_AMOUNT
        )

        # Risk management checks
        max_allowed_risk = MUST_RISK_AMOUNT * 1.2
        min_required_risk = MUST_RISK_AMOUNT * 0.8
        if report_risk_amount > max_allowed_risk:
            logger.warning("Stop loss amount exceeds risk management limit")
            return {"status": "error", "message": "Stop loss amount exceeds risk management limit"}
        if report_risk_amount < min_required_risk:
            logger.warning("Risk amount below minimum required limit")
            return {"status": "error", "message": "Risk amount below minimum required limit"}

        # Calculate take profit
        take_profit = (
            entry_price + (order.risk_to_reward * abs(entry_price - stop_loss))
            if order.position_type.startswith("buy")
            else entry_price - (order.risk_to_reward * abs(entry_price - stop_loss))
        )

        # Prepare order request
        order_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": order.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": entry_price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": 20,
            "magic": 234000,
            "comment": "propiy",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }

        # Send order
        result = mt5_client.place_order(order_request)
        if result and result["status"] == "success":
            self.state_manager.increment_order_count()
            orders_left = MAX_DAILY_ORDERS - self.state_manager.successful_orders_count
            logger.info(f"Order placed successfully. {orders_left} orders left for today")
            return {
                "status": "success",
                "message": f"Order placed successfully. {orders_left} orders left for today",
                "order_id": result["order_id"]
            }
        return result or {"status": "error", "message": "Unknown error occurred"}

    def get_all_orders_and_positions(self, mt5_client: MT5Client = get_mt5_client()) -> List[Position]:
        """Retrieve all open positions and pending orders."""
        positions = mt5_client.get_positions()
        orders = mt5_client.get_orders()
        type_map = {
            mt5.ORDER_TYPE_BUY: "Buy",
            mt5.ORDER_TYPE_SELL: "Sell",
            mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit",
            mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit",
            mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
            mt5.ORDER_TYPE_SELL_STOP: "Sell Stop",
        }

        combined_list = []
        for position in positions:
            pips = calculate_pips(position.price_open, position.sl, position.symbol)
            combined_list.append(Position(
                ticket=position.ticket,
                symbol=position.symbol,
                type=type_map.get(position.type, "Unknown"),
                entry_price=position.price_open,
                stop_loss=position.sl,
                take_profit=position.tp,
                status="open",
                pips=pips or 0.0
            ))

        for order in orders:
            pips = calculate_pips(order.price_open, order.sl, order.symbol)
            combined_list.append(Position(
                ticket=order.ticket,
                symbol=order.symbol,
                type=type_map.get(order.type, "Unknown"),
                entry_price=order.price_open,
                stop_loss=order.sl,
                take_profit=order.tp,
                status="pending",
                pips=pips or 0.0
            ))

        return combined_list

    def _determine_order_type(self, position_type: str, current_price: float, entry_price: float) -> Optional[int]:
        """Determine MT5 order type based on position type and prices."""
        try:
            if position_type == "buy":
                return mt5.ORDER_TYPE_BUY_LIMIT if current_price > entry_price else mt5.ORDER_TYPE_BUY_STOP
            elif position_type == "sell":
                return mt5.ORDER_TYPE_SELL_LIMIT if current_price < entry_price else mt5.ORDER_TYPE_SELL_STOP
            elif position_type == "buy limit":
                return mt5.ORDER_TYPE_BUY_LIMIT
            elif position_type == "sell limit":
                return mt5.ORDER_TYPE_SELL_LIMIT
            elif position_type == "buy stop":
                return mt5.ORDER_TYPE_BUY_STOP
            elif position_type == "sell stop":
                return mt5.ORDER_TYPE_SELL_STOP
        except Exception as e:
            logger.error(f"Error determining order type: {e}")
        return None

    def _calculate_lot_and_stop_loss(self, symbol: str, entry_price: float, stop_loss: float, max_loss_usd: float) -> tuple[float, float]:
        """Calculate lot size and stop loss in USD."""
        pip_value = get_pip_value(symbol)
        pip_difference = abs(entry_price - stop_loss) / pip_value

        # Calculate pip value in USD (simplified, assuming USD as quote currency)
        if symbol == "BTCUSD":
            pip_value_usd = pip_value * 1  # Assuming 1 BTC = 1 lot
        elif symbol.endswith("USD"):
            pip_value_usd = pip_value * 100000
        elif symbol.startswith("USD"):
            pip_value_usd = (pip_value / entry_price) * 100000
        else:
            # For non-USD pairs, assume conversion rate = 1 (to be improved with API)
            pip_value_usd = (pip_value / entry_price) * 100000

        lot_size = max_loss_usd / (pip_difference * pip_value_usd)
        lot_size = round(lot_size, 2)
        stop_loss_usd = pip_difference * pip_value_usd * lot_size
        return lot_size, stop_loss_usd