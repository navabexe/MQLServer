from pydantic import BaseModel

class MT5Status(BaseModel):
    connected: bool
    login: int
    server: str
    company: str
    balance: float
    equity: float
    margin: float