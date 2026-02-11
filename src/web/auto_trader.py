"""
Auto Trader Service
Monitors signals and automatically executes trades based on high-confidence signals
"""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json

from src.web.ai_models.multi_timeframe_signal import get_multi_timeframe_aggregator
from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
from src.web.risk_manager import get_risk_manager
from src.web.risk_config import get_risk_config
from src.web.trade_executor import TradeExecutor
from src.web.upstox_api import UpstoxAPI
from src.web.data.all_stocks_list import get_all_stocks
from src.web.market_hours import MarketHoursManager, get_market_hours_manager

logger = logging.getLogger(__name__)


class AutoTrader:
    """
    Automatic trading service that monitors signals and executes trades.
    """
    
    def __init__(
        self,
        upstox_client: Optional[UpstoxAPI] = None,
        confidence_threshold: float = 0.7,
        max_positions: int = 10,
        watchlist: Optional[List[str]] = None
    ):
        """
        Initialize auto trader.
        
        Args:
            upstox_client: Upstox API client (required for live trading)
            confidence_threshold: Minimum confidence threshold for execution (default: 0.7)
            max_positions: Maximum concurrent positions (default: 10)
            watchlist: List of tickers to monitor (if None, uses all stocks)
        """
        self.upstox_client = upstox_client
        rc = get_risk_config()
        self.confidence_threshold = float(rc.get('confidence_threshold', confidence_threshold))
        self.max_positions = int(rc.get('max_open_positions', max_positions))
        self.watchlist = watchlist
        self.is_running = False
        
        # Initialize components
        self.multi_tf_aggregator = get_multi_timeframe_aggregator()
        self.elite_generator = get_elite_signal_generator()
        self.risk_manager = get_risk_manager()
        self.trade_executor = (
            TradeExecutor(upstox_client, on_pnl_callback=self.update_pnl)
            if upstox_client else None
        )
        self.market_hours = get_market_hours_manager()
        
        # Execution tracking
        self.executed_signals: List[Dict] = []
        self.rejected_signals: List[Dict] = []
        
        # Circuit breaker state (from config)
        self.circuit_breaker_enabled = True
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.daily_loss_limit_pct = float(rc.get('daily_loss_limit_pct', 0.10))
        self.daily_loss_limit_amount = float(rc.get('daily_loss_limit_amount', 50000.0))
        self.max_consecutive_losses = int(rc.get('max_consecutive_losses', 5))
        self.circuit_breaker_triggered = False
        self.circuit_breaker_time = None
        self.cooldown_minutes = int(rc.get('cooldown_minutes', 60))
        self.signal_source = (rc.get('signal_source') or 'elite').lower()
        self.quant_ensemble_method = rc.get('quant_ensemble_method') or 'weighted_average'
        self.min_accuracy = float(rc.get('min_accuracy', 0.0))
        self.use_adaptive_threshold = bool(rc.get('use_adaptive_threshold', False))
        self.adaptive_threshold_floor = float(rc.get('adaptive_threshold_floor', 0.75))
        self.use_regime_thresholds = bool(rc.get('use_regime_thresholds', False))
        self.confidence_threshold_ranging = float(rc.get('confidence_threshold_ranging', 0.75))
        self.confidence_threshold_trending = float(rc.get('confidence_threshold_trending', 0.65))
        self.cooldown_hours_after_ticker_loss = int(rc.get('cooldown_hours_after_ticker_loss', 24))
        self._ticker_last_loss_time: Dict[str, datetime] = {}
        self._load_ticker_cooldown()
        self._scan_lock = threading.Lock()

    def _cooldown_file(self) -> Path:
        return Path("data/ticker_cooldown.json")

    def _load_ticker_cooldown(self) -> None:
        p = self._cooldown_file()
        if not p.exists():
            return
        try:
            with open(p) as f:
                raw = json.load(f)
            for k, v in (raw or {}).items():
                try:
                    self._ticker_last_loss_time[k] = datetime.fromisoformat(v)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Load ticker cooldown failed: {e}")

    def _save_ticker_cooldown(self) -> None:
        p = self._cooldown_file()
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            out = {k: v.isoformat() for k, v in self._ticker_last_loss_time.items()}
            with open(p, "w") as f:
                json.dump(out, f)
        except Exception as e:
            logger.debug(f"Save ticker cooldown failed: {e}")

    def _is_ticker_in_cooldown(self, ticker: str) -> bool:
        if self.cooldown_hours_after_ticker_loss <= 0:
            return False
        t = self._ticker_last_loss_time.get(ticker)
        if not t:
            return False
        from datetime import timedelta
        return (datetime.now() - t).total_seconds() < self.cooldown_hours_after_ticker_loss * 3600

    def scan_and_execute(
        self,
        timeframes: Optional[List[str]] = None,
        is_intraday: bool = True
    ) -> Dict:
        """
        Scan all stocks in watchlist, generate signals, and execute high-confidence trades.
        
        Args:
            timeframes: List of timeframes to analyze (default: ['5m', '15m', '1h', '1d'])
            is_intraday: Whether currently in intraday trading hours
        
        Returns:
            Dictionary with scan results and execution summary
        """
        if not self.is_running:
            return {
                'error': 'Auto trader is not running',
                'success': False
            }
        if not self._scan_lock.acquire(blocking=False):
            return {
                'error': 'Scan already in progress',
                'success': False,
                'skipped': True
            }
        try:
            return self._scan_and_execute_impl(timeframes=timeframes, is_intraday=is_intraday)
        finally:
            self._scan_lock.release()
    
    def _scan_and_execute_impl(
        self,
        timeframes: Optional[List[str]] = None,
        is_intraday: bool = True
    ) -> Dict:
        """Internal scan-and-execute (called with _scan_lock held)."""
        # Check market hours
        if not self.market_hours.is_market_open():
            return {
                'error': 'Market is closed',
                'success': False,
                'market_status': self.market_hours.get_market_status()
            }
        
        if timeframes is None:
            timeframes = ['5m', '15m', '1h', '1d']
        
        # Get watchlist
        stocks_to_scan = self.watchlist or get_all_stocks()
        
        logger.info(f"[AutoTrader] Scanning {len(stocks_to_scan)} stocks...")
        
        scan_results = {
            'timestamp': datetime.now().isoformat(),
            'stocks_scanned': len(stocks_to_scan),
            'signals_generated': 0,
            'signals_executed': 0,
            'signals_rejected': 0,
            'executions': [],
            'rejections': []
        }
        
        # Get current positions
        current_positions = self._get_current_positions()
        portfolio_value = self._get_portfolio_value()
        
        # Scan each stock
        use_quant = self.signal_source in ('quant', 'quant_ensemble')
        if use_quant:
            from src.web.strategies.strategy_manager import get_strategy_manager
            strategy_manager = get_strategy_manager()

        for ticker in stocks_to_scan:
            try:
                if use_quant:
                    data = strategy_manager.get_market_data_for_ticker(ticker)
                    if not data:
                        continue
                    if self.signal_source == 'quant_ensemble':
                        result = strategy_manager.combine_strategies(
                            data, method=self.quant_ensemble_method
                        )
                    else:
                        result = strategy_manager.execute_active_strategy(data)
                    model_id = 'quant_ensemble' if self.signal_source == 'quant_ensemble' else ('quant_' + strategy_manager.active_strategy)
                    signal = {
                        'ticker': ticker,
                        'consensus_signal': result.signal,
                        'probability': result.confidence,
                        'entry_level': result.entry_price or data['current_price'],
                        'stop_loss': result.stop_loss,
                        'target_1': result.target_1,
                        'target_2': result.target_2,
                        'current_price': data['current_price'],
                        'source': 'quant',
                        'model_id': model_id,
                        'metadata': getattr(result, 'metadata', None),
                    }
                    regime = (data.get('market_data') or {}).get('regime_type')
                    eff_threshold = self._get_effective_confidence_threshold(regime=regime)
                    in_cooldown = self._is_ticker_in_cooldown(ticker)
                    should_exec = (
                        result.signal != 'HOLD'
                        and result.confidence >= eff_threshold
                        and self._passes_execution_filter(signal, data)
                        and not in_cooldown
                    )
                else:
                    signal = self.multi_tf_aggregator.generate_multi_timeframe_signal(
                        ticker=ticker,
                        timeframes=timeframes,
                        is_intraday=is_intraday,
                        min_confidence=self.confidence_threshold
                    )
                    if 'error' in signal:
                        continue
                    signal['model_id'] = signal.get('model_id') or 'elite_multi_tf'
                    # Fetch market_data for ELITE path (trend filter + regime-aware threshold)
                    elite_market_data = self._get_market_data_for_filter(ticker, signal)
                    regime = elite_market_data.get('regime_type') if elite_market_data else None
                    eff_threshold = self._get_effective_confidence_threshold(regime=regime)
                    should_exec = (
                        self.multi_tf_aggregator.should_execute(signal, eff_threshold)
                        and self._passes_execution_filter(signal, elite_market_data)
                        and not self._is_ticker_in_cooldown(ticker)
                    )

                scan_results['signals_generated'] += 1
                if should_exec:
                    execution_result = self.execute_signal(
                        signal=signal,
                        current_positions=current_positions,
                        portfolio_value=portfolio_value
                    )
                    if execution_result.get('success'):
                        scan_results['signals_executed'] += 1
                        scan_results['executions'].append(execution_result)
                        self.executed_signals.append(signal)
                    else:
                        scan_results['signals_rejected'] += 1
                        scan_results['rejections'].append({
                            'ticker': ticker,
                            'reason': execution_result.get('reason', 'Unknown'),
                            'signal': signal
                        })
                        self.rejected_signals.append(signal)
                else:
                    scan_results['signals_rejected'] += 1
                    scan_results['rejections'].append({
                        'ticker': ticker,
                        'reason': 'Signal does not meet execution criteria',
                        'signal': signal
                    })
            except Exception as e:
                logger.error(f"Error scanning {ticker}: {e}")
                continue
        
        logger.info(
            f"[AutoTrader] Scan complete: {scan_results['signals_generated']} signals, "
            f"{scan_results['signals_executed']} executed, {scan_results['signals_rejected']} rejected"
        )
        
        return scan_results
    
    def execute_signal(
        self,
        signal: Dict,
        current_positions: Optional[List[Dict]] = None,
        portfolio_value: Optional[float] = None
    ) -> Dict:
        """
        Execute a single signal with risk checks.
        
        Args:
            signal: Signal dictionary from multi-timeframe aggregator
            current_positions: Current open positions (if None, fetched)
            portfolio_value: Current portfolio value (if None, fetched)
        
        Returns:
            Execution result dictionary
        """
        # Check circuit breaker first
        if self.check_circuit_breaker():
            return {
                'success': False,
                'reason': 'Circuit breaker active - trading paused',
                'circuit_breaker_status': {
                    'triggered': self.circuit_breaker_triggered,
                    'consecutive_losses': self.consecutive_losses,
                    'daily_pnl': self.daily_pnl
                },
                'signal': signal
            }
        
        if not self.trade_executor:
            return {
                'success': False,
                'reason': 'Trade executor not initialized (Upstox client required)'
            }
        
        ticker = signal.get('ticker', '')
        consensus_signal = signal.get('consensus_signal', 'HOLD')
        
        # Only execute BUY/SELL signals
        if consensus_signal == 'HOLD':
            return {
                'success': False,
                'reason': 'Signal is HOLD',
                'signal': signal
            }
        
        # Get current positions and portfolio value if not provided
        if current_positions is None:
            current_positions = self._get_current_positions()
        
        if portfolio_value is None:
            portfolio_value = self._get_portfolio_value()
        
        # Risk check
        risk_result = self.risk_manager.check_auto_trade_risk(
            signal=signal,
            current_positions=current_positions,
            portfolio_value=portfolio_value
        )
        
        if not risk_result.passed:
            return {
                'success': False,
                'reason': f'Risk check failed: {risk_result.message}',
                'risk_details': risk_result.details,
                'signal': signal
            }
        
        # Check max positions
        if len(current_positions) >= self.max_positions:
            return {
                'success': False,
                'reason': f'Maximum positions ({self.max_positions}) reached',
                'signal': signal
            }
        
        # Execute trade
        try:
            if consensus_signal in ['BUY', 'STRONG_BUY']:
                # Calculate quantity from risk details
                max_quantity = risk_result.details.get('max_quantity', 1)
                
                execution_result = self.trade_executor.execute_buy_order(
                    signal=signal,
                    quantity=max_quantity,
                    product='I'  # Intraday
                )
                
                if execution_result.get('success'):
                    try:
                        from src.web.ai_models.performance_tracker import get_performance_tracker
                        tracker = get_performance_tracker()
                        model_id = signal.get('model_id', 'elite_multi_tf')
                        prob = float(signal.get('probability', 0.5))
                        entry = float(signal.get('entry_level') or signal.get('current_price') or 0)
                        if entry > 0:
                            tracker.add_pending(model_id=model_id, ticker=ticker, prediction=prob, entry_price=entry)
                    except Exception as e:
                        logger.debug(f"Could not add pending prediction: {e}")
                
                return {
                    'success': execution_result.get('success', False),
                    'execution_result': execution_result,
                    'signal': signal,
                    'risk_check': risk_result.details
                }
            
            elif consensus_signal in ['SELL', 'STRONG_SELL']:
                signal_symbol = (ticker or '').replace('.NS', '').replace('.BO', '').strip().upper()
                if not signal_symbol:
                    return {
                        'success': False,
                        'reason': 'SELL signal has no ticker',
                        'signal': signal
                    }
                matching_position = None
                for pos in current_positions:
                    pos_symbol = (pos.get('tradingsymbol') or pos.get('symbol') or '').strip().upper()
                    if not pos_symbol:
                        continue
                    if pos_symbol == signal_symbol:
                        matching_position = pos
                        break
                if not matching_position:
                    return {
                        'success': False,
                        'reason': f'No open position for SELL ({ticker})',
                        'signal': signal
                    }
                quantity = int(matching_position.get('quantity', 0) or matching_position.get('qty', 0))
                if quantity <= 0:
                    return {
                        'success': False,
                        'reason': f'Position quantity invalid for {ticker}',
                        'signal': signal
                    }
                position_for_executor = {
                    'ticker': ticker,
                    'symbol': matching_position.get('tradingsymbol') or matching_position.get('symbol'),
                    'quantity': quantity,
                    'average_price': matching_position.get('average_price') or matching_position.get('avg_price'),
                    'entry_price': matching_position.get('average_price') or matching_position.get('avg_price'),
                    'current_price': signal.get('current_price') or matching_position.get('ltp') or matching_position.get('current_price'),
                    'ltp': matching_position.get('ltp') or matching_position.get('current_price'),
                    'product': matching_position.get('product', 'I'),
                }
                execution_result = self.trade_executor.execute_sell_order(
                    position=position_for_executor,
                    reason='SIGNAL_SELL'
                )
                return {
                    'success': execution_result.get('success', False),
                    'execution_result': execution_result,
                    'signal': signal,
                    'position': matching_position,
                }
            
            else:
                return {
                    'success': False,
                    'reason': f'Unknown signal type: {consensus_signal}',
                    'signal': signal
                }
        
        except Exception as e:
            logger.error(f"Error executing signal for {ticker}: {e}")
            return {
                'success': False,
                'reason': f'Execution error: {str(e)}',
                'signal': signal
            }
    
    def should_execute(self, signal: Dict) -> bool:
        """
        Determine if signal should be executed (wrapper for multi-timeframe aggregator).
        
        Args:
            signal: Signal dictionary
        
        Returns:
            True if signal should be executed
        """
        return self.multi_tf_aggregator.should_execute(signal, self.confidence_threshold)
    
    def start(self) -> bool:
        """Start auto trading"""
        if self.is_running:
            logger.warning("Auto trader is already running")
            return False
        
        if not self.trade_executor:
            logger.error("Cannot start: Trade executor not initialized")
            return False
        
        self.is_running = True
        logger.info("Auto trader started")
        return True
    
    def stop(self) -> bool:
        """Stop auto trading"""
        if not self.is_running:
            logger.warning("Auto trader is not running")
            return False
        
        self.is_running = False
        logger.info("Auto trader stopped")
        return True
    
    def _get_market_data_for_filter(self, ticker: str, signal: Dict) -> Optional[Dict]:
        """Fetch market data for ELITE path to apply trend filter and regime-aware threshold. Returns None on failure."""
        try:
            from src.web.strategies.strategy_manager import get_strategy_manager
            sm = get_strategy_manager()
            data = sm.get_market_data_for_ticker(ticker)
            if not data:
                return None
            md = data.get('market_data') or data
            cp = float(data.get('current_price') or md.get('current_price') or signal.get('current_price') or 0)
            sma = float(data.get('sma_20') or md.get('sma_20') or cp)
            if cp <= 0:
                return None
            regime = md.get('regime_type') if isinstance(md, dict) else None
            return {'current_price': cp, 'sma_20': sma, 'regime_type': regime}
        except Exception as e:
            logger.debug(f"Could not fetch market data for filter ({ticker}): {e}")
            return None

    def _passes_execution_filter(self, signal: Dict, market_data: Optional[Dict] = None) -> bool:
        """Light execution filter: confidence (handled by should_execute) + trend confirmation when market_data available."""
        if not market_data:
            return True
        consensus = signal.get('consensus_signal', 'HOLD')
        if consensus not in ('BUY', 'STRONG_BUY', 'SELL', 'STRONG_SELL'):
            return True
        current_price = float(market_data.get('current_price', 0) or 0)
        sma_20 = float(market_data.get('sma_20', current_price) or current_price)
        if current_price <= 0 or sma_20 <= 0:
            return True
        if consensus in ('BUY', 'STRONG_BUY'):
            return current_price >= sma_20 * 0.97
        return current_price <= sma_20 * 1.03
    
    def _get_effective_confidence_threshold(self, regime: Optional[str] = None) -> float:
        """Return confidence threshold; regime-aware and/or adaptive-accuracy floor."""
        base = self.confidence_threshold
        if getattr(self, 'use_regime_thresholds', False) and regime:
            if regime == 'RANGING':
                base = getattr(self, 'confidence_threshold_ranging', 0.75)
            elif regime in ('STRONG_TREND', 'WEAK_TREND'):
                base = getattr(self, 'confidence_threshold_trending', 0.65)
        if not getattr(self, 'use_adaptive_threshold', False):
            return base
        try:
            from src.web.ai_models.performance_tracker import get_performance_tracker
            from src.web.strategies.strategy_manager import get_strategy_manager
            sm = get_strategy_manager()
            model_id = 'quant_ensemble' if self.signal_source == 'quant_ensemble' else ('quant_' + sm.active_strategy if self.signal_source == 'quant' else 'elite_multi_tf')
            metrics = get_performance_tracker().calculate_metrics(model_id, days=30)
            if 'error' in metrics:
                return base
            ev = metrics.get('evaluated_predictions', 0)
            acc = metrics.get('accuracy', 0)
            if ev >= 5 and acc < 0.5:
                return max(base, getattr(self, 'adaptive_threshold_floor', 0.75))
        except Exception:
            pass
        return base
    
    def _get_current_positions(self) -> List[Dict]:
        """Get current open positions"""
        if not self.upstox_client:
            return []
        
        try:
            positions = self.upstox_client.get_positions()
            return positions if positions else []
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def _get_portfolio_value(self) -> float:
        """Get current portfolio value"""
        if not self.upstox_client:
            return 100000.0  # Default assumption
        
        try:
            profile = self.upstox_client.get_profile()
            if profile and 'data' in profile:
                # Extract portfolio value from profile (structure may vary)
                return float(profile['data'].get('equity', {}).get('total', 100000.0))
        except Exception as e:
            logger.error(f"Error getting portfolio value: {e}")
        
        return 100000.0  # Default fallback
    
    def get_status(self) -> Dict:
        """Get auto trader status"""
        from src.web.strategies.strategy_manager import get_strategy_manager
        sm = get_strategy_manager()
        return {
            'is_running': self.is_running,
            'confidence_threshold': self.confidence_threshold,
            'max_positions': self.max_positions,
            'watchlist_size': len(self.watchlist) if self.watchlist else None,
            'executed_signals_count': len(self.executed_signals),
            'rejected_signals_count': len(self.rejected_signals),
            'market_status': self.market_hours.get_market_status() if self.market_hours else None,
            'signal_source': getattr(self, 'signal_source', 'elite'),
            'quant_ensemble_method': getattr(self, 'quant_ensemble_method', 'weighted_average'),
            'active_quant_strategy': sm.active_strategy if sm else None,
            'available_quant_strategies': sm.get_available_strategies() if sm else [],
            'circuit_breaker': {
                'enabled': self.circuit_breaker_enabled,
                'triggered': self.circuit_breaker_triggered,
                'consecutive_losses': self.consecutive_losses,
                'daily_pnl': self.daily_pnl,
                'cooldown_until': self.circuit_breaker_time.isoformat() if self.circuit_breaker_time else None,
                'daily_loss_limit_pct': self.daily_loss_limit_pct,
                'daily_loss_limit_amount': self.daily_loss_limit_amount,
                'max_consecutive_losses': self.max_consecutive_losses,
                'cooldown_minutes': self.cooldown_minutes,
            }
        }
    
    def check_circuit_breaker(self) -> bool:
        """
        Check if circuit breaker should prevent trading.
        
        Returns:
            True if circuit breaker is active (trading should be paused)
        """
        if not self.circuit_breaker_enabled:
            return False
        
        # Check consecutive losses
        if self.consecutive_losses >= self.max_consecutive_losses:
            if not self.circuit_breaker_triggered:
                self.circuit_breaker_triggered = True
                self.circuit_breaker_time = datetime.now()
                logger.warning(
                    f"Circuit breaker triggered: {self.consecutive_losses} consecutive losses"
                )
            return True
        
        # Check daily loss limit (percentage)
        portfolio_value = self._get_portfolio_value()
        daily_loss_pct = abs(self.daily_pnl) / portfolio_value if portfolio_value > 0 else 0
        
        if self.daily_pnl < 0 and daily_loss_pct >= self.daily_loss_limit_pct:
            if not self.circuit_breaker_triggered:
                self.circuit_breaker_triggered = True
                self.circuit_breaker_time = datetime.now()
                logger.warning(
                    f"Circuit breaker triggered: Daily loss {daily_loss_pct*100:.2f}% exceeds limit {self.daily_loss_limit_pct*100:.2f}%"
                )
            return True
        
        # Check daily loss limit (absolute amount)
        if self.daily_pnl < 0 and abs(self.daily_pnl) >= self.daily_loss_limit_amount:
            if not self.circuit_breaker_triggered:
                self.circuit_breaker_triggered = True
                self.circuit_breaker_time = datetime.now()
                logger.warning(
                    f"Circuit breaker triggered: Daily loss Rs {abs(self.daily_pnl):.2f} exceeds limit Rs {self.daily_loss_limit_amount:.2f}"
                )
            return True
        
        # Check min accuracy (pause if 30-day accuracy below threshold)
        if getattr(self, 'min_accuracy', 0) > 0:
            try:
                from src.web.ai_models.performance_tracker import get_performance_tracker
                from src.web.strategies.strategy_manager import get_strategy_manager
                sm = get_strategy_manager()
                model_id = 'quant_ensemble' if self.signal_source == 'quant_ensemble' else ('quant_' + sm.active_strategy if self.signal_source == 'quant' else 'elite_multi_tf')
                metrics = get_performance_tracker().calculate_metrics(model_id, days=30)
                if 'error' not in metrics:
                    ev = metrics.get('evaluated_predictions', 0)
                    acc = metrics.get('accuracy', 0)
                    if ev >= 5 and acc < self.min_accuracy:
                        if not self.circuit_breaker_triggered:
                            self.circuit_breaker_triggered = True
                            self.circuit_breaker_time = datetime.now()
                            logger.warning(
                                f"Circuit breaker triggered: 30-day accuracy {acc*100:.1f}% below min {self.min_accuracy*100:.1f}%"
                            )
                        return True
            except Exception as e:
                logger.debug(f"Min accuracy check failed: {e}")
        
        # Check cooldown period
        if self.circuit_breaker_triggered and self.circuit_breaker_time:
            from datetime import timedelta
            cooldown_end = self.circuit_breaker_time + timedelta(minutes=self.cooldown_minutes)
            
            if datetime.now() < cooldown_end:
                return True  # Still in cooldown
            else:
                # Cooldown expired, reset circuit breaker
                logger.info("Circuit breaker cooldown expired, resuming trading")
                self.circuit_breaker_triggered = False
                self.circuit_breaker_time = None
                self.consecutive_losses = 0  # Reset consecutive losses after cooldown
                return False
        
        return False
    
    def reset_circuit_breaker(self) -> None:
        """Manually reset circuit breaker (for manual override)"""
        self.circuit_breaker_triggered = False
        self.circuit_breaker_time = None
        self.consecutive_losses = 0
        logger.info("Circuit breaker manually reset")
    
    def update_pnl(self, pnl: float, ticker: Optional[str] = None) -> None:
        """
        Update daily P&L (called when positions are closed).
        Optionally record per-ticker loss time for cooldown.
        
        Args:
            pnl: Profit/loss amount (positive for profit, negative for loss)
            ticker: Ticker symbol (if provided and pnl < 0, cooldown is recorded)
        """
        self.daily_pnl += pnl
        
        if pnl < 0:
            self.consecutive_losses += 1
            if ticker and self.cooldown_hours_after_ticker_loss > 0:
                self._ticker_last_loss_time[ticker] = datetime.now()
                self._save_ticker_cooldown()
        else:
            self.consecutive_losses = 0
        
        logger.debug(f"Updated P&L: {pnl:.2f}, Daily P&L: {self.daily_pnl:.2f}, Consecutive losses: {self.consecutive_losses}")

    def reset_daily_pnl(self) -> None:
        """Reset daily P&L at start of day (e.g. from pre-market)."""
        self.daily_pnl = 0.0
        logger.info("Daily P&L reset for new trading day")
