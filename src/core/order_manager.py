import MetaTrader5 as mt5
from typing import Dict, Optional, List
from decimal import Decimal, ROUND_DOWN
from src.api.dependencies import get_mt5_client
from src.core.state_manager import get_state_manager, StateManager
from src.data.mt5_client import MT5Client
from src.models.order import OrderRequest
from src.models.position import Position
from src.utils.config import MAX_DAILY_ORDERS, MUST_RISK_AMOUNT, COMMENT
from src.utils.helpers import calculate_pips, get_pip_value, get_conversion_rate
from src.utils.logger import logger

class OrderManager:
    def __init__(self):
        self.state_manager = get_state_manager()

    def place_order(self, order: OrderRequest, mt5_client: MT5Client = get_mt5_client()) -> Dict[str, str | int]:
        if self.state_manager.successful_orders_count >= MAX_DAILY_ORDERS:
            logger.warning("Maximum daily orders reached")
            return {"status": "error", "message": "Maximum daily orders reached"}
        try:
            entry_price = float(order.entry_price)
            stop_loss = float(order.stop_loss)
        except ValueError:
            logger.error("Invalid price format")
            return {"status": "error", "message": "Invalid price format"}
        price_info = mt5_client.get_current_price(order.symbol)
        if not price_info:
            return {"status": "error", "message": "Failed to get market price"}
        current_price = price_info["ask"] if order.position_type.startswith("buy") else price_info["bid"]
        order_type = self._determine_order_type(order.position_type, current_price, entry_price)
        if order_type is None:
            logger.error("Invalid position type or price settings")
            return {"status": "error", "message": "Invalid position type or price settings"}
        lot_size, report_risk_amount = self._calculate_lot_and_stop_loss(
            order.symbol, entry_price, stop_loss, MUST_RISK_AMOUNT, mt5_client
        )
        max_allowed_risk = MUST_RISK_AMOUNT * 1.2
        min_required_risk = MUST_RISK_AMOUNT * 0.8
        if report_risk_amount > max_allowed_risk:
            logger.warning("Stop loss amount exceeds risk management limit")
            return {"status": "error", "message": "Stop loss amount exceeds risk management limit"}
        if report_risk_amount < min_required_risk:
            logger.warning("Risk amount below minimum required limit")
            return {"status": "error", "message": "Risk amount below minimum required limit"}
        take_profit = (
            entry_price + (order.risk_to_reward * abs(entry_price - stop_loss))
            if order.position_type.startswith("buy")
            else entry_price - (order.risk_to_reward * abs(entry_price - stop_loss))
        )
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
            "comment": COMMENT,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
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

    def cancel_pending_orders(self, mt5_client: MT5Client = get_mt5_client()) -> Dict[str, str | int]:
        try:
            orders = mt5_client.get_orders()
            if not orders:
                logger.info("No pending orders to cancel")
                return {"status": "success", "message": "No pending orders to cancel", "canceled_count": 0}
            canceled_count = 0
            for order in orders:
                request = {
                    "action": mt5.TRADE_ACTION_REMOVE,
                    "order": order.ticket,
                }
                result = mt5.order_send(request)
                if result.retcode == mt5.TRADE_RETCODE_DONE:
                    logger.info(f"Pending order {order.ticket} canceled successfully")
                    canceled_count += 1
                else:
                    logger.error(f"Failed to cancel pending order {order.ticket}: {result.comment}")
            if canceled_count > 0:
                self.state_manager.decrement_order_count(canceled_count)
                logger.info(
                    f"Canceled {canceled_count} pending orders. New order count: {self.state_manager.successful_orders_count}")
            return {
                "status": "success",
                "message": f"Canceled {canceled_count} pending orders",
                "canceled_count": canceled_count
            }
        except Exception as e:
            logger.error(f"Error canceling pending orders: {str(e)}")
            return {"status": "error", "message": f"Failed to cancel pending orders: {str(e)}", "canceled_count": 0}

    def _determine_order_type(self, position_type: str, current_price: float, entry_price: float) -> Optional[int]:
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

    def _calculate_lot_and_stop_loss(self, symbol: str, entry_price: float, stop_loss: float, max_loss_usd: float,
                                     mt5_client: MT5Client) -> tuple[float, float]:
        pip_value = Decimal(str(get_pip_value(symbol)))
        pip_difference = Decimal(str(abs(entry_price - stop_loss))) / pip_value
        pip_difference = pip_difference.quantize(Decimal('0.01'), rounding=ROUND_DOWN)

        price_info = mt5_client.get_current_price(symbol)
        if not price_info:
            logger.error(f"Failed to get price info for {symbol} to calculate spread")
            spread_pips = Decimal('0')
        else:
            spread_pips = Decimal(str((price_info["ask"] - price_info["bid"]) / float(pip_value)))
            spread_pips = spread_pips.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            logger.info(f"Spread for {symbol}: {spread_pips} pips")

        # محاسبه ارزش پیپ به USD
        if symbol == "BTCUSD":
            pip_value_usd = pip_value * Decimal('1')
            conversion_info = "BTCUSD: No conversion needed"
        elif symbol.endswith("USD"):
            if symbol == "XAUUSD":
                pip_value_usd = pip_value * Decimal('10')  # هر پیپ برای 1 لات = 0.1 دلار
            elif symbol == "XAGUSD":
                pip_value_usd = pip_value * Decimal('50')  # هر پیپ برای 1 لات = 0.05 دلار
            else:
                pip_value_usd = pip_value * Decimal('100000')  # برای جفت‌ارزهای استاندارد مثل EURUSD
            conversion_info = f"XXXUSD: Standard pip value scaling for {symbol}"
        elif symbol.startswith("USD"):
            quote_currency = symbol[3:]
            price_info = mt5_client.get_current_price(f"USD{quote_currency}")
            if not price_info:
                logger.error(f"Failed to get price info for USD{quote_currency}")
                raise ValueError(f"Currency pair USD{quote_currency} not available in MT5")
            conversion_rate = Decimal(str(1 / ((price_info["bid"] + price_info["ask"]) / 2)))
            pip_value_usd = pip_value * Decimal('100000') * conversion_rate
            conversion_info = f"USDXXX: quote_currency={quote_currency}, conversion_rate={conversion_rate}"
        else:
            base_currency = symbol[:3]
            quote_currency = symbol[3:]
            price_info = mt5_client.get_current_price(f"{quote_currency}USD")
            if price_info:
                quote_to_usd = Decimal(str((price_info["bid"] + price_info["ask"]) / 2))
                logger.info(f"Updated quote_to_usd for {quote_currency} to USD: {quote_to_usd}")
            else:
                price_info = mt5_client.get_current_price(f"USD{quote_currency}")
                if price_info:
                    quote_to_usd = Decimal(str(1 / ((price_info["bid"] + price_info["ask"]) / 2)))
                    logger.info(f"Updated quote_to_usd for {quote_currency} to USD using USD{quote_currency}: {quote_to_usd}")
                else:
                    logger.error(f"Failed to get price info for {quote_currency}USD or USD{quote_currency}")
                    raise ValueError(f"Currency pair {quote_currency}USD or USD{quote_currency} not available in MT5")
            pip_value_usd = (pip_value / Decimal(str(entry_price))) * Decimal('100000') * quote_to_usd
            conversion_info = f"Non-USD pair: base_currency={base_currency}, quote_currency={quote_currency}, quote_to_usd={quote_to_usd}"

        # محاسبه حجم اولیه
        lot_size = Decimal(str(max_loss_usd)) / (pip_difference * pip_value_usd)
        original_lot_size = lot_size

        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Failed to get symbol info for {symbol}")
            volume_step = Decimal('0.01')
            volume_min = Decimal('0.01')
            volume_max = Decimal('100')
        else:
            volume_step = Decimal(str(symbol_info.volume_step))
            volume_min = Decimal(str(symbol_info.volume_min))
            volume_max = Decimal(str(symbol_info.volume_max))
            logger.info(f"Volume step for {symbol}: {volume_step}, Volume min: {volume_min}, Volume max: {volume_max}")

        # رند کردن حجم به نزدیک‌ترین مضرب volume_step با رعایت volume_min و volume_max
        lot_size_lower = max((lot_size / volume_step).to_integral_value(rounding=ROUND_DOWN) * volume_step, volume_min)
        lot_size_upper = lot_size_lower + volume_step
        lot_size_lower = lot_size_lower.quantize(Decimal('0.001'), rounding=ROUND_DOWN)
        lot_size_upper = min(lot_size_upper.quantize(Decimal('0.001'), rounding=ROUND_DOWN), volume_max)

        # محاسبه ریسک برای هر حجم
        risk_lower = pip_difference * pip_value_usd * lot_size_lower
        risk_upper = pip_difference * pip_value_usd * lot_size_upper

        # انتخاب حجم با ریسک نزدیک‌تر به 30 دلار
        if abs(risk_lower - Decimal(str(max_loss_usd))) <= abs(risk_upper - Decimal(str(max_loss_usd))):
            lot_size = lot_size_lower
            adjusted_risk_usd = risk_lower
        else:
            lot_size = lot_size_upper
            adjusted_risk_usd = risk_upper

        # افزودن کمیسیون (اگر وجود دارد)
        commission_per_lot = Decimal('0.0')  # مقدار کمیسیون به USD برای هر لات (از بروکر خود بگیرید)
        total_risk_usd = adjusted_risk_usd + (commission_per_lot * lot_size)

        logger.info(
            f"Lot size calculation for {symbol}: "
            f"entry_price={entry_price}, stop_loss={stop_loss}, "
            f"pip_value={pip_value}, pip_difference={pip_difference}, "
            f"pip_value_usd={pip_value_usd}, lot_size={lot_size}, "
            f"original_lot_size={original_lot_size}, "
            f"lot_size_lower={lot_size_lower}, lot_size_upper={lot_size_upper}, "
            f"risk_lower={risk_lower}, risk_upper={risk_upper}, "
            f"adjusted_risk_usd={adjusted_risk_usd}, "
            f"spread_pips={spread_pips}, commission_per_lot={commission_per_lot}, "
            f"total_risk_usd={total_risk_usd}, {conversion_info}"
        )

        return float(lot_size), float(total_risk_usd)