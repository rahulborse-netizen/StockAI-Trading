"""
Daily Workflow Manager
Orchestrates pre-market, market hours, and post-market automation tasks
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from datetime import datetime, time

from src.web.market_hours import get_market_hours_manager, MarketHoursManager
from src.web.auto_trader import AutoTrader
from src.web.trading_scheduler import get_trading_scheduler, TradingScheduler
from src.web.data.all_stocks_list import get_all_stocks

logger = logging.getLogger(__name__)


class DailyWorkflowManager:
    """
    Manages daily trading workflow: pre-market, market hours, post-market.
    """
    
    def __init__(
        self,
        auto_trader: Optional[AutoTrader] = None,
        watchlist: Optional[List[str]] = None
    ):
        """
        Initialize daily workflow manager.
        
        Args:
            auto_trader: AutoTrader instance (if None, will be created when needed)
            watchlist: List of tickers to monitor (if None, uses all stocks)
        """
        self.auto_trader = auto_trader
        self.watchlist = watchlist
        self.market_hours = get_market_hours_manager()
        self.scheduler = get_trading_scheduler()
        self.is_running = False
        
        # Workflow state
        self.pre_market_completed = False
        self.market_hours_active = False
        self.post_market_completed = False
        self.workflow_log: List[Dict] = []
    
    def run_pre_market_scan(self) -> Dict:
        """
        Pre-market scan task (9:00 AM).
        Scans all stocks, generates signals, prepares watchlist.
        
        Returns:
            Dictionary with scan results
        """
        logger.info("[Daily Workflow] Running pre-market scan...")
        if self.auto_trader:
            self.auto_trader.reset_daily_pnl()
        try:
            from src.web.ai_models.multi_timeframe_signal import get_multi_timeframe_aggregator
            
            multi_tf_aggregator = get_multi_timeframe_aggregator()
            stocks_to_scan = self.watchlist or get_all_stocks()
            
            # Limit scan to top stocks for performance (can be configured)
            max_scan = 100
            stocks_to_scan = stocks_to_scan[:max_scan]
            
            logger.info(f"[Daily Workflow] Scanning {len(stocks_to_scan)} stocks for pre-market signals...")
            
            signals = []
            errors = []
            
            for ticker in stocks_to_scan:
                try:
                    # Generate daily timeframe signal for pre-market analysis
                    signal = multi_tf_aggregator.generate_multi_timeframe_signal(
                        ticker=ticker,
                        timeframes=['1d'],  # Daily for pre-market
                        is_intraday=False,
                        min_confidence=0.6
                    )
                    
                    if 'error' not in signal:
                        signals.append(signal)
                    else:
                        errors.append({'ticker': ticker, 'error': signal.get('error')})
                
                except Exception as e:
                    logger.error(f"Error generating pre-market signal for {ticker}: {e}")
                    errors.append({'ticker': ticker, 'error': str(e)})
            
            # Sort signals by confidence/probability
            signals.sort(key=lambda x: x.get('probability', 0), reverse=True)
            
            # Prepare watchlist (top N high-confidence signals)
            top_signals = signals[:20]  # Top 20 for watchlist
            watchlist_tickers = [s['ticker'] for s in top_signals]
            
            result = {
                'timestamp': datetime.now().isoformat(),
                'stocks_scanned': len(stocks_to_scan),
                'signals_generated': len(signals),
                'errors': len(errors),
                'watchlist_size': len(watchlist_tickers),
                'top_signals': [
                    {
                        'ticker': s['ticker'],
                        'signal': s.get('consensus_signal', 'HOLD'),
                        'probability': s.get('probability', 0),
                        'confidence': s.get('confidence', 0)
                    }
                    for s in top_signals
                ],
                'watchlist': watchlist_tickers
            }
            
            self.pre_market_completed = True
            self.workflow_log.append({
                'event': 'pre_market_scan',
                'timestamp': datetime.now().isoformat(),
                'result': result
            })
            
            logger.info(
                f"[Daily Workflow] Pre-market scan complete: {len(signals)} signals, "
                f"{len(watchlist_tickers)} stocks in watchlist"
            )
            
            return result
        
        except Exception as e:
            logger.error(f"Error in pre-market scan: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_market_hours_trading(self) -> Dict:
        """
        Market hours trading loop.
        Continuous signal generation and execution during market hours.
        
        Returns:
            Dictionary with trading activity summary
        """
        if not self.market_hours.is_market_open():
            return {
                'error': 'Market is not open',
                'market_status': self.market_hours.get_market_status()
            }
        
        logger.info("[Daily Workflow] Running market hours trading...")
        
        if not self.auto_trader:
            return {
                'error': 'Auto trader not initialized',
                'timestamp': datetime.now().isoformat()
            }
        
        # Ensure auto trader is running
        if not self.auto_trader.is_running:
            self.auto_trader.start()
        
        # Run scan and execute
        scan_result = self.auto_trader.scan_and_execute(
            timeframes=['5m', '15m', '1h', '1d'],
            is_intraday=True
        )
        
        self.market_hours_active = True
        self.workflow_log.append({
            'event': 'market_hours_trading',
            'timestamp': datetime.now().isoformat(),
            'result': scan_result
        })
        
        return scan_result
    
    def run_post_market_cleanup(self) -> Dict:
        """
        Post-market cleanup task (3:45 PM).
        Closes intraday positions, generates daily report.
        
        Returns:
            Dictionary with cleanup results
        """
        logger.info("[Daily Workflow] Running post-market cleanup...")
        
        try:
            cleanup_results = {
                'timestamp': datetime.now().isoformat(),
                'positions_closed': 0,
                'positions_remaining': 0,
                'daily_pnl': 0,
                'errors': []
            }
            
            if self.auto_trader and self.auto_trader.trade_executor:
                # Get current positions
                positions = self.auto_trader._get_current_positions()
                
                # Close all intraday positions
                for position in positions:
                    try:
                        product = position.get('product', 'I')
                        if product == 'I':  # Intraday
                            result = self.auto_trader.trade_executor.execute_sell_order(
                                position=position,
                                reason='EOD_CLEANUP'
                            )
                            
                            if result.get('success'):
                                cleanup_results['positions_closed'] += 1
                            else:
                                cleanup_results['errors'].append({
                                    'ticker': position.get('ticker', ''),
                                    'error': result.get('error', 'Unknown error')
                                })
                    except Exception as e:
                        logger.error(f"Error closing position: {e}")
                        cleanup_results['errors'].append({
                            'ticker': position.get('ticker', ''),
                            'error': str(e)
                        })
                
                cleanup_results['positions_remaining'] = len([
                    p for p in positions if p.get('product', 'I') != 'I'
                ])
            
            # Generate daily report
            daily_report = self._generate_daily_report()
            cleanup_results['daily_report'] = daily_report
            
            self.post_market_completed = True
            self.market_hours_active = False
            self.workflow_log.append({
                'event': 'post_market_cleanup',
                'timestamp': datetime.now().isoformat(),
                'result': cleanup_results
            })
            
            logger.info(
                f"[Daily Workflow] Post-market cleanup complete: "
                f"{cleanup_results['positions_closed']} positions closed"
            )
            
            return cleanup_results
        
        except Exception as e:
            logger.error(f"Error in post-market cleanup: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _generate_daily_report(self) -> Dict:
        """
        Generate daily trading report.
        
        Returns:
            Dictionary with daily report
        """
        report = {
            'date': datetime.now().date().isoformat(),
            'pre_market_completed': self.pre_market_completed,
            'market_hours_active': self.market_hours_active,
            'post_market_completed': self.post_market_completed,
            'workflow_events': len(self.workflow_log)
        }
        
        if self.auto_trader:
            report['auto_trader_status'] = self.auto_trader.get_status()
            report['executed_signals'] = len(self.auto_trader.executed_signals)
            report['rejected_signals'] = len(self.auto_trader.rejected_signals)
        
        return report
    
    def start_daily_workflow(self) -> bool:
        """
        Start daily workflow automation.
        Registers tasks with scheduler and starts execution.
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("Daily workflow is already running")
            return False
        
        logger.info("Starting daily workflow...")
        
        # Register workflow tasks with scheduler
        def pre_market_task():
            self.run_pre_market_scan()
        
        def market_hours_task():
            self.run_market_hours_trading()
        
        def post_market_task():
            self.run_post_market_cleanup()
        
        # Update scheduler job functions
        if 'pre_market_scan' in self.scheduler.jobs:
            self.scheduler.jobs['pre_market_scan']['func'] = pre_market_task
        
        if 'signal_generation' in self.scheduler.jobs:
            self.scheduler.jobs['signal_generation']['func'] = market_hours_task
        
        if 'trade_execution' in self.scheduler.jobs:
            self.scheduler.jobs['trade_execution']['func'] = market_hours_task
        
        if 'post_market_cleanup' in self.scheduler.jobs:
            self.scheduler.jobs['post_market_cleanup']['func'] = post_market_task
        
        # Start scheduler
        if self.scheduler.start_daily_schedule():
            self.is_running = True
            logger.info("Daily workflow started successfully")
            return True
        else:
            logger.error("Failed to start scheduler")
            return False
    
    def stop_daily_workflow(self) -> bool:
        """
        Stop daily workflow automation.
        
        Returns:
            True if stopped successfully
        """
        if not self.is_running:
            logger.warning("Daily workflow is not running")
            return False
        
        logger.info("Stopping daily workflow...")
        
        if self.scheduler.stop_schedule():
            self.is_running = False
            
            if self.auto_trader:
                self.auto_trader.stop()
            
            logger.info("Daily workflow stopped")
            return True
        
        return False
    
    def get_workflow_status(self) -> Dict:
        """
        Get current workflow status.
        
        Returns:
            Dictionary with workflow status
        """
        return {
            'is_running': self.is_running,
            'pre_market_completed': self.pre_market_completed,
            'market_hours_active': self.market_hours_active,
            'post_market_completed': self.post_market_completed,
            'market_status': self.market_hours.get_market_status(),
            'workflow_events': len(self.workflow_log),
            'auto_trader_status': self.auto_trader.get_status() if self.auto_trader else None
        }


# Global instance
_daily_workflow_manager: Optional[DailyWorkflowManager] = None


def get_daily_workflow_manager(auto_trader: Optional[AutoTrader] = None) -> DailyWorkflowManager:
    """Get global daily workflow manager instance"""
    global _daily_workflow_manager
    if _daily_workflow_manager is None:
        _daily_workflow_manager = DailyWorkflowManager(auto_trader=auto_trader)
    return _daily_workflow_manager
