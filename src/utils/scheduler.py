import schedule
import threading
import time
from src.core.state_manager import get_state_manager
from src.core.equity_closer import EquityCloser
from src.utils.config import RESET_ORDER_TIME
from src.utils.logger import logger

_equity_closer = EquityCloser()


def start_scheduler():
    try:
        state_manager = get_state_manager()
        schedule.every().day.at(RESET_ORDER_TIME).do(state_manager.reset_order_count)
        schedule.every(2).seconds.do(_equity_closer.check_and_close_positions)

        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(1)

        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info(
            f"Scheduler started. Will reset order count daily at {RESET_ORDER_TIME} and check equity every 2 seconds")
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")