from pydantic import BaseModel

class PriceRequest(BaseModel):
    symbol: str