"""
Phase 3.2: Advanced Order Types
- Smart Order Routing (SOR)
- Conditional Orders (Bracket, Trailing Stop, OCO, Time-based)
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class OrderExecutionStrategy(Enum):
    """Order execution strategies"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    TWAP = "TWAP"  # Time-Weighted Average Price
    VWAP = "VWAP"  # Volume-Weighted Average Price
    ICEBERG = "ICEBERG"  # Hidden order size
    SLICE = "SLICE"  # Order slicing


class ConditionalOrderType(Enum):
    """Types of conditional orders"""
    BRACKET = "BRACKET"  # Entry + Stop Loss + Target
    TRAILING_STOP = "TRAILING_STOP"
    OCO = "OCO"  # One-Cancels-Other
    TIME_BASED = "TIME_BASED"


@dataclass
class OrderSlice:
    """Represents a slice of a larger order"""
    slice_id: str
    quantity: int
    price: Optional[float] = None
    status: str = "PENDING"  # PENDING, EXECUTED, CANCELLED
    executed_quantity: int = 0
    executed_price: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConditionalOrder:
    """Represents a conditional order"""
    order_id: str
    ticker: str
    transaction_type: str  # BUY or SELL
    quantity: int
    order_type: ConditionalOrderType
    status: str = "PENDING"  # PENDING, ACTIVE, TRIGGERED, CANCELLED, COMPLETED
    
    # Bracket order fields
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    
    # Trailing stop fields
    trailing_stop_percent: Optional[float] = None
    trailing_stop_amount: Optional[float] = None
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    
    # OCO fields
    oco_orders: List[str] = field(default_factory=list)  # List of related order IDs
    
    # Time-based fields
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Execution tracking
    executed_quantity: int = 0
    executed_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class SmartOrderRouter:
    """Smart Order Routing - Best execution algorithms"""
    
    def __init__(self, upstox_client=None):
        self.upstox_client = upstox_client
        self.execution_history: List[Dict] = []
    
    def calculate_best_execution_price(
        self,
        ticker: str,
        quantity: int,
        transaction_type: str,
        current_price: float,
        bid_ask_spread: Optional[float] = None
    ) -> float:
        """
        Calculate best execution price considering market impact
        """
        if transaction_type == "BUY":
            # For buy orders, add a small premium to ensure execution
            impact = (quantity / 1000) * 0.001  # Market impact estimate
            best_price = current_price * (1 + impact)
            if bid_ask_spread:
                best_price = min(best_price, current_price + bid_ask_spread / 2)
        else:  # SELL
            # For sell orders, subtract a small discount
            impact = (quantity / 1000) * 0.001
            best_price = current_price * (1 - impact)
            if bid_ask_spread:
                best_price = max(best_price, current_price - bid_ask_spread / 2)
        
        return round(best_price, 2)
    
    def execute_twap_order(
        self,
        ticker: str,
        quantity: int,
        transaction_type: str,
        duration_minutes: int = 30,
        slices: int = 10
    ) -> Dict[str, Any]:
        """
        Execute order using TWAP (Time-Weighted Average Price) strategy
        Divides order into equal slices over time period
        """
        slice_quantity = quantity // slices
        remaining_quantity = quantity % slices
        
        slice_interval = duration_minutes * 60 / slices  # seconds
        
        order_slices: List[OrderSlice] = []
        executed_slices: List[OrderSlice] = []
        
        for i in range(slices):
            slice_qty = slice_quantity + (remaining_quantity if i == slices - 1 else 0)
            slice_id = f"TWAP_{ticker}_{int(time.time())}_{i}"
            order_slices.append(OrderSlice(
                slice_id=slice_id,
                quantity=slice_qty,
                status="PENDING"
            ))
        
        # Execute slices over time
        start_time = time.time()
        for i, slice_order in enumerate(order_slices):
            if i > 0:
                time.sleep(slice_interval)
            
            # Execute slice
            try:
                if self.upstox_client:
                    result = self.upstox_client.place_order(
                        ticker=ticker,
                        transaction_type=transaction_type,
                        quantity=slice_order.quantity,
                        order_type='MARKET'
                    )
                    if 'error' not in result:
                        slice_order.status = "EXECUTED"
                        slice_order.executed_quantity = slice_order.quantity
                        executed_slices.append(slice_order)
                    else:
                        slice_order.status = "CANCELLED"
                else:
                    # Simulate execution
                    slice_order.status = "EXECUTED"
                    slice_order.executed_quantity = slice_order.quantity
                    executed_slices.append(slice_order)
            except Exception as e:
                logger.error(f"TWAP slice execution failed: {e}")
                slice_order.status = "CANCELLED"
        
        total_executed = sum(s.executed_quantity for s in executed_slices)
        avg_price = sum(s.executed_price or 0 for s in executed_slices) / len(executed_slices) if executed_slices else 0
        
        return {
            'strategy': 'TWAP',
            'total_quantity': quantity,
            'executed_quantity': total_executed,
            'slices': len(order_slices),
            'executed_slices': len(executed_slices),
            'average_price': avg_price,
            'duration_minutes': duration_minutes,
            'status': 'COMPLETED' if total_executed == quantity else 'PARTIAL'
        }
    
    def execute_vwap_order(
        self,
        ticker: str,
        quantity: int,
        transaction_type: str,
        duration_minutes: int = 30,
        volume_percentage: float = 0.1  # Target 10% of volume
    ) -> Dict[str, Any]:
        """
        Execute order using VWAP (Volume-Weighted Average Price) strategy
        Executes based on volume profile
        """
        # This would ideally use real-time volume data
        # For now, simulate VWAP execution
        slices = max(5, int(quantity / 100))  # Adaptive slicing based on quantity
        
        return self.execute_twap_order(
            ticker=ticker,
            quantity=quantity,
            transaction_type=transaction_type,
            duration_minutes=duration_minutes,
            slices=slices
        )
    
    def execute_iceberg_order(
        self,
        ticker: str,
        total_quantity: int,
        transaction_type: str,
        visible_quantity: int,  # Quantity shown in order book
        refill_threshold: int = 50  # Refill when executed quantity reaches this %
    ) -> Dict[str, Any]:
        """
        Execute iceberg order - shows only part of order in book
        """
        executed_quantity = 0
        remaining_quantity = total_quantity
        slices: List[OrderSlice] = []
        
        while remaining_quantity > 0:
            current_visible = min(visible_quantity, remaining_quantity)
            slice_id = f"ICEBERG_{ticker}_{int(time.time())}_{len(slices)}"
            
            try:
                if self.upstox_client:
                    result = self.upstox_client.place_order(
                        ticker=ticker,
                        transaction_type=transaction_type,
                        quantity=current_visible,
                        order_type='LIMIT'
                    )
                    if 'error' not in result:
                        executed_quantity += current_visible
                        remaining_quantity -= current_visible
                        slices.append(OrderSlice(
                            slice_id=slice_id,
                            quantity=current_visible,
                            status="EXECUTED",
                            executed_quantity=current_visible
                        ))
                    else:
                        break
                else:
                    # Simulate
                    executed_quantity += current_visible
                    remaining_quantity -= current_visible
                    slices.append(OrderSlice(
                        slice_id=slice_id,
                        quantity=current_visible,
                        status="EXECUTED",
                        executed_quantity=current_visible
                    ))
            except Exception as e:
                logger.error(f"Iceberg order slice failed: {e}")
                break
            
            # Wait before next slice
            time.sleep(2)
        
        return {
            'strategy': 'ICEBERG',
            'total_quantity': total_quantity,
            'executed_quantity': executed_quantity,
            'visible_quantity': visible_quantity,
            'slices': len(slices),
            'status': 'COMPLETED' if executed_quantity == total_quantity else 'PARTIAL'
        }


class ConditionalOrderManager:
    """Manages conditional orders (Bracket, Trailing Stop, OCO, Time-based)"""
    
    def __init__(self, upstox_client=None):
        self.upstox_client = upstox_client
        self.conditional_orders: Dict[str, ConditionalOrder] = {}
        self.active_monitors: Dict[str, threading.Thread] = {}
        self.running = True
        self._lock = threading.Lock()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_orders, daemon=True)
        self.monitor_thread.start()
    
    def create_bracket_order(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        entry_price: float,
        stop_loss: float,
        target_1: float,
        target_2: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create a bracket order: Entry + Stop Loss + Target(s)
        """
        order_id = f"BRACKET_{ticker}_{int(time.time())}"
        
        conditional_order = ConditionalOrder(
            order_id=order_id,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=ConditionalOrderType.BRACKET,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            status="PENDING"
        )
        
        with self._lock:
            self.conditional_orders[order_id] = conditional_order
        
        # Place entry order
        try:
            if self.upstox_client:
                result = self.upstox_client.place_order(
                    ticker=ticker,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    order_type='LIMIT',
                    price=entry_price
                )
                if 'error' not in result:
                    conditional_order.status = "ACTIVE"
                    return {
                        'status': 'success',
                        'order_id': order_id,
                        'message': 'Bracket order created successfully',
                        'entry_order': result,
                        'stop_loss': stop_loss,
                        'target_1': target_1,
                        'target_2': target_2
                    }
                else:
                    conditional_order.status = "CANCELLED"
                    return {'status': 'error', 'error': result.get('error', 'Failed to place entry order')}
            else:
                # Simulate
                conditional_order.status = "ACTIVE"
                return {
                    'status': 'success',
                    'order_id': order_id,
                    'message': 'Bracket order created (simulated)',
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target_1': target_1,
                    'target_2': target_2
                }
        except Exception as e:
            logger.error(f"Bracket order creation failed: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def create_trailing_stop_order(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        trailing_stop_percent: Optional[float] = None,
        trailing_stop_amount: Optional[float] = None,
        current_price: float = None
    ) -> Dict[str, Any]:
        """
        Create a trailing stop order
        """
        if not trailing_stop_percent and not trailing_stop_amount:
            return {'status': 'error', 'error': 'Either trailing_stop_percent or trailing_stop_amount required'}
        
        order_id = f"TRAILING_{ticker}_{int(time.time())}"
        
        conditional_order = ConditionalOrder(
            order_id=order_id,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=ConditionalOrderType.TRAILING_STOP,
            trailing_stop_percent=trailing_stop_percent,
            trailing_stop_amount=trailing_stop_amount,
            highest_price=current_price if transaction_type == "SELL" else None,
            lowest_price=current_price if transaction_type == "BUY" else None,
            status="ACTIVE"
        )
        
        with self._lock:
            self.conditional_orders[order_id] = conditional_order
        
        return {
            'status': 'success',
            'order_id': order_id,
            'message': 'Trailing stop order created',
            'trailing_stop_percent': trailing_stop_percent,
            'trailing_stop_amount': trailing_stop_amount
        }
    
    def create_oco_order(
        self,
        ticker: str,
        orders: List[Dict[str, Any]]  # List of order definitions
    ) -> Dict[str, Any]:
        """
        Create OCO (One-Cancels-Other) order
        """
        if len(orders) < 2:
            return {'status': 'error', 'error': 'OCO requires at least 2 orders'}
        
        order_ids = []
        conditional_orders = []
        
        for order_def in orders:
            order_id = f"OCO_{ticker}_{int(time.time())}_{len(order_ids)}"
            order_ids.append(order_id)
            
            conditional_order = ConditionalOrder(
                order_id=order_id,
                ticker=ticker,
                transaction_type=order_def.get('transaction_type', 'BUY'),
                quantity=order_def.get('quantity', 0),
                order_type=ConditionalOrderType.OCO,
                oco_orders=order_ids.copy(),
                status="PENDING"
            )
            
            conditional_orders.append(conditional_order)
        
        # Update all orders with OCO relationships
        for co in conditional_orders:
            co.oco_orders = order_ids
        
        with self._lock:
            for co in conditional_orders:
                self.conditional_orders[co.order_id] = co
        
        return {
            'status': 'success',
            'order_ids': order_ids,
            'message': f'OCO order created with {len(orders)} linked orders'
        }
    
    def create_time_based_order(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        order_type: str = 'MARKET',
        price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create time-based order (executes within time window)
        """
        order_id = f"TIME_{ticker}_{int(time.time())}"
        
        conditional_order = ConditionalOrder(
            order_id=order_id,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            order_type=ConditionalOrderType.TIME_BASED,
            start_time=start_time or datetime.now(),
            end_time=end_time,
            status="PENDING"
        )
        
        with self._lock:
            self.conditional_orders[order_id] = conditional_order
        
        return {
            'status': 'success',
            'order_id': order_id,
            'message': 'Time-based order created',
            'start_time': start_time.isoformat() if start_time else None,
            'end_time': end_time.isoformat() if end_time else None
        }
    
    def _monitor_orders(self):
        """Background thread to monitor conditional orders"""
        while self.running:
            try:
                current_time = datetime.now()
                orders_to_check = []
                
                with self._lock:
                    orders_to_check = list(self.conditional_orders.values())
                
                for order in orders_to_check:
                    if order.status not in ["ACTIVE", "PENDING"]:
                        continue
                    
                    try:
                        # Check bracket orders
                        if order.order_type == ConditionalOrderType.BRACKET:
                            self._check_bracket_order(order)
                        
                        # Check trailing stop orders
                        elif order.order_type == ConditionalOrderType.TRAILING_STOP:
                            self._check_trailing_stop(order)
                        
                        # Check time-based orders
                        elif order.order_type == ConditionalOrderType.TIME_BASED:
                            self._check_time_based_order(order, current_time)
                    
                    except Exception as e:
                        logger.error(f"Error monitoring order {order.order_id}: {e}")
                
                time.sleep(5)  # Check every 5 seconds
            
            except Exception as e:
                logger.error(f"Error in order monitor thread: {e}")
                time.sleep(10)
    
    def _check_bracket_order(self, order: ConditionalOrder):
        """Check if bracket order targets/stop-loss should trigger"""
        # This would ideally check current market price
        # For now, simulate based on order status
        if order.status == "ACTIVE":
            # In real implementation, check current price vs stop_loss/target_1/target_2
            pass
    
    def _check_trailing_stop(self, order: ConditionalOrder):
        """Update trailing stop based on price movement"""
        # This would ideally get current market price
        # For now, simulate
        if order.status == "ACTIVE":
            # In real implementation:
            # 1. Get current price
            # 2. Update highest_price/lowest_price
            # 3. Calculate new stop price
            # 4. Place/modify stop order if needed
            pass
    
    def _check_time_based_order(self, order: ConditionalOrder, current_time: datetime):
        """Check if time-based order should execute"""
        if order.status == "PENDING":
            if order.start_time and current_time >= order.start_time:
                if order.end_time is None or current_time <= order.end_time:
                    # Execute order
                    try:
                        if self.upstox_client:
                            result = self.upstox_client.place_order(
                                ticker=order.ticker,
                                transaction_type=order.transaction_type,
                                quantity=order.quantity,
                                order_type='MARKET'
                            )
                            if 'error' not in result:
                                order.status = "COMPLETED"
                        else:
                            order.status = "COMPLETED"
                    except Exception as e:
                        logger.error(f"Time-based order execution failed: {e}")
            
            elif order.end_time and current_time > order.end_time:
                order.status = "CANCELLED"
    
    def cancel_conditional_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel a conditional order"""
        with self._lock:
            if order_id in self.conditional_orders:
                order = self.conditional_orders[order_id]
                order.status = "CANCELLED"
                
                # Cancel OCO linked orders
                if order.order_type == ConditionalOrderType.OCO:
                    for linked_id in order.oco_orders:
                        if linked_id != order_id and linked_id in self.conditional_orders:
                            self.conditional_orders[linked_id].status = "CANCELLED"
                
                return {'status': 'success', 'message': f'Order {order_id} cancelled'}
            else:
                return {'status': 'error', 'error': 'Order not found'}
    
    def get_conditional_orders(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conditional orders"""
        with self._lock:
            orders = list(self.conditional_orders.values())
            if status:
                orders = [o for o in orders if o.status == status]
            
            return [self._order_to_dict(o) for o in orders]
    
    def _order_to_dict(self, order: ConditionalOrder) -> Dict[str, Any]:
        """Convert ConditionalOrder to dictionary"""
        return {
            'order_id': order.order_id,
            'ticker': order.ticker,
            'transaction_type': order.transaction_type,
            'quantity': order.quantity,
            'order_type': order.order_type.value,
            'status': order.status,
            'entry_price': order.entry_price,
            'stop_loss': order.stop_loss,
            'target_1': order.target_1,
            'target_2': order.target_2,
            'trailing_stop_percent': order.trailing_stop_percent,
            'trailing_stop_amount': order.trailing_stop_amount,
            'executed_quantity': order.executed_quantity,
            'executed_price': order.executed_price,
            'created_at': order.created_at.isoformat(),
            'updated_at': order.updated_at.isoformat()
        }
    
    def stop(self):
        """Stop the monitoring thread"""
        self.running = False


# Singleton instances
_smart_order_router: Optional[SmartOrderRouter] = None
_conditional_order_manager: Optional[ConditionalOrderManager] = None


def get_smart_order_router(upstox_client=None) -> SmartOrderRouter:
    """Get singleton SmartOrderRouter instance"""
    global _smart_order_router
    if _smart_order_router is None:
        _smart_order_router = SmartOrderRouter(upstox_client=upstox_client)
    return _smart_order_router


def get_conditional_order_manager(upstox_client=None) -> ConditionalOrderManager:
    """Get singleton ConditionalOrderManager instance"""
    global _conditional_order_manager
    if _conditional_order_manager is None:
        _conditional_order_manager = ConditionalOrderManager(upstox_client=upstox_client)
    return _conditional_order_manager
