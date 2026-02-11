"""
Trade Executor Service
Handles order placement, tracking, and position lifecycle management
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime
import time

from src.web.upstox_api import UpstoxAPI
from src.web.trading_mode import TradingMode, get_trading_mode

logger = logging.getLogger(__name__)


class TradeExecutor:
    """
    Executes trades via Upstox API with retry logic and position tracking.
    """
    
    def __init__(self, upstox_client: UpstoxAPI, on_pnl_callback: Optional[Callable[[float], None]] = None):
        self.upstox_client = upstox_client
        self.trading_mode = get_trading_mode()
        self.execution_history: List[Dict] = []
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        self.on_pnl_callback: Optional[Callable[[float], None]] = on_pnl_callback
    
    def execute_buy_order(
        self,
        signal: Dict,
        quantity: Optional[int] = None,
        order_type: str = 'MARKET',
        product: str = 'I'  # 'I' for Intraday, 'D' for Delivery
    ) -> Dict:
        """
        Execute BUY order based on signal.
        
        Args:
            signal: Signal dictionary with ticker, entry_level, stop_loss, etc.
            quantity: Order quantity (if None, calculated from risk)
            order_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
            product: 'I' for Intraday, 'D' for Delivery
        
        Returns:
            Order execution result dictionary
        """
        ticker = signal.get('ticker', '')
        entry_level = signal.get('entry_level', signal.get('current_price', 0))
        stop_loss = signal.get('stop_loss', 0)
        
        if not ticker:
            return {
                'success': False,
                'error': 'Missing ticker in signal',
                'signal': signal
            }
        
        # Calculate quantity if not provided
        if quantity is None:
            # Use default quantity based on risk (simplified)
            quantity = self._calculate_quantity(signal)
        
        if quantity <= 0:
            return {
                'success': False,
                'error': f'Invalid quantity: {quantity}',
                'signal': signal
            }
        
        # Check trading mode
        if self.trading_mode.is_paper_mode():
            logger.info(f"[PAPER TRADE] BUY {quantity} {ticker} @ {entry_level}")
            return self._simulate_order(
                ticker=ticker,
                transaction_type='BUY',
                quantity=quantity,
                price=entry_level,
                order_type=order_type,
                product=product
            )
        
        # Execute real order
        return self._execute_order_with_retry(
            ticker=ticker,
            transaction_type='BUY',
            quantity=quantity,
            order_type=order_type,
            price=entry_level if order_type == 'LIMIT' else None,
            trigger_price=stop_loss if order_type in ['SL', 'SL-M'] else None,
            product=product,
            signal=signal
        )
    
    def execute_sell_order(
        self,
        position: Dict,
        quantity: Optional[int] = None,
        order_type: str = 'MARKET',
        reason: str = 'MANUAL'
    ) -> Dict:
        """
        Execute SELL order to exit position.
        
        Args:
            position: Position dictionary with ticker, quantity, etc.
            quantity: Quantity to sell (if None, sells entire position)
            order_type: 'MARKET', 'LIMIT', 'SL', 'SL-M'
            reason: Reason for exit ('STOP_LOSS', 'TARGET', 'MANUAL', etc.)
        
        Returns:
            Order execution result dictionary
        """
        ticker = position.get('ticker') or position.get('symbol', '') or position.get('tradingsymbol', '')
        position_qty = position.get('quantity', 0)
        current_price = position.get('current_price', position.get('ltp', 0))
        
        if not ticker:
            return {
                'success': False,
                'error': 'Missing ticker in position',
                'position': position
            }
        
        if quantity is None:
            quantity = position_qty
        
        if quantity <= 0 or quantity > position_qty:
            return {
                'success': False,
                'error': f'Invalid quantity: {quantity} (position: {position_qty})',
                'position': position
            }
        
        # Check trading mode
        if self.trading_mode.is_paper_mode():
            logger.info(f"[PAPER TRADE] SELL {quantity} {ticker} @ {current_price} ({reason})")
            result = self._simulate_order(
                ticker=ticker,
                transaction_type='SELL',
                quantity=quantity,
                price=current_price,
                order_type=order_type,
                product=position.get('product', 'I')
            )
        else:
            result = self._execute_order_with_retry(
                ticker=ticker,
                transaction_type='SELL',
                quantity=quantity,
                order_type=order_type,
                price=current_price if order_type == 'LIMIT' else None,
                product=position.get('product', 'I'),
                signal={'reason': reason}
            )
        if result.get('success'):
            sell_price = float(current_price or 0)
            if sell_price > 0:
                try:
                    from src.web.ai_models.performance_tracker import get_performance_tracker
                    get_performance_tracker().resolve_pending(ticker, sell_price)
                except Exception as e:
                    logger.debug(f"resolve_pending failed: {e}")
            if self.on_pnl_callback:
                avg_buy = float(position.get('average_price') or position.get('entry_price') or 0)
                if avg_buy > 0 and sell_price > 0:
                    realized_pnl = (sell_price - avg_buy) * quantity
                    try:
                        self.on_pnl_callback(realized_pnl, ticker)
                    except TypeError:
                        try:
                            self.on_pnl_callback(realized_pnl)
                        except Exception as e:
                            logger.warning(f"on_pnl_callback failed: {e}")
                    except Exception as e:
                        logger.warning(f"on_pnl_callback failed: {e}")
        return result
    
    def update_stop_loss(
        self,
        order_id: str,
        new_stop: float
    ) -> Dict:
        """
        Update stop-loss for an existing order/position.
        
        Args:
            order_id: Order ID to modify
            new_stop: New stop-loss price
        
        Returns:
            Modification result dictionary
        """
        if self.trading_mode.is_paper_mode():
            logger.info(f"[PAPER TRADE] Update stop-loss for order {order_id} to {new_stop}")
            return {
                'success': True,
                'order_id': order_id,
                'new_stop_loss': new_stop,
                'paper_trade': True
            }
        
        try:
            result = self.upstox_client.modify_order(
                order_id=order_id,
                price=new_stop,
                order_type='SL'
            )
            
            if 'error' not in result:
                logger.info(f"Updated stop-loss for order {order_id} to {new_stop}")
                return {
                    'success': True,
                    'order_id': order_id,
                    'new_stop_loss': new_stop,
                    'result': result
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error'),
                    'order_id': order_id
                }
        except Exception as e:
            logger.error(f"Error updating stop-loss: {e}")
            return {
                'success': False,
                'error': str(e),
                'order_id': order_id
            }
    
    def check_and_exit_positions(
        self,
        positions: List[Dict],
        signals: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Check exit conditions for positions and execute exits.
        
        Args:
            positions: List of current positions
            signals: Optional dictionary of ticker -> signal for stop-loss/target updates
        
        Returns:
            List of exit execution results
        """
        exit_results = []
        
        for position in positions:
            ticker = position.get('ticker') or position.get('symbol', '') or position.get('tradingsymbol', '')
            current_price = position.get('current_price') or position.get('ltp', 0)
            entry_price = position.get('entry_price', 0)
            stop_loss = position.get('stop_loss', 0)
            target_1 = position.get('target_1', 0)
            target_2 = position.get('target_2', 0)
            
            if current_price <= 0 or entry_price <= 0:
                continue
            
            # Check stop-loss
            if stop_loss > 0:
                if current_price <= stop_loss:
                    logger.info(f"Stop-loss triggered for {ticker} @ {current_price}")
                    result = self.execute_sell_order(
                        position=position,
                        reason='STOP_LOSS'
                    )
                    exit_results.append(result)
                    continue
            
            # Check targets
            if target_1 > 0 and current_price >= target_1:
                logger.info(f"Target 1 hit for {ticker} @ {current_price}")
                # Exit 50% at target 1
                result = self.execute_sell_order(
                    position=position,
                    quantity=position.get('quantity', 0) // 2,
                    reason='TARGET_1'
                )
                exit_results.append(result)
            
            if target_2 > 0 and current_price >= target_2:
                logger.info(f"Target 2 hit for {ticker} @ {current_price}")
                # Exit remaining at target 2
                result = self.execute_sell_order(
                    position=position,
                    reason='TARGET_2'
                )
                exit_results.append(result)
        
        return exit_results
    
    def _calculate_quantity(self, signal: Dict) -> int:
        """
        Calculate order quantity based on signal and risk.
        Simplified version - should use risk manager for actual calculation.
        """
        # Default quantity (should be calculated from risk manager)
        default_qty = 1
        
        # Try to get quantity from signal
        if 'quantity' in signal:
            return int(signal['quantity'])
        
        # Calculate based on risk (simplified)
        entry_level = signal.get('entry_level', signal.get('current_price', 0))
        stop_loss = signal.get('stop_loss', 0)
        
        if entry_level > 0 and stop_loss > 0:
            risk_per_share = abs(entry_level - stop_loss)
            # Assume 2% risk per trade
            max_risk = 10000  # Default portfolio value assumption
            max_risk_per_trade = max_risk * 0.02
            calculated_qty = int(max_risk_per_trade / risk_per_share) if risk_per_share > 0 else default_qty
            return max(1, calculated_qty)
        
        return default_qty
    
    def _execute_order_with_retry(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        product: str = 'I',
        signal: Optional[Dict] = None
    ) -> Dict:
        """Execute order with retry logic"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.upstox_client.place_order(
                    ticker=ticker,
                    transaction_type=transaction_type,
                    quantity=quantity,
                    order_type=order_type,
                    price=price,
                    trigger_price=trigger_price,
                    product=product
                )
                
                if 'error' not in result:
                    # Success
                    execution_record = {
                        'timestamp': datetime.now().isoformat(),
                        'ticker': ticker,
                        'transaction_type': transaction_type,
                        'quantity': quantity,
                        'order_type': order_type,
                        'price': price,
                        'product': product,
                        'result': result,
                        'signal': signal,
                        'success': True
                    }
                    self.execution_history.append(execution_record)
                    
                    logger.info(
                        f"Order executed: {transaction_type} {quantity} {ticker} "
                        f"@ {price or 'MARKET'} ({order_type})"
                    )
                    
                    return {
                        'success': True,
                        'order_id': result.get('data', {}).get('order_id'),
                        'result': result,
                        'execution_record': execution_record
                    }
                else:
                    last_error = result.get('error')
                    logger.warning(f"Order failed (attempt {attempt}/{self.max_retries}): {last_error}")
            
            except Exception as e:
                last_error = str(e)
                logger.error(f"Order execution error (attempt {attempt}/{self.max_retries}): {e}")
            
            # Wait before retry
            if attempt < self.max_retries:
                time.sleep(self.retry_delay * attempt)  # Exponential backoff
        
        # All retries failed
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'order_type': order_type,
            'price': price,
            'product': product,
            'error': last_error,
            'signal': signal,
            'success': False
        }
        self.execution_history.append(execution_record)
        
        return {
            'success': False,
            'error': last_error,
            'execution_record': execution_record
        }
    
    def _simulate_order(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        price: float,
        order_type: str,
        product: str
    ) -> Dict:
        """Simulate order execution for paper trading"""
        execution_record = {
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'order_type': order_type,
            'price': price,
            'product': product,
            'paper_trade': True,
            'success': True
        }
        self.execution_history.append(execution_record)
        
        return {
            'success': True,
            'order_id': f'PAPER_{datetime.now().timestamp()}',
            'paper_trade': True,
            'execution_record': execution_record
        }
    
    def get_execution_history(self, limit: int = 100) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:] if limit > 0 else self.execution_history.copy()
