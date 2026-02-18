"""
Request/Response Validation
Pydantic-based validation for API requests and responses
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)

# Request Models
class SignalRequest(BaseModel):
    """Request model for signal generation"""
    ticker: str = Field(..., description="Stock ticker symbol")
    use_ensemble: bool = Field(True, description="Use ensemble of models")
    use_multi_timeframe: bool = Field(True, description="Analyze multiple timeframes")
    instrument_key: Optional[str] = Field(None, description="Upstox instrument key")
    
    @validator('ticker')
    def validate_ticker(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Ticker cannot be empty")
        return v.strip().upper()

class TradeRegisterRequest(BaseModel):
    """Request model for trade registration"""
    ticker: str = Field(..., description="Stock ticker")
    entry_price: float = Field(..., gt=0, description="Entry price")
    stop_loss: float = Field(..., gt=0, description="Stop loss price")
    target_1: float = Field(..., gt=0, description="Target 1 price")
    target_2: float = Field(..., gt=0, description="Target 2 price")
    type: str = Field(..., description="Trade type: LONG or SHORT")
    
    @validator('type')
    def validate_type(cls, v):
        if v.upper() not in ['LONG', 'SHORT']:
            raise ValueError("Type must be LONG or SHORT")
        return v.upper()
    
    @validator('stop_loss', 'target_1', 'target_2')
    def validate_prices(cls, v, values):
        entry_price = values.get('entry_price')
        if entry_price and v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

class OrderRequest(BaseModel):
    """Request model for order placement"""
    ticker: str = Field(..., description="Stock ticker")
    transaction_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: str = Field("MARKET", description="Order type: MARKET, LIMIT, SL, SL-M")
    price: Optional[float] = Field(None, description="Price for LIMIT orders")
    trigger_price: Optional[float] = Field(None, description="Trigger price for SL orders")
    product: str = Field("D", description="Product type: D (Delivery), I (Intraday)")
    
    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        if v.upper() not in ['BUY', 'SELL']:
            raise ValueError("Transaction type must be BUY or SELL")
        return v.upper()
    
    @validator('order_type')
    def validate_order_type(cls, v):
        valid_types = ['MARKET', 'LIMIT', 'SL', 'SL-M']
        if v.upper() not in valid_types:
            raise ValueError(f"Order type must be one of: {', '.join(valid_types)}")
        return v.upper()

# Response Models
class HealthResponse(BaseModel):
    """Response model for health check"""
    ok: bool
    status: str
    timestamp: str
    version: str
    services: Dict[str, Any]

class SignalResponse(BaseModel):
    """Response model for signal generation"""
    ticker: str
    signal: str
    probability: float
    confidence: float
    current_price: float
    entry_price: float
    stop_loss: float
    target_1: float
    target_2: float
    timestamp: str

def validate_request(model_class):
    """Decorator to validate request data"""
    def decorator(f):
        from functools import wraps
        from flask import request, jsonify
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                data = request.get_json() or {}
                validated_data = model_class(**data)
                # Replace request.json with validated data
                request.validated_data = validated_data
                return f(*args, **kwargs)
            except Exception as e:
                return jsonify({
                    'status': 'error',
                    'message': 'Validation error',
                    'errors': str(e)
                }), 400
        
        return decorated_function
    return decorator
