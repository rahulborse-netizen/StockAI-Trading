"""
Real-time Signal Manager
Updates trading signals dynamically based on live market prices
Recalculates strike prices, entry/exit levels, and trade recommendations
"""
import logging
import threading
from typing import Dict, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class RealtimeSignalManager:
    """
    Manages real-time signal updates based on live market prices.
    Tracks active trades and updates signals dynamically.
    """
    
    def __init__(self):
        self.active_signals: Dict[str, Dict] = {}  # ticker -> signal data
        self.active_trades: Dict[str, Dict] = {}  # ticker -> trade details
        self.price_history: Dict[str, List[Dict]] = defaultdict(list)  # ticker -> price history
        self.update_callbacks: List[callable] = []
        self._lock = threading.Lock()
        self.last_update: Dict[str, datetime] = {}
        self.update_interval = 3.0  # Update signals every 3 seconds if price changed (faster for live data)
        self.live_data_refresh_interval = 10.0  # Force refresh every 10 seconds when live data available
        
    def register_update_callback(self, callback: callable):
        """Register callback for signal updates"""
        with self._lock:
            if callback not in self.update_callbacks:
                self.update_callbacks.append(callback)
                logger.info(f"Registered signal update callback: {callback.__name__}")
    
    def on_price_update(self, ticker: str, price_data: Dict, instrument_key: Optional[str] = None):
        """
        Called when price update is received from WebSocket.
        Updates signal if price changed significantly.
        
        Args:
            ticker: Stock/index ticker (e.g., '^NSEI', 'RELIANCE.NS')
            price_data: Price data dict with 'ltp', 'close', etc.
            instrument_key: Optional Upstox instrument_key (for mapping if ticker not available)
        """
        try:
            # If ticker not provided but instrument_key is, try to map it
            if not ticker and instrument_key:
                try:
                    from src.web.websocket_server import get_ticker_for_key
                    ticker = get_ticker_for_key(instrument_key)
                    if not ticker:
                        return  # Can't map instrument_key to ticker
                except Exception:
                    return  # Mapping failed
            
            if not ticker:
                return  # Need ticker to proceed
            
            current_price = price_data.get('ltp') or price_data.get('close') or 0
            if not current_price or current_price <= 0:
                return
            
            # Get last known price
            last_price = None
            if ticker in self.active_signals:
                last_price = self.active_signals[ticker].get('current_price', 0)
            
            # Update if price changed significantly (>0.1% for indices, >0.5% for stocks)
            threshold = 0.001 if ticker.startswith('^') else 0.005
            if last_price and abs(current_price - last_price) / last_price < threshold:
                return  # Price change too small, skip update
            
            # Check if enough time has passed since last update
            now = datetime.now()
            if ticker in self.last_update:
                elapsed = (now - self.last_update[ticker]).total_seconds()
                # For live data, refresh more frequently
                if price_data and price_data.get('source') == 'upstox':
                    min_interval = self.live_data_refresh_interval
                else:
                    min_interval = self.update_interval
                
                if elapsed < min_interval:
                    return  # Too soon, skip update
            
            # Trigger signal update
            logger.info(f"[RealtimeSignal] Price update for {ticker}: {current_price:.2f} (was {last_price:.2f})")
            self.update_signal(ticker, current_price, price_data)
            
        except Exception as e:
            logger.error(f"Error in on_price_update for {ticker}: {e}")
    
    def update_signal(self, ticker: str, current_price: float, price_data: Optional[Dict] = None):
        """
        Update signal for a ticker with current market price.
        Recalculates strike prices, entry/exit levels, and recommendations.
        Uses enhanced signal generator for better accuracy.
        """
        try:
            # Try enhanced signal generator first (better accuracy with live data)
            try:
                from src.web.ai_models.enhanced_signal_generator import get_enhanced_signal_generator
                generator = get_enhanced_signal_generator()
                use_enhanced = True
            except ImportError:
                from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
                generator = get_elite_signal_generator()
                use_enhanced = False
            
            from src.web.index_signals import enhance_index_signal
            
            # Generate fresh signal with current price (enhanced generator uses live data)
            if use_enhanced:
                signal_response = generator.update_signal_with_live_price(
                    ticker=ticker,
                    live_price=current_price,
                    instrument_key_override=price_data.get('instrument_key') if price_data else None
                )
            else:
                signal_response = generator.generate_signal(
                    ticker=ticker,
                    use_ensemble=True,
                    use_multi_timeframe=True
                )
            
            if signal_response and 'error' not in signal_response:
                # Update current price from live data
                signal_response['current_price'] = current_price
                
                # Enhance with strike prices if it's an index
                if ticker.startswith('^'):
                    signal_response = enhance_index_signal(ticker, signal_response)
                else:
                    # For stocks, calculate strike prices based on current price
                    signal_response = self._calculate_stock_strikes(ticker, signal_response, current_price)
                
                # Update active trade if exists
                if ticker in self.active_trades:
                    signal_response = self._update_active_trade(ticker, signal_response, current_price)
                
                # Store updated signal
                with self._lock:
                    self.active_signals[ticker] = signal_response
                    self.last_update[ticker] = datetime.now()
                
                # Store price history (keep last 100 updates)
                self.price_history[ticker].append({
                    'price': current_price,
                    'timestamp': datetime.now().isoformat(),
                    'signal': signal_response.get('signal', 'HOLD')
                })
                if len(self.price_history[ticker]) > 100:
                    self.price_history[ticker].pop(0)
                
                # Notify callbacks
                self._notify_update(ticker, signal_response)
                
                logger.info(f"[RealtimeSignal] ✅ Updated signal for {ticker}: {signal_response.get('signal', 'N/A')} @ ₹{current_price:.2f}")
                return signal_response
            else:
                logger.warning(f"[RealtimeSignal] Failed to update signal for {ticker}: {signal_response.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating signal for {ticker}: {e}", exc_info=True)
            return None
    
    def _calculate_stock_strikes(self, ticker: str, signal: Dict, current_price: float) -> Dict:
        """
        Calculate strike prices for stock options based on current price.
        Uses standard NSE strike intervals (50 for stocks >1000, 25 for stocks 500-1000, 10 for stocks <500)
        """
        # Determine strike interval based on price
        if current_price >= 1000:
            interval = 50
        elif current_price >= 500:
            interval = 25
        else:
            interval = 10
        
        # Round to nearest strike
        strike_atm = int(round(current_price / interval) * interval)
        
        # For bullish signals, suggest OTM call (strike above ATM)
        # For bearish signals, suggest OTM put (strike below ATM)
        signal_type = signal.get('signal', 'HOLD')
        if signal_type in ('STRONG_BUY', 'BUY'):
            strike_ce = strike_atm + interval  # OTM call
            strike_pe = strike_atm  # ATM put for hedging
            option_type = 'CE'
            option_label = f'Call OTM ({strike_ce})'
        elif signal_type in ('STRONG_SELL', 'SELL'):
            strike_ce = strike_atm  # ATM call for hedging
            strike_pe = strike_atm - interval  # OTM put
            option_type = 'PE'
            option_label = f'Put OTM ({strike_pe})'
        else:
            strike_ce = strike_atm
            strike_pe = strike_atm
            option_type = ''
            option_label = '—'
        
        signal['strike_atm'] = strike_atm
        signal['strike_ce'] = strike_ce
        signal['strike_pe'] = strike_pe
        signal['strike_interval'] = interval
        signal['option_type'] = option_type
        signal['option_label'] = option_label
        
        return signal
    
    def _update_active_trade(self, ticker: str, signal: Dict, current_price: float) -> Dict:
        """
        Update active trade with current market conditions.
        Adjusts stop-loss, targets, and provides trade management recommendations.
        """
        trade = self.active_trades[ticker]
        entry_price = trade.get('entry_price', 0)
        stop_loss = trade.get('stop_loss', 0)
        target_1 = trade.get('target_1', 0)
        target_2 = trade.get('target_2', 0)
        trade_type = trade.get('type', 'LONG')  # LONG or SHORT
        
        if not entry_price or entry_price <= 0:
            return signal
        
        # Calculate P&L
        if trade_type == 'LONG':
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        else:  # SHORT
            pnl_pct = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0
        
        # Update signal with trade status
        signal['trade_status'] = {
            'entry_price': entry_price,
            'current_price': current_price,
            'pnl_pct': round(pnl_pct, 2),
            'stop_loss': stop_loss,
            'target_1': target_1,
            'target_2': target_2,
            'trade_type': trade_type
        }
        
        # Generate trade management recommendations
        recommendations = []
        
        # Check stop-loss hit
        if trade_type == 'LONG' and current_price <= stop_loss:
            recommendations.append("⚠️ STOP-LOSS HIT - Exit position immediately")
        elif trade_type == 'SHORT' and current_price >= stop_loss:
            recommendations.append("⚠️ STOP-LOSS HIT - Exit position immediately")
        
        # Check target 1 hit
        if trade_type == 'LONG' and current_price >= target_1:
            recommendations.append(f"✅ TARGET 1 HIT ({target_1:.2f}) - Book partial profits (50%)")
        elif trade_type == 'SHORT' and current_price <= target_1:
            recommendations.append(f"✅ TARGET 1 HIT ({target_1:.2f}) - Book partial profits (50%)")
        
        # Check target 2 hit
        if trade_type == 'LONG' and current_price >= target_2:
            recommendations.append(f"🎯 TARGET 2 HIT ({target_2:.2f}) - Book remaining profits")
        elif trade_type == 'SHORT' and current_price <= target_2:
            recommendations.append(f"🎯 TARGET 2 HIT ({target_2:.2f}) - Book remaining profits")
        
        # Trailing stop-loss recommendation
        if pnl_pct > 5:  # If in profit >5%
            new_stop = entry_price * 1.02 if trade_type == 'LONG' else entry_price * 0.98
            if (trade_type == 'LONG' and new_stop > stop_loss) or (trade_type == 'SHORT' and new_stop < stop_loss):
                recommendations.append(f"📈 Consider trailing stop-loss to ₹{new_stop:.2f} (lock in profits)")
        
        # Update signal with recommendations
        if recommendations:
            signal['trade_recommendations'] = recommendations
            signal['trade_action'] = ' | '.join(recommendations)
        
        return signal
    
    def register_trade(self, ticker: str, trade_details: Dict):
        """
        Register an active trade for tracking.
        trade_details should contain: entry_price, stop_loss, target_1, target_2, type (LONG/SHORT)
        """
        with self._lock:
            self.active_trades[ticker] = trade_details
            logger.info(f"[RealtimeSignal] Registered trade for {ticker}: {trade_details.get('type', 'LONG')} @ ₹{trade_details.get('entry_price', 0):.2f}")
    
    def unregister_trade(self, ticker: str):
        """Unregister an active trade"""
        with self._lock:
            if ticker in self.active_trades:
                del self.active_trades[ticker]
                logger.info(f"[RealtimeSignal] Unregistered trade for {ticker}")
    
    def get_active_trades(self) -> Dict[str, Dict]:
        """Get all active trades"""
        with self._lock:
            return dict(self.active_trades)
    
    def get_signal(self, ticker: str) -> Optional[Dict]:
        """Get current signal for a ticker"""
        with self._lock:
            return self.active_signals.get(ticker)
    
    def _notify_update(self, ticker: str, signal: Dict):
        """Notify all registered callbacks of signal update"""
        for callback in self.update_callbacks:
            try:
                callback(ticker, signal)
            except Exception as e:
                logger.error(f"Error in signal update callback: {e}")
        
        # Also broadcast via Socket.IO if available
        try:
            # Import the global socketio instance from websocket_server
            import src.web.websocket_server as ws_module
            socketio_instance = getattr(ws_module, '_socketio_instance', None)
            if socketio_instance:
                socketio_instance.emit('signal_update', {
                    'ticker': ticker,
                    'signal': signal
                }, broadcast=True)
                logger.debug(f"[RealtimeSignal] Broadcasted signal update for {ticker} via Socket.IO")
        except Exception as e:
            logger.debug(f"Socket.IO broadcast skipped: {e}")


# Global instance
_realtime_signal_manager: Optional[RealtimeSignalManager] = None


def get_realtime_signal_manager() -> RealtimeSignalManager:
    """Get global RealtimeSignalManager instance"""
    global _realtime_signal_manager
    if _realtime_signal_manager is None:
        _realtime_signal_manager = RealtimeSignalManager()
    return _realtime_signal_manager
