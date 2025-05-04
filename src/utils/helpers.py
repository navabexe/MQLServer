import MetaTrader5 as mt5
import requests
from src.utils.config import OPEN_EXCHANGE_RATES_API_KEY
from src.utils.logger import logger

def get_pip_value(symbol: str) -> float:
    """Get pip value for a symbol."""
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Failed to get symbol info for {symbol}")
        return 0.0

    if "JPY" in symbol:
        return 0.01
    elif symbol == "BTCUSD":
        return 1.0
    return 0.0001

def get_conversion_rate(from_currency: str, to_currency: str) -> float:
    """Get the real-time conversion rate between two currencies using Open Exchange Rates API."""
    try:
        if not OPEN_EXCHANGE_RATES_API_KEY:
            logger.error("Open Exchange Rates API key is not set")
            return 1.0

        url = f"https://openexchangerates.org/api/latest.json?app_id={OPEN_EXCHANGE_RATES_API_KEY}"
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch conversion rate for {from_currency} to {to_currency}: {response.status_code}")
            return 1.0

        rates = response.json().get("rates", {})
        if from_currency not in rates or to_currency not in rates:
            logger.error(f"Currency pair {from_currency}/{to_currency} not found in rates")
            return 1.0

        # Convert from_currency to to_currency
        rate = rates[to_currency] / rates[from_currency]
        logger.info(f"Conversion rate for {from_currency} to {to_currency}: {rate}")
        return rate
    except Exception as e:
        logger.error(f"Error fetching conversion rate for {from_currency} to {to_currency}: {str(e)}")
        return 1.0

def calculate_pips(entry_price: float, stop_loss: float, symbol: str) -> float:
    """Calculate the distance between entry price and stop loss in pips."""
    try:
        pip_value = get_pip_value(symbol)
        if pip_value == 0:
            return 0.0
        return abs(entry_price - stop_loss) / pip_value
    except Exception as e:
        logger.error(f"Error calculating pips for {symbol}: {e}")
        return 0.0