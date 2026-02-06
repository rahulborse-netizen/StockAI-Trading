"""
Portfolio Recorder
Phase 2.4: Background task to record portfolio snapshots
"""
import logging
import threading
import time
from datetime import datetime, time as dt_time
from typing import Optional
from src.web.holdings_db import get_holdings_db

logger = logging.getLogger(__name__)


class PortfolioRecorder:
    """Records portfolio snapshots at regular intervals"""
    
    def __init__(self, interval_minutes: int = 60):
        self.interval_minutes = interval_minutes
        self.running = False
        self.thread = None
        self.stop_flag = threading.Event()
        
    def start_recording(self):
        """Start background recording"""
        if self.running:
            logger.warning("Portfolio recorder already running")
            return
            
        self.running = True
        self.stop_flag.clear()
        self.thread = threading.Thread(target=self._recording_loop, daemon=True)
        self.thread.start()
        logger.info(f"✅ Portfolio recorder started (interval: {self.interval_minutes} min)")
    
    def stop_recording(self):
        """Stop background recording"""
        self.running = False
        self.stop_flag.set()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 Portfolio recorder stopped")
    
    def _recording_loop(self):
        """Background recording loop"""
        while not self.stop_flag.is_set():
            try:
                self._record_snapshot()
            except Exception as e:
                logger.error(f"Error in portfolio recording: {e}")
            
            # Wait for next interval
            self.stop_flag.wait(self.interval_minutes * 60)
    
    def _record_snapshot(self):
        """Record a portfolio snapshot"""
        try:
            # TODO: Get actual holdings from position manager
            # For now, this is a placeholder
            logger.debug("📊 Recording portfolio snapshot...")
            
        except Exception as e:
            logger.error(f"Error recording snapshot: {e}")
    
    def record_end_of_day_snapshot(self):
        """Record snapshot at market close (3:30 PM IST)"""
        try:
            now = datetime.now()
            market_close = dt_time(15, 30)  # 3:30 PM
            
            if now.time() >= market_close:
                logger.info("📊 Recording end-of-day portfolio snapshot...")
                self._record_snapshot()
            
        except Exception as e:
            logger.error(f"Error recording EOD snapshot: {e}")


# Global singleton
_portfolio_recorder = None


def get_portfolio_recorder() -> PortfolioRecorder:
    """Get global portfolio recorder instance"""
    global _portfolio_recorder
    if _portfolio_recorder is None:
        _portfolio_recorder = PortfolioRecorder()
    return _portfolio_recorder
