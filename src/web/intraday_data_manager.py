"""
Intraday Data Manager
Manages intraday data fetching from multiple sources (Upstox, NSE, Yahoo Finance)
with caching and market hours awareness.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import pytz

from src.research.data import download_yahoo_ohlcv, OHLCV

logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Market hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def _is_market_hours(dt: datetime) -> bool:
    """Check if datetime is during market hours (9:15 AM - 3:30 PM IST)"""
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    elif dt.tzinfo != IST:
        dt = dt.astimezone(IST)
    
    hour = dt.hour
    minute = dt.minute
    
    # Before market open
    if hour < MARKET_OPEN_HOUR or (hour == MARKET_OPEN_HOUR and minute < MARKET_OPEN_MINUTE):
        return False
    
    # After market close
    if hour > MARKET_CLOSE_HOUR or (hour == MARKET_CLOSE_HOUR and minute > MARKET_CLOSE_MINUTE):
        return False
    
    return True


def _get_market_hours_range(start_date: datetime, end_date: datetime, timeframe: str) -> tuple[datetime, datetime]:
    """
    Adjust date range to market hours for intraday data.
    For intraday, we only want data during trading hours.
    """
    if start_date.tzinfo is None:
        start_date = IST.localize(start_date)
    if end_date.tzinfo is None:
        end_date = IST.localize(end_date)
    
    # Set start to market open if before
    if start_date.hour < MARKET_OPEN_HOUR or (start_date.hour == MARKET_OPEN_HOUR and start_date.minute < MARKET_OPEN_MINUTE):
        start_date = start_date.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    
    # Set end to market close if after
    if end_date.hour > MARKET_CLOSE_HOUR or (end_date.hour == MARKET_CLOSE_HOUR and end_date.minute > MARKET_CLOSE_MINUTE):
        end_date = end_date.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)
    
    return start_date, end_date


class IntradayDataManager:
    """
    Manages intraday data fetching from multiple sources with caching.
    Priority: Upstox API > NSE API > Yahoo Finance
    """
    
    def __init__(self, upstox_client=None, cache_dir: Optional[Path] = None):
        """
        Initialize intraday data manager.
        
        Args:
            upstox_client: Optional UpstoxAPI client (if connected)
            cache_dir: Directory for caching intraday data
        """
        self.upstox_client = upstox_client
        self.cache_dir = cache_dir or Path("cache/intraday")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # TTL for different timeframes (in minutes)
        self.cache_ttl = {
            '5m': 10,   # 5min bars expire after 10 minutes
            '15m': 30,  # 15min bars expire after 30 minutes
            '1h': 120,  # Hourly bars expire after 2 hours
            '1d': 1440, # Daily bars expire after 24 hours
        }

    def set_upstox_client(self, upstox_client) -> None:
        """Wire Upstox client when available (e.g. after connection). Enables real intraday data during market hours."""
        self.upstox_client = upstox_client
    
    def get_intraday_data(
        self,
        ticker: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        days_back: int = 20,
        use_cache: bool = True,
    ) -> Optional[OHLCV]:
        """
        Get intraday data for a ticker.
        
        Args:
            ticker: Stock ticker (e.g., 'RELIANCE.NS', '^NSEI')
            timeframe: '5m', '15m', '1h', '1d'
            start_time: Start datetime (defaults to days_back days ago)
            end_time: End datetime (defaults to now)
            days_back: Number of days to look back if start_time not provided
            use_cache: Whether to use cached data
        
        Returns:
            OHLCV dataclass or None if error
        """
        timeframe = timeframe.lower()
        valid_timeframes = {'5m', '15m', '1h', '1d'}
        if timeframe not in valid_timeframes:
            raise ValueError(f"Invalid timeframe: {timeframe}. Must be one of {valid_timeframes}")
        
        # Set default times
        now = datetime.now(IST)
        if end_time is None:
            end_time = now
        elif end_time.tzinfo is None:
            end_time = IST.localize(end_time)
        else:
            end_time = end_time.astimezone(IST)
        
        if start_time is None:
            # For intraday, limit lookback based on timeframe
            max_days = {
                '5m': 20,   # 20 days of 5min bars
                '15m': 30,  # 30 days of 15min bars
                '1h': 60,   # 60 days of hourly bars
                '1d': 365,  # 1 year of daily bars
            }
            days_back = min(days_back, max_days.get(timeframe, 20))
            start_time = end_time - timedelta(days=days_back)
        elif start_time.tzinfo is None:
            start_time = IST.localize(start_time)
        else:
            start_time = start_time.astimezone(IST)
        
        # Adjust to market hours for intraday
        if timeframe != '1d':
            start_time, end_time = _get_market_hours_range(start_time, end_time, timeframe)
        
        # Check cache
        cache_path = self._get_cache_path(ticker, timeframe, start_time, end_time)
        if use_cache and cache_path.exists():
            cache_age = (now - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() / 60
            ttl = self.cache_ttl.get(timeframe, 60)
            
            if cache_age < ttl:
                try:
                    cached = self._load_cache(cache_path)
                    logger.info(f"Loaded cached intraday data for {ticker} ({timeframe})")
                    return cached
                except Exception as e:
                    logger.warning(f"Failed to load cache: {e}")
        
        # Try Upstox first (if available)
        if self.upstox_client and self.upstox_client.access_token:
            try:
                data = self._fetch_from_upstox(ticker, timeframe, start_time, end_time)
                if data:
                    self._save_cache(data, cache_path)
                    return data
            except Exception as e:
                logger.debug(f"Upstox fetch failed for {ticker}: {e}")
        
        # Fallback to Yahoo Finance
        try:
            start_str = start_time.strftime('%Y-%m-%d')
            end_str = end_time.strftime('%Y-%m-%d')
            
            data = download_yahoo_ohlcv(
                ticker=ticker,
                start=start_str,
                end=end_str,
                interval=timeframe,
                cache_path=cache_path,
                refresh=not use_cache,
            )
            
            if data:
                self._save_cache(data, cache_path)
                return data
        except Exception as e:
            logger.error(f"Failed to fetch intraday data for {ticker} ({timeframe}): {e}")
            return None
        
        return None
    
    def _fetch_from_upstox(
        self,
        ticker: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Optional[OHLCV]:
        """
        Fetch historical intraday data from Upstox API.
        When this returns None, get_intraday_data falls back to Yahoo Finance (same interval).
        """
        try:
            from src.web.instrument_master import get_instrument_master
            
            inst_master = get_instrument_master()
            inst_key = inst_master.get_instrument_key(ticker)
            if not inst_key:
                logger.debug(f"No instrument key for {ticker}")
                return None
            # Upstox historical candle endpoint: GET /v2/historical-candle/{instrument_key}/{interval}/{to}
            # interval: 30minute, 15minute, 5minute, 1day etc.; from & to as date strings
            from urllib.parse import quote
            interval_map = {"5m": "5minute", "15m": "15minute", "1h": "30minute", "1d": "1day"}
            upstox_interval = interval_map.get(timeframe, "5minute")
            to_ts = end_time.strftime("%Y-%m-%d")
            from_ts = start_time.strftime("%Y-%m-%d")
            inst_key_enc = quote(inst_key, safe="")
            url = (
                f"https://api.upstox.com/v2/historical-candle/{inst_key_enc}/{upstox_interval}/{to_ts}"
            )
            params = {"from": from_ts}
            resp = self.upstox_client.session.get(
                url, params=params, timeout=30
            )
            if resp.status_code != 200:
                logger.debug(f"Upstox historical returned {resp.status_code} for {ticker}")
                return None
            data = resp.json()
            candles = data.get("data", {}).get("candles") if isinstance(data, dict) else None
            if not candles or not isinstance(candles, list):
                return None
            import pandas as pd
            rows = []
            for c in candles:
                if isinstance(c, (list, tuple)) and len(c) >= 5:
                    # Typical: [timestamp, open, high, low, close, volume]
                    ts = c[0]; o, h, l, cl, v = float(c[1]), float(c[2]), float(c[3]), float(c[4]), float(c[5]) if len(c) > 5 else 0
                    rows.append({"open": o, "high": h, "low": l, "close": cl, "volume": v, "date": pd.Timestamp(ts, unit="s", tz=IST)})
                elif isinstance(c, dict):
                    rows.append({
                        "open": float(c.get("open", 0)),
                        "high": float(c.get("high", 0)),
                        "low": float(c.get("low", 0)),
                        "close": float(c.get("close", 0)),
                        "volume": float(c.get("volume", 0)),
                        "date": pd.to_datetime(c.get("timestamp", c.get("date")), utc=True).tz_convert(IST),
                    })
            if not rows:
                return None
            df = pd.DataFrame(rows).set_index("date").sort_index()
            df = df[["open", "high", "low", "close", "volume"]]
            df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
            return OHLCV(df=df)
        except Exception as e:
            logger.debug(f"Upstox historical fetch failed for {ticker}: {e}")
            return None
    
    def _get_cache_path(
        self,
        ticker: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime,
    ) -> Path:
        """Generate cache file path for intraday data"""
        safe_ticker = ticker.replace('^', '').replace('.NS', '').replace('.BO', '').replace(':', '_')
        start_str = start_time.strftime('%Y%m%d')
        end_str = end_time.strftime('%Y%m%d')
        filename = f"{safe_ticker}_{timeframe}_{start_str}_{end_str}.csv"
        return self.cache_dir / filename
    
    def _load_cache(self, cache_path: Path) -> OHLCV:
        """Load cached intraday data"""
        df = pd.read_csv(cache_path, parse_dates=True, index_col=0)
        df.index = pd.to_datetime(df.index)
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize(IST)
        return OHLCV(df=df)
    
    def _save_cache(self, ohlcv: OHLCV, cache_path: Path) -> None:
        """Save intraday data to cache"""
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        df = ohlcv.df.copy()
        if df.index.tzinfo is not None:
            df.index = df.index.tz_convert(IST)
        df.insert(0, "date", df.index)
        df.to_csv(cache_path, index=False)
    
    def clear_cache(self, ticker: Optional[str] = None, timeframe: Optional[str] = None) -> None:
        """
        Clear cached intraday data.
        
        Args:
            ticker: If provided, clear cache for this ticker only
            timeframe: If provided, clear cache for this timeframe only
        """
        if ticker:
            safe_ticker = ticker.replace('^', '').replace('.NS', '').replace('.BO', '').replace(':', '_')
            pattern = f"{safe_ticker}_*.csv" if not timeframe else f"{safe_ticker}_{timeframe}_*.csv"
        elif timeframe:
            pattern = f"*_{timeframe}_*.csv"
        else:
            # Clear all
            for f in self.cache_dir.glob("*.csv"):
                f.unlink()
            return
        
        for f in self.cache_dir.glob(pattern):
            f.unlink()
        logger.info(f"Cleared cache for {ticker or 'all'} ({timeframe or 'all timeframes'})")


def get_intraday_data_manager(upstox_client=None) -> IntradayDataManager:
    """Get singleton instance of IntradayDataManager"""
    if not hasattr(get_intraday_data_manager, '_instance'):
        get_intraday_data_manager._instance = IntradayDataManager(upstox_client=upstox_client)
    return get_intraday_data_manager._instance
