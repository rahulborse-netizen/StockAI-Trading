"""
Background Signal Refresh Service
Refreshes signals in the background without blocking user requests
"""
import logging
import threading
import time
from typing import List, Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SignalRefreshService:
    """Background service to refresh signals periodically"""
    
    def __init__(self):
        self.refresh_interval = 3600  # Refresh every hour (3600 seconds)
        self.refresh_thread = None
        self.running = False
        self.last_refresh = {}
        self.priority_tickers = []  # Tickers to refresh more frequently
    
    def start(self, priority_tickers: Optional[List[str]] = None):
        """Start background refresh service"""
        if self.running:
            logger.warning("[SignalRefresh] Refresh service already running")
            return
        
        self.priority_tickers = priority_tickers or []
        self.running = True
        self.refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.refresh_thread.start()
        logger.info(f"[SignalRefresh] ✅ Background refresh service started (interval: {self.refresh_interval}s)")
    
    def stop(self):
        """Stop background refresh service"""
        self.running = False
        if self.refresh_thread:
            self.refresh_thread.join(timeout=5)
        logger.info("[SignalRefresh] Background refresh service stopped")
    
    def _refresh_loop(self):
        """Main refresh loop"""
        while self.running:
            try:
                # Refresh priority tickers more frequently (every 15 minutes)
                priority_interval = 900  # 15 minutes
                if self.priority_tickers:
                    time_since_priority_refresh = time.time() - self.last_refresh.get('priority', 0)
                    if time_since_priority_refresh >= priority_interval:
                        self._refresh_signals(self.priority_tickers, priority=True)
                        self.last_refresh['priority'] = time.time()
                
                # Refresh all cached signals periodically
                time_since_refresh = time.time() - self.last_refresh.get('all', 0)
                if time_since_refresh >= self.refresh_interval:
                    self._refresh_signals()
                    self.last_refresh['all'] = time.time()
                
                # Sleep for 5 minutes before checking again
                time.sleep(300)
                
            except Exception as e:
                logger.error(f"[SignalRefresh] Error in refresh loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute on error before retrying
    
    def _refresh_signals(self, tickers: Optional[List[str]] = None, priority: bool = False):
        """Refresh signals for given tickers"""
        try:
            from src.web.signal_cache import get_all_cached_signals
            from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
            
            if not tickers:
                # Get all cached tickers
                cached_signals = get_all_cached_signals()
                tickers = list(cached_signals.keys())
            
            if not tickers:
                return
            
            logger.info(f"[SignalRefresh] Refreshing {len(tickers)} signals ({'priority' if priority else 'background'})...")
            
            generator = get_elite_signal_generator()
            refreshed = 0
            failed = 0
            rate_limited = 0
            
            for ticker in tickers:
                if not self.running:
                    break
                
                try:
                    result = generator.generate_signal(
                        ticker=ticker,
                        use_ensemble=True,
                        use_multi_timeframe=True
                    )
                    
                    if result and "error" not in result:
                        from src.web.signal_cache import set_cached_signal
                        set_cached_signal(ticker, result)
                        refreshed += 1
                        
                        # Adaptive delay based on priority and rate limits
                        delay = 1.0 if priority else 3.0
                        time.sleep(delay)
                    else:
                        failed += 1
                        error_msg = str(result.get('error', 'unknown')) if result else 'no result'
                        if 'rate limit' in error_msg.lower():
                            rate_limited += 1
                            # Longer delay on rate limit
                            time.sleep(5.0)
                        else:
                            time.sleep(1.0)
                            
                except Exception as e:
                    failed += 1
                    error_msg = str(e).lower()
                    if 'rate limit' in error_msg:
                        rate_limited += 1
                        logger.debug(f"[SignalRefresh] Rate limited for {ticker}, waiting...")
                        time.sleep(5.0)  # Wait longer on rate limit
                    else:
                        logger.debug(f"[SignalRefresh] Failed to refresh {ticker}: {e}")
                        time.sleep(1.0)
            
            if rate_limited > 0:
                logger.warning(f"[SignalRefresh] ⚠️ Rate limited for {rate_limited} signals. Consider connecting Upstox for unlimited data.")
            logger.info(f"[SignalRefresh] ✅ Refreshed {refreshed}/{len(tickers)} signals ({failed} failed, {rate_limited} rate limited)")
            
        except Exception as e:
            logger.error(f"[SignalRefresh] Error refreshing signals: {e}", exc_info=True)
    
    def refresh_now(self, tickers: Optional[List[str]] = None):
        """Manually trigger refresh for specific tickers"""
        self._refresh_signals(tickers, priority=True)


# Global instance
_signal_refresh_service: Optional[SignalRefreshService] = None

def get_signal_refresh_service() -> SignalRefreshService:
    """Get global signal refresh service instance"""
    global _signal_refresh_service
    if _signal_refresh_service is None:
        _signal_refresh_service = SignalRefreshService()
    return _signal_refresh_service
