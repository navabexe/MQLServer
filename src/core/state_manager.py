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