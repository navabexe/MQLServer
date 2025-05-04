import schedule
import threading
import time
from src.core.state_manager import get_state_manager
from src.utils.config import RESET_ORDER_TIME
from src.utils.logger import logger

def start_scheduler():
    """Start the scheduler for resetting order count."""
    try:
        state_manager = get_state_manager()
        schedule.every().day.at(RESET_ORDER_TIME).do(state_manager.reset_order_count)

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(5)

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(f"Scheduler started. Will reset order count daily at {RESET_ORDER_TIME}")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")