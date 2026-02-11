"""
Market Hours Manager
Detects market status, trading sessions, and market holidays
"""
from __future__ import annotations

import logging
from typing import Dict, Optional
from datetime import datetime, time, timedelta
import pytz

logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Market hours (IST)
MARKET_OPEN_TIME = time(9, 15)  # 9:15 AM
MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM

# Pre-market hours
PRE_MARKET_START = time(9, 0)  # 9:00 AM
PRE_MARKET_END = time(9, 15)  # 9:15 AM

# Post-market hours
POST_MARKET_START = time(15, 30)  # 3:30 PM
POST_MARKET_END = time(16, 0)  # 4:00 PM


class MarketHoursManager:
    """
    Manages market hours detection and trading session status.
    """
    
    def __init__(self):
        self.ist = IST
        # Market holidays cache (would be populated from NSE/BSE holiday calendar)
        self._holidays_cache: set = set()
    
    def is_market_open(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if market is currently open.
        
        Args:
            dt: Datetime to check (default: now)
        
        Returns:
            True if market is open
        """
        if dt is None:
            dt = datetime.now(self.ist)
        elif dt.tzinfo is None:
            dt = self.ist.localize(dt)
        else:
            dt = dt.astimezone(self.ist)
        
        # Check if trading day
        if not self.is_trading_day(dt):
            return False
        
        # Check if within market hours
        current_time = dt.time()
        return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME
    
    def is_trading_day(self, dt: Optional[datetime] = None) -> bool:
        """
        Check if given date is a trading day (not weekend or holiday).
        
        Args:
            dt: Date to check (default: today)
        
        Returns:
            True if trading day
        """
        if dt is None:
            dt = datetime.now(self.ist)
        elif dt.tzinfo is None:
            dt = self.ist.localize(dt)
        else:
            dt = dt.astimezone(self.ist)
        
        # Check if weekend (Saturday = 5, Sunday = 6)
        weekday = dt.weekday()
        if weekday >= 5:  # Saturday or Sunday
            return False
        
        # Check if holiday (simplified - would need actual holiday calendar)
        date_str = dt.date().isoformat()
        if date_str in self._holidays_cache:
            return False
        
        return True
    
    def get_market_status(self, dt: Optional[datetime] = None) -> Dict:
        """
        Get current market status.
        
        Args:
            dt: Datetime to check (default: now)
        
        Returns:
            Dictionary with market status information
        """
        if dt is None:
            dt = datetime.now(self.ist)
        elif dt.tzinfo is None:
            dt = self.ist.localize(dt)
        else:
            dt = dt.astimezone(self.ist)
        
        current_time = dt.time()
        is_trading_day = self.is_trading_day(dt)
        
        if not is_trading_day:
            return {
                'status': 'CLOSED',
                'session': 'NON_TRADING_DAY',
                'is_open': False,
                'is_trading_day': False,
                'current_time': current_time.isoformat(),
                'date': dt.date().isoformat(),
                'next_open': self.get_next_market_open(dt)
            }
        
        if current_time < PRE_MARKET_START:
            return {
                'status': 'CLOSED',
                'session': 'PRE_MARKET',
                'is_open': False,
                'is_trading_day': True,
                'current_time': current_time.isoformat(),
                'date': dt.date().isoformat(),
                'next_open': dt.replace(
                    hour=MARKET_OPEN_TIME.hour,
                    minute=MARKET_OPEN_TIME.minute,
                    second=0,
                    microsecond=0
                ).isoformat()
            }
        
        if PRE_MARKET_START <= current_time < MARKET_OPEN_TIME:
            return {
                'status': 'PRE_MARKET',
                'session': 'PRE_MARKET',
                'is_open': False,
                'is_trading_day': True,
                'current_time': current_time.isoformat(),
                'date': dt.date().isoformat(),
                'opens_at': dt.replace(
                    hour=MARKET_OPEN_TIME.hour,
                    minute=MARKET_OPEN_TIME.minute,
                    second=0,
                    microsecond=0
                ).isoformat()
            }
        
        if MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME:
            return {
                'status': 'OPEN',
                'session': 'OPEN',
                'is_open': True,
                'is_trading_day': True,
                'current_time': current_time.isoformat(),
                'date': dt.date().isoformat(),
                'closes_at': dt.replace(
                    hour=MARKET_CLOSE_TIME.hour,
                    minute=MARKET_CLOSE_TIME.minute,
                    second=0,
                    microsecond=0
                ).isoformat()
            }
        
        if MARKET_CLOSE_TIME < current_time <= POST_MARKET_END:
            return {
                'status': 'POST_MARKET',
                'session': 'POST_MARKET',
                'is_open': False,
                'is_trading_day': True,
                'current_time': current_time.isoformat(),
                'date': dt.date().isoformat(),
                'next_open': self.get_next_market_open(dt)
            }
        
        # After post-market hours
        return {
            'status': 'CLOSED',
            'session': 'CLOSED',
            'is_open': False,
            'is_trading_day': True,
            'current_time': current_time.isoformat(),
            'date': dt.date().isoformat(),
            'next_open': self.get_next_market_open(dt)
        }
    
    def get_trading_session(self, dt: Optional[datetime] = None) -> str:
        """
        Get current trading session.
        
        Args:
            dt: Datetime to check (default: now)
        
        Returns:
            'PRE_MARKET', 'OPEN', 'POST_MARKET', or 'CLOSED'
        """
        status = self.get_market_status(dt)
        return status.get('session', 'CLOSED')
    
    def get_next_market_open(self, dt: Optional[datetime] = None) -> Optional[str]:
        """
        Get next market open time.
        
        Args:
            dt: Reference datetime (default: now)
        
        Returns:
            ISO format datetime string of next market open, or None if error
        """
        if dt is None:
            dt = datetime.now(self.ist)
        elif dt.tzinfo is None:
            dt = self.ist.localize(dt)
        else:
            dt = dt.astimezone(self.ist)
        
        # Start from today
        check_date = dt.date()
        max_days = 7  # Look ahead up to 7 days
        
        for _ in range(max_days):
            # Check if this date is a trading day
            check_dt = self.ist.localize(datetime.combine(check_date, MARKET_OPEN_TIME))
            
            if self.is_trading_day(check_dt):
                # Found next trading day
                return check_dt.isoformat()
            
            # Move to next day
            check_date += timedelta(days=1)
        
        return None
    
    def get_market_hours_today(self) -> Dict:
        """
        Get market hours for today.
        
        Returns:
            Dictionary with open and close times
        """
        today = datetime.now(self.ist).date()
        open_time = datetime.combine(today, MARKET_OPEN_TIME)
        close_time = datetime.combine(today, MARKET_CLOSE_TIME)
        
        return {
            'date': today.isoformat(),
            'open': self.ist.localize(open_time).isoformat(),
            'close': self.ist.localize(close_time).isoformat(),
            'is_trading_day': self.is_trading_day()
        }
    
    def add_holiday(self, date_str: str) -> None:
        """
        Add a market holiday to cache.
        
        Args:
            date_str: Date in YYYY-MM-DD format
        """
        self._holidays_cache.add(date_str)
        logger.info(f"Added holiday: {date_str}")
    
    def remove_holiday(self, date_str: str) -> None:
        """Remove a holiday from cache"""
        self._holidays_cache.discard(date_str)
    
    def get_holidays(self) -> list:
        """Get list of cached holidays"""
        return sorted(list(self._holidays_cache))


# Global instance
_market_hours_manager: Optional[MarketHoursManager] = None


def get_market_hours_manager() -> MarketHoursManager:
    """Get global market hours manager instance"""
    global _market_hours_manager
    if _market_hours_manager is None:
        _market_hours_manager = MarketHoursManager()
    return _market_hours_manager
