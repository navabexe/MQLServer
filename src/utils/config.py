import os
from dotenv import load_dotenv

load_dotenv()

MT5_LOGIN = int(os.getenv("MT5_LOGIN", 329228))
COMMENT = (os.getenv("COMMENT"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")
RESET_ORDER_TIME = os.getenv("RESET_ORDER_TIME")
MAX_DAILY_ORDERS = int(os.getenv("MAX_DAILY_ORDERS", 2))
MUST_RISK_AMOUNT = float(os.getenv("MUST_RISK_AMOUNT", 30))
RISK_TO_REWARD = float(os.getenv("RISK_TO_REWARD", 3))
AVAILABLE_SYMBOLS = os.getenv("AVAILABLE_SYMBOLS", "AUDNZD,AUDCHF,EURCHF,AUDUSD,EURAUD,EURGBP,EURUSD,GBPAUD,GBPCAD,GBPUSD,NZDCAD,NZDUSD,USDCAD,USDCHF,USDJPY,USDSGD,BTCUSD").split(",")

# API Key for Open Exchange Rates
OPEN_EXCHANGE_RATES_API_KEY = os.getenv("OPEN_EXCHANGE_RATES_API_KEY", "")

ACCOUNTS = {
    "real": {
        "login": MT5_LOGIN,
        "password": MT5_PASSWORD,
        "server": MT5_SERVER
    }
}