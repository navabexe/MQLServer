from pydantic import BaseModel, field_validator
from src.utils.config import AVAILABLE_SYMBOLS
from typing import Literal

class OrderRequest(BaseModel):
    symbol: str
    entry_price: float
    stop_loss: float
    position_type: str
    risk_to_reward: float = 3.0

    @field_validator("symbol")
    @classmethod
    def validate_symbol(cls, value: str) -> str:
        if value not in AVAILABLE_SYMBOLS:
            raise ValueError(f"Symbol {value} is not in available symbols")
        return value

    @field_validator("entry_price", "stop_loss")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Price must be positive")
        return value

    @field_validator("position_type")
    @classmethod
    def validate_position_type(cls, value: str) -> str:
        valid_types = ["buy", "sell", "buy limit", "sell limit", "buy stop", "sell stop"]
        if value.lower() not in valid_types:
            raise ValueError(f"Invalid position type: {value}")
        return value.lower()

    @field_validator("risk_to_reward")
    @classmethod
    def validate_risk_to_reward(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Risk to reward ratio must be positive")
        return value