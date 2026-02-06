"""
Paper Trading System
Simulates trading without real money for strategy testing
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PaperOrder:
    """Paper trading order"""
    order_id: str
    symbol: str
    ticker: str
    transaction_type: str  # BUY or SELL
    quantity: int
    order_type: str  # MARKET, LIMIT, SL, SL-M
    price: Optional[float]
    trigger_price: Optional[float]
    product: str  # 'I' for Intraday, 'D' for Delivery
    status: str  # PENDING, EXECUTED, CANCELLED, REJECTED
    executed_price: Optional[float] = None
    executed_quantity: int = 0
    timestamp: Optional[str] = None
    executed_timestamp: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PaperOrder':
        return cls(**data)


@dataclass
class PaperPosition:
    """Paper trading position"""
    symbol: str
    ticker: str
    quantity: int
    average_price: float
    current_price: float
    product: str
    entry_timestamp: str
    
    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def invested_value(self) -> float:
        return self.quantity * self.average_price
    
    @property
    def pnl(self) -> float:
        return self.current_value - self.invested_value
    
    @property
    def pnl_pct(self) -> float:
        if self.invested_value > 0:
            return (self.pnl / self.invested_value) * 100
        return 0.0
    
    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'ticker': self.ticker,
            'quantity': self.quantity,
            'average_price': self.average_price,
            'current_price': self.current_price,
            'current_value': self.current_value,
            'invested_value': self.invested_value,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'product': self.product,
            'entry_timestamp': self.entry_timestamp
        }


class PaperTradingManager:
    """Manages paper trading orders and positions"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path('data/paper_trading.json')
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.orders: Dict[str, PaperOrder] = {}
        self.positions: Dict[str, PaperPosition] = {}
        self.cash_balance: float = 100000.0  # Starting cash
        self.initial_cash: float = 100000.0
        self.load_state()
    
    def load_state(self):
        """Load paper trading state from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    
                    # Load orders
                    self.orders = {
                        order_id: PaperOrder.from_dict(order_data)
                        for order_id, order_data in data.get('orders', {}).items()
                    }
                    
                    # Load positions
                    self.positions = {
                        symbol: PaperPosition(
                            symbol=pos_data['symbol'],
                            ticker=pos_data['ticker'],
                            quantity=pos_data['quantity'],
                            average_price=pos_data['average_price'],
                            current_price=pos_data.get('current_price', pos_data['average_price']),
                            product=pos_data.get('product', 'D'),
                            entry_timestamp=pos_data.get('entry_timestamp', datetime.now().isoformat())
                        )
                        for symbol, pos_data in data.get('positions', {}).items()
                    }
                    
                    # Load cash balance
                    self.cash_balance = data.get('cash_balance', 100000.0)
                    self.initial_cash = data.get('initial_cash', 100000.0)
                    
                logger.info(f"Loaded paper trading state: {len(self.orders)} orders, {len(self.positions)} positions")
        except Exception as e:
            logger.error(f"Error loading paper trading state: {e}")
            self.orders = {}
            self.positions = {}
            self.cash_balance = 100000.0
            self.initial_cash = 100000.0
    
    def save_state(self):
        """Save paper trading state to storage"""
        try:
            data = {
                'orders': {
                    order_id: order.to_dict()
                    for order_id, order in self.orders.items()
                },
                'positions': {
                    symbol: {
                        'symbol': pos.symbol,
                        'ticker': pos.ticker,
                        'quantity': pos.quantity,
                        'average_price': pos.average_price,
                        'current_price': pos.current_price,
                        'product': pos.product,
                        'entry_timestamp': pos.entry_timestamp
                    }
                    for symbol, pos in self.positions.items()
                },
                'cash_balance': self.cash_balance,
                'initial_cash': self.initial_cash,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Saved paper trading state")
        except Exception as e:
            logger.error(f"Error saving paper trading state: {e}")
    
    def place_order(
        self,
        symbol: str,
        ticker: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'D',
        current_market_price: Optional[float] = None
    ) -> Dict:
        """
        Place a paper trading order
        
        Args:
            symbol: Stock symbol
            ticker: Full ticker (e.g., RELIANCE.NS)
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, SL-M
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            product: 'I' for Intraday, 'D' for Delivery
            current_market_price: Current market price (for execution simulation)
        
        Returns:
            Dict with order result
        """
        order_id = f"PAPER_{symbol}_{transaction_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine execution price based on order type
        if order_type == 'MARKET':
            # Market order executes at current price (with slight slippage)
            if current_market_price:
                if transaction_type == 'BUY':
                    executed_price = current_market_price * 1.001  # 0.1% slippage on buy
                else:  # SELL
                    executed_price = current_market_price * 0.999  # 0.1% slippage on sell
            else:
                executed_price = price if price else 100.0  # Fallback
        elif order_type == 'LIMIT':
            executed_price = price if price else current_market_price
            # Limit order only executes if price is favorable
            if transaction_type == 'BUY' and executed_price > (current_market_price or price):
                return {
                    'status': 'error',
                    'error': 'Limit price above market price for BUY order',
                    'order_id': order_id
                }
            elif transaction_type == 'SELL' and executed_price < (current_market_price or price):
                return {
                    'status': 'error',
                    'error': 'Limit price below market price for SELL order',
                    'order_id': order_id
                }
        else:
            # SL orders - simplified execution
            executed_price = price if price else current_market_price
        
        # Check if order can be executed
        if transaction_type == 'BUY':
            required_cash = executed_price * quantity
            if required_cash > self.cash_balance:
                return {
                    'status': 'error',
                    'error': f'Insufficient cash. Required: ₹{required_cash:.2f}, Available: ₹{self.cash_balance:.2f}',
                    'order_id': order_id
                }
        elif transaction_type == 'SELL':
            # Check if we have the position
            if symbol not in self.positions:
                return {
                    'status': 'error',
                    'error': f'No position found for {symbol}',
                    'order_id': order_id
                }
            if self.positions[symbol].quantity < quantity:
                return {
                    'status': 'error',
                    'error': f'Insufficient quantity. Required: {quantity}, Available: {self.positions[symbol].quantity}',
                    'order_id': order_id
                }
        
        # Create order
        order = PaperOrder(
            order_id=order_id,
            symbol=symbol,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=order_type,
            price=price,
            trigger_price=trigger_price,
            product=product,
            status='EXECUTED',  # Paper trading executes immediately
            executed_price=executed_price,
            executed_quantity=quantity,
            timestamp=datetime.now().isoformat(),
            executed_timestamp=datetime.now().isoformat()
        )
        
        # Execute the order
        if transaction_type == 'BUY':
            cost = executed_price * quantity
            self.cash_balance -= cost
            
            # Update or create position
            if symbol in self.positions:
                pos = self.positions[symbol]
                total_cost = (pos.average_price * pos.quantity) + cost
                total_quantity = pos.quantity + quantity
                pos.average_price = total_cost / total_quantity
                pos.quantity = total_quantity
            else:
                self.positions[symbol] = PaperPosition(
                    symbol=symbol,
                    ticker=ticker,
                    quantity=quantity,
                    average_price=executed_price,
                    current_price=executed_price,
                    product=product,
                    entry_timestamp=datetime.now().isoformat()
                )
        else:  # SELL
            proceeds = executed_price * quantity
            self.cash_balance += proceeds
            
            # Update position
            pos = self.positions[symbol]
            pos.quantity -= quantity
            
            if pos.quantity <= 0:
                del self.positions[symbol]
        
        # Save order
        self.orders[order_id] = order
        self.save_state()
        
        logger.info(f"Paper order executed: {order_id} - {symbol} {transaction_type} {quantity} @ {executed_price}")
        
        return {
            'status': 'success',
            'message': f'✅ PAPER ORDER EXECUTED: {symbol} {transaction_type} {quantity} @ ₹{executed_price:.2f}',
            'order_id': order_id,
            'order': order.to_dict()
        }
    
    def get_positions(self) -> List[Dict]:
        """Get all paper trading positions"""
        return [pos.to_dict() for pos in self.positions.values()]
    
    def get_orders(self, status: Optional[str] = None) -> List[Dict]:
        """Get all paper trading orders"""
        orders = list(self.orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        return [o.to_dict() for o in orders]
    
    def get_portfolio_summary(self) -> Dict:
        """Get paper trading portfolio summary"""
        total_position_value = sum(pos.current_value for pos in self.positions.values())
        total_invested = sum(pos.invested_value for pos in self.positions.values())
        total_pnl = sum(pos.pnl for pos in self.positions.values())
        total_value = self.cash_balance + total_position_value
        
        return {
            'cash_balance': self.cash_balance,
            'position_value': total_position_value,
            'total_value': total_value,
            'invested_value': total_invested,
            'total_pnl': total_pnl,
            'total_pnl_pct': ((total_value - self.initial_cash) / self.initial_cash * 100) if self.initial_cash > 0 else 0.0,
            'num_positions': len(self.positions),
            'initial_cash': self.initial_cash
        }
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None
    ) -> Dict:
        """
        Phase 2.2: Modify a pending paper trading order
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            order_type: New order type (optional)
        
        Returns:
            Dict with modification result
        """
        if order_id not in self.orders:
            return {
                'status': 'error',
                'error': f'Order {order_id} not found'
            }
        
        order = self.orders[order_id]
        
        # Can only modify pending orders
        if order.status != 'PENDING':
            return {
                'status': 'error',
                'error': f'Cannot modify {order.status} order. Only PENDING orders can be modified.'
            }
        
        # Update order fields
        if quantity is not None:
            order.quantity = quantity
        if price is not None:
            order.price = price
        if order_type is not None:
            order.order_type = order_type
        
        self.save_state()
        
        logger.info(f"Paper order modified: {order_id}")
        
        return {
            'status': 'success',
            'message': f'Order {order_id} modified successfully',
            'order': order.to_dict()
        }
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Phase 2.2: Cancel a pending paper trading order
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            Dict with cancellation result
        """
        if order_id not in self.orders:
            return {
                'status': 'error',
                'error': f'Order {order_id} not found'
            }
        
        order = self.orders[order_id]
        
        # Can only cancel pending orders
        if order.status != 'PENDING':
            return {
                'status': 'error',
                'error': f'Cannot cancel {order.status} order. Only PENDING orders can be cancelled.'
            }
        
        # Fix Bug 3: Refund cash for pending BUY orders
        # For pending orders, executed_price is None, so use order.price
        # For executed orders, use executed_price
        if order.transaction_type == 'BUY':
            if order.executed_price:
                # Order was executed - refund executed amount
                refund = order.executed_price * order.quantity
            elif order.price:
                # Pending order - refund reserved amount based on order price
                refund = order.price * order.quantity
            else:
                # Fallback: estimate refund based on current market price
                # This shouldn't happen, but handle gracefully
                from src.web.market_data import MarketDataClient
                try:
                    # Try to get current price for the symbol
                    # Note: This is a fallback, ideally order.price should always be set
                    current_price = 100.0  # Default fallback
                    refund = current_price * order.quantity
                    logger.warning(f"Order {order_id} has no price, using fallback for refund")
                except:
                    refund = 0
            
            if refund > 0:
                self.cash_balance += refund
                logger.info(f"Refunded ₹{refund:.2f} for cancelled BUY order {order_id}")
        
        # Update order status
        order.status = 'CANCELLED'
        self.save_state()
        
        logger.info(f"Paper order cancelled: {order_id}")
        
        return {
            'status': 'success',
            'message': f'Order {order_id} cancelled successfully',
            'order': order.to_dict()
        }
    
    def update_position_prices(self, price_updates: Dict[str, float]):
        """Update position prices with current market prices"""
        for symbol, price in price_updates.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
        self.save_state()
    
    def reset_portfolio(self, initial_cash: float = 100000.0):
        """Reset paper trading portfolio"""
        self.orders = {}
        self.positions = {}
        self.cash_balance = initial_cash
        self.initial_cash = initial_cash
        self.save_state()
        logger.info(f"Paper trading portfolio reset with ₹{initial_cash}")


# Global instance
_paper_trading_manager = None


def get_paper_trading_manager() -> PaperTradingManager:
    """Get global paper trading manager instance"""
    global _paper_trading_manager
    if _paper_trading_manager is None:
        _paper_trading_manager = PaperTradingManager()
    return _paper_trading_manager
