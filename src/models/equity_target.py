from pydantic import BaseModel, field_validator

class EquityTargetRequest(BaseModel):
    profit_equity: float
    loss_equity: float

    @field_validator("profit_equity", "loss_equity")
    @classmethod
    def validate_positive(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("Equity target must be positive")
        return value