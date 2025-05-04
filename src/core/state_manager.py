import threading
from src.utils.logger import logger
from src.utils.config import MAX_DAILY_ORDERS

class StateManager:
    def __init__(self):
        self.successful_orders_count = 0
        self.lock = threading.Lock()

    def increment_order_count(self) -> int:
        """Increment the successful orders count."""
        with self.lock:
            self.successful_orders_count += 1
            logger.info(f"Order count incremented. Current count: {self.successful_orders_count}")
            return self.successful_orders_count

    def decrement_order_count(self, count: int) -> int:
        """Decrement the successful orders count by the specified amount."""
        with self.lock:
            self.successful_orders_count = max(0, self.successful_orders_count - count)
            logger.info(f"Order count decremented by {count}. Current count: {self.successful_orders_count}")
            return self.successful_orders_count

    def reset_order_count(self) -> int:
        """Reset the successful orders count."""
        with self.lock:
            self.successful_orders_count = 0
            logger.info(f"Order count reset. Current count: {self.successful_orders_count}")
            return self.successful_orders_count

    @property
    def orders_remaining(self) -> int:
        """Get the number of remaining orders for the day."""
        return MAX_DAILY_ORDERS - self.successful_orders_count

# Global StateManager instance
_state_manager = None

def get_state_manager() -> StateManager:
    """Get the global StateManager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager