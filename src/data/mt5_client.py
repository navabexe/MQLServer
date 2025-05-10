import MetaTrader5 as mt5
from src.utils.config import ACCOUNTS
from src.utils.logger import logger
from typing import Dict, Optional, List, Any

class MT5Client:
    def __init__(self, account_type: str = "real"):
        self.account_type = account_type
        self.connected = False

    def connect(self) -> bool:
        account = ACCOUNTS.get(self.account_type)
        if not account:
            logger.error(f"Invalid account type: {self.account_type}")
            return False
        try:
            if not mt5.initialize():
                logger.error("Failed to initialize MT5")
                return False
            if not mt5.login(account["login"], account["password"], account["server"]):
                logger.error(f"Failed to login to MT5 account: {self.account_type}")
                return False
            self.connected = True
            logger.info(f"Connected to MT5 account: {self.account_type}")
            return True
        except Exception as e:
            logger.error(f"MT5 connection error: {e}")
            return False

    def ensure_connection(self) -> bool:
        """Ensure MT5 connection, reconnect if necessary."""
        if self.connected:
            return True
        logger.warning("MT5 connection lost, attempting to reconnect")
        return self.connect()

    def get_current_price(self, symbol: str) -> Optional[Dict[str, float]]:
        if not self.ensure_connection():
            logger.error("MT5 not connected")
            return None
        price_info = mt5.symbol_info_tick(symbol)
        if price_info is None:
            logger.error(f"Failed to get price for {symbol}")
            return None
        return {"bid": price_info.bid, "ask": price_info.ask}

    def place_order(self, order_request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.ensure_connection():
            logger.error("MT5 not connected")
            return None
        result = mt5.order_send(order_request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Order placed successfully: {result.order}")
            return {"status": "success", "order_id": result.order}
        else:
            error_message = self._translate_error(result.retcode if result else 0)
            logger.error(f"Order placement failed: {error_message}")
            return {"status": "error", "message": error_message}

    def get_positions(self) -> List[Any]:
        if not self.ensure_connection():
            logger.error("MT5 not connected")
            return []
        positions = mt5.positions_get()
        return positions if positions else []

    def get_orders(self) -> List[Any]:
        if not self.ensure_connection():
            logger.error("MT5 not connected")
            return []
        orders = mt5.orders_get()
        return orders if orders else []

    def switch_account(self, account_type: str) -> Dict[str, str]:
        if account_type not in ACCOUNTS:
            logger.error(f"Invalid account type: {account_type}")
            return {"status": "error", "message": "Invalid account type"}
        if account_type == self.account_type:
            return {"status": "success", "message": "Already on this account"}
        mt5.shutdown()
        self.account_type = account_type
        self.connected = False
        if self.connect():
            return {"status": "success", "message": f"Switched to {account_type} account"}
        return {"status": "error", "message": "Failed to connect to new account"}

    def modify_order(self, ticket: int, stop_loss: float, take_profit: float) -> bool:
        if not self.ensure_connection():
            logger.error("MT5 not connected")
            return False
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": stop_loss,
            "tp": take_profit
        }
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Order {ticket} modified: SL={stop_loss}, TP={take_profit}")
            return True
        logger.error(f"Failed to modify order {ticket}: {result.comment if result else 'Unknown error'}")
        return False

    def _translate_error(self, code: int) -> str:
        error_messages = {
            mt5.TRADE_RETCODE_DONE: "Operation completed successfully",
            mt5.TRADE_RETCODE_REJECT: "Order rejected",
            mt5.TRADE_RETCODE_INVALID_FILL: "Invalid order filling type",
            10014: "Volume value error",
            10015: "Connection error",
            10016: "Network error",
            10017: "Server access error",
            10030: "Invalid order filling type"
        }
        return error_messages.get(code, f"Unknown error with code {code}")