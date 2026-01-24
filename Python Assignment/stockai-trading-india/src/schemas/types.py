from pydantic import BaseModel
from typing import List, Optional

class Stock(BaseModel):
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: Optional[float] = None
    price: float
    volume: int

class Trade(BaseModel):
    stock: Stock
    quantity: int
    price: float
    trade_type: str  # 'buy' or 'sell'
    timestamp: str

class StrategyConfig(BaseModel):
    name: str
    parameters: dict

class Order(BaseModel):
    order_id: str
    trade: Trade
    status: str  # 'pending', 'completed', 'failed'
    timestamp: str

class Portfolio(BaseModel):
    stocks: List[Stock]
    cash_balance: float

class MarketData(BaseModel):
    stock: Stock
    timestamp: str
    price: float
    volume: int