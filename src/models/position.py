from pydantic import BaseModel

class Position(BaseModel):
    ticket: int
    symbol: str
    type: str
    entry_price: float
    stop_loss: float
    take_profit: float
    status: str  # "open" or "pending"
    pips: float