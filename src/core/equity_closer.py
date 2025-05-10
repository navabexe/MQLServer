import MetaTrader5 as mt5
from typing import Dict, Optional
from src.api.dependencies import get_mt5_client
from src.data.mt5_client import MT5Client
from src.utils.logger import logger


class EquityCloser:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EquityCloser, cls).__new__(cls)
            cls._instance.targets = {"profit": 0.0, "loss": 0.0}
            cls._instance.is_active = False
            logger.debug("Created new EquityCloser instance")
        return cls._instance

    def set_equity_targets(self, profit_equity: float, loss_equity: float) -> Dict[str, str]:
        logger.debug(f"Setting equity targets: Profit={profit_equity}, Loss={loss_equity}")
        if profit_equity <= loss_equity:
            logger.error("Profit equity must be greater than loss equity")
            return {"status": "error", "message": "Profit equity must be greater than loss equity"}

        self.targets["profit"] = profit_equity
        self.targets["loss"] = loss_equity
        self.is_active = True
        logger.info(f"Equity targets set: Profit={profit_equity}, Loss={loss_equity}, is_active={self.is_active}")
        return {"status": "success", "message": "Equity targets set successfully"}

    def check_and_close_positions(self, mt5_client: MT5Client = get_mt5_client()) -> Optional[Dict[str, str]]:
        logger.debug("Starting equity check")

        if not mt5_client.ensure_connection():
            logger.error("MT5 not connected")
            return {"status": "error", "message": "MT5 not connected"}

        account_info = mt5.account_info()
        if not account_info:
            logger.error("Failed to retrieve MT5 account info")
            return {"status": "error", "message": "Failed to retrieve account info"}

        current_equity = account_info.equity
        logger.info(f"Current equity: {current_equity}, is_active={self.is_active}")

        if not self.is_active:
            logger.debug("Equity closer is not active, skipping target check")
            return None

        logger.info(f"Checking targets: Profit={self.targets['profit']}, Loss={self.targets['loss']}")

        if current_equity >= self.targets["profit"] or current_equity <= self.targets["loss"]:
            logger.info(f"Equity target hit: Current={current_equity}, Closing all positions")
            return self.close_all_positions_and_orders(mt5_client)

        logger.debug("Equity targets not met")
        return None

    def _close_all_positions(self, mt5_client: MT5Client) -> Dict[str, str]:
        positions = mt5_client.get_positions()

        if not positions:
            logger.info("No open positions to close")
            self.is_active = False
            return {"status": "success", "message": "No open positions to close", "closed_count": 0}

        closed_count = 0

        for position in positions:
            logger.info(f"Processing position {position.ticket} for {position.symbol}")

            price_info = mt5_client.get_current_price(position.symbol)
            if not price_info:
                logger.error(f"Failed to get price for {position.symbol}")
                continue

            symbol_info = mt5.symbol_info(position.symbol)
            if not symbol_info:
                logger.error(f"Failed to get symbol info for {position.symbol}")
                continue

            logger.info(f"{position.symbol} filling_mode={symbol_info.filling_mode}")

            order_type = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
            price = price_info["bid"] if position.type == mt5.ORDER_TYPE_BUY else price_info["ask"]

            volume_step = symbol_info.volume_step or 0.01
            volume = round(position.volume / volume_step) * volume_step
            volume = min(max(volume, symbol_info.volume_min), symbol_info.volume_max)

            # Always try all filling types regardless of symbol_info
            filling_types = [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]

            for filling_type in filling_types:
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "position": position.ticket,
                    "symbol": position.symbol,
                    "volume": volume,
                    "type": order_type,
                    "price": price,
                    "deviation": 50,
                    "magic": 234000,
                    "comment": "Auto-close on equity target",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": filling_type,
                }
                result = mt5_client.place_order(request)
                if result and result["status"] == "success":
                    logger.info(f"Successfully closed position {position.ticket} with filling type {filling_type}")
                    closed_count += 1
                    break
                else:
                    msg = result.get("message", "Unknown error") if result else "No response"
                    logger.warning(f"Failed to close position {position.ticket} with filling {filling_type}: {msg}")
            else:
                logger.error(f"All filling modes failed for position {position.ticket}")

        if closed_count > 0:
            self.is_active = False
            logger.info(f"Closed {closed_count} positions, setting is_active to False")
            return {
                "status": "success",
                "message": f"Closed {closed_count} positions due to equity target",
                "closed_count": closed_count
            }

        return {"status": "error", "message": "Failed to close positions", "closed_count": 0}

    def close_all_positions_and_orders(self, mt5_client: MT5Client) -> Dict[str, str]:
        logger.info("Closing all open positions and cancelling all pending orders")

        result_positions = self._close_all_positions(mt5_client)

        orders = mt5_client.get_orders()
        canceled_count = 0

        for order in orders:
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": order.ticket
            }
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Successfully cancelled pending order {order.ticket}")
                canceled_count += 1
            else:
                logger.warning(f"Failed to cancel pending order {order.ticket}: {result.comment if result else 'No response'}")

        result_positions["canceled_orders"] = canceled_count
        result_positions["message"] += f", Canceled {canceled_count} pending orders"
        return result_positions
