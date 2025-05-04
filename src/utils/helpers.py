from src.utils.logger import logger
from typing import Optional

def calculate_pips(entry_price: float, stop_loss_price: float, symbol: str) -> Optional[float]:
    """
    Calculate the pip difference between entry price and stop loss price.

    Args:
        entry_price: Entry price of the trade
        stop_loss_price: Stop loss price
        symbol: Trading symbol (e.g., EURUSD, BTCUSD)

    Returns:
        Number of pips or None if invalid
    """
    try:
        if symbol == "BTCUSD":
            pip_value = 0.01
        else:
            pip_value = 0.00001 if not symbol.endswith("JPY") else 0.001
        pips = abs(entry_price - stop_loss_price) / pip_value
        return round(pips, 2)
    except Exception as e:
        logger.error(f"Error calculating pips for {symbol}: {e}")
        return None

def get_pip_value(symbol: str) -> float:
    """
    Get the pip value for a given symbol.

    Args:
        symbol: Trading symbol

    Returns:
        Pip value for the symbol
    """
    if symbol == "BTCUSD":
        return 0.01
    elif symbol.endswith("JPY"):
        return 0.001
    return 0.0001