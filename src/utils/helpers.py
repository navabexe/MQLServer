import MetaTrader5 as mt5
from src.utils.logger import logger

def get_pip_value(symbol: str) -> float:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        logger.error(f"Failed to get symbol info for {symbol}")
        return 0.0
    # محاسبه ارزش پیپ بر اساس تعداد ارقام اعشار و نوع دارایی
    digits = symbol_info.digits
    if "JPY" in symbol:
        return 0.01  # برای جفت‌ارزهای JPY (مثل USDJPY)
    elif symbol == "BTCUSD":
        return 1.0  # برای BTCUSD
    elif symbol in ["XAUUSD", "XAGUSD"]:  # برای طلا و نقره
        return 0.01 if symbol == "XAUUSD" else 0.001
    return 10 ** (-digits + 1)  # برای جفت‌ارزهای استاندارد (مثل EURUSD)

def get_conversion_rate(from_currency: str, to_currency: str) -> float:
    try:
        if from_currency == to_currency:
            logger.info(f"Conversion rate for {from_currency} to {to_currency}: 1.0 (same currency)")
            return 1.0
        if to_currency == "USD":
            symbol = f"{from_currency}USD"
            price_info = mt5.symbol_info_tick(symbol)
            if not price_info:
                # امتحان کردن جفت‌ارز معکوس
                symbol = f"USD{from_currency}"
                price_info = mt5.symbol_info_tick(symbol)
                if not price_info:
                    logger.error(f"Failed to get MT5 price for {symbol}")
                    raise ValueError(f"Currency pair {symbol} not available in MT5")
                rate = 1 / ((price_info.bid + price_info.ask) / 2)
                logger.info(f"Conversion rate for {from_currency} to {to_currency} from MT5 (inverse): {rate}")
                return rate
            rate = (price_info.bid + price_info.ask) / 2
            logger.info(f"Conversion rate for {from_currency} to {to_currency} from MT5: {rate}")
            return rate
        if from_currency == "USD":
            symbol = f"USD{to_currency}"
            price_info = mt5.symbol_info_tick(symbol)
            if not price_info:
                logger.error(f"Failed to get MT5 price for {symbol}")
                raise ValueError(f"Currency pair {symbol} not available in MT5")
            rate = 1 / ((price_info.bid + price_info.ask) / 2)
            logger.info(f"Conversion rate for {from_currency} to {to_currency} from MT5: {rate}")
            return rate
        symbol_to_usd = f"{from_currency}USD"
        symbol_from_usd = f"USD{to_currency}"
        price_to_usd = mt5.symbol_info_tick(symbol_to_usd)
        price_from_usd = mt5.symbol_info_tick(symbol_from_usd)
        if not price_to_usd or not price_from_usd:
            # امتحان کردن جفت‌ارزهای معکوس
            if not price_to_usd:
                symbol_to_usd = f"USD{from_currency}"
                price_to_usd = mt5.symbol_info_tick(symbol_to_usd)
                if price_to_usd:
                    price_to_usd = 1 / ((price_to_usd.bid + price_to_usd.ask) / 2)
            if not price_from_usd:
                symbol_from_usd = f"{to_currency}USD"
                price_from_usd = mt5.symbol_info_tick(symbol_from_usd)
                if price_from_usd:
                    price_from_usd = (price_from_usd.bid + price_from_usd.ask) / 2
            if not price_to_usd or not price_from_usd:
                logger.error(f"Failed to get MT5 prices for {symbol_to_usd} or {symbol_from_usd}")
                raise ValueError(f"Currency pairs {symbol_to_usd} or {symbol_from_usd} not available in MT5")
        rate = price_to_usd / price_from_usd
        logger.info(f"Conversion rate for {from_currency} to {to_currency} from MT5: {rate}")
        return rate
    except Exception as e:
        logger.error(f"Error fetching conversion rate for {from_currency} to {to_currency} from MT5: {str(e)}")
        raise ValueError(f"Failed to fetch conversion rate from MT5: {str(e)}")

def calculate_pips(entry_price: float, stop_loss: float, symbol: str) -> float:
    try:
        pip_value = get_pip_value(symbol)
        if pip_value == 0:
            return 0.0
        return abs(entry_price - stop_loss) / pip_value
    except Exception as e:
        logger.error(f"Error calculating pips for {symbol}: {e}")
        return 0.0