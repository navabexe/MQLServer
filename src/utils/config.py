import os
from dotenv import load_dotenv

load_dotenv()

SERVER_IP = os.getenv("SERVER_IP", "localhost")
SERVER_PORT = int(os.getenv("SERVER_PORT", 12341))

ACCOUNTS = {
    "real": {
        "login": int(os.getenv("MT5_LOGIN")),
        "password": os.getenv("MT5_PASSWORD"),
        "server": os.getenv("MT5_SERVER")
    }
}

RESET_ORDER_TIME = os.getenv("RESET_ORDER_TIME", "23:35")
MAX_DAILY_ORDERS = int(os.getenv("MAX_DAILY_ORDERS", 2))
MUST_RISK_AMOUNT = float(os.getenv("MUST_RISK_AMOUNT", 30))
RISK_TO_REWARD = float(os.getenv("RISK_TO_REWARD", 3))
AVAILABLE_SYMBOLS = os.getenv("AVAILABLE_SYMBOLS", "").split(",")