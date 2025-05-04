import os
from dotenv import load_dotenv

load_dotenv()

def get_required_env_var(var_name: str) -> str:
    """Get an environment variable and raise an error if not set."""
    value = os.getenv(var_name)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set in .env file")
    return value

def get_required_int_env_var(var_name: str) -> int:
    """Get an integer environment variable and raise an error if not set or invalid."""
    value = get_required_env_var(var_name)
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Environment variable {var_name} must be an integer, got: {value}")

def get_required_float_env_var(var_name: str) -> float:
    """Get a float environment variable and raise an error if not set or invalid."""
    value = get_required_env_var(var_name)
    try:
        return float(value)
    except ValueError:
        raise ValueError(f"Environment variable {var_name} must be a float, got: {value}")

# Load required environment variables
MT5_LOGIN = get_required_int_env_var("MT5_LOGIN")
MT5_PASSWORD = get_required_env_var("MT5_PASSWORD")
MT5_SERVER = get_required_env_var("MT5_SERVER")
SERVER_IP = get_required_env_var("SERVER_IP")
SERVER_PORT = get_required_int_env_var("SERVER_PORT")
RESET_ORDER_TIME = get_required_env_var("RESET_ORDER_TIME")
MAX_DAILY_ORDERS = get_required_int_env_var("MAX_DAILY_ORDERS")
MUST_RISK_AMOUNT = get_required_float_env_var("MUST_RISK_AMOUNT")
RISK_TO_REWARD = get_required_float_env_var("RISK_TO_REWARD")
COMMENT = get_required_env_var("COMMENT")
OPEN_EXCHANGE_RATES_API_KEY = get_required_env_var("OPEN_EXCHANGE_RATES_API_KEY")
AVAILABLE_SYMBOLS = get_required_env_var("AVAILABLE_SYMBOLS").split(",")

ACCOUNTS = {
    "real": {
        "login": MT5_LOGIN,
        "password": MT5_PASSWORD,
        "server": MT5_SERVER
    }
}