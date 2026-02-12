"""
Stock Universe Loader
Fetches all NSE/BSE stocks dynamically from Upstox instrument master or NSE API
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
import requests

from src.web.instrument_master import get_instrument_master

logger = logging.getLogger(__name__)

# Cache settings
CACHE_DIR = Path('data/stock_universe')
CACHE_EXPIRY_HOURS = 24  # Refresh daily


class StockUniverse:
    """
    Manages complete stock universe for Indian markets.
    Fetches from Upstox instrument master or NSE API.
    """
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.instrument_master = get_instrument_master()
        self._universe_cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def _get_cache_path(self) -> Path:
        """Get cache file path for stock universe"""
        return self.cache_dir / "universe.csv"
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return False
        
        try:
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age = datetime.now() - mtime
            return age < timedelta(hours=CACHE_EXPIRY_HOURS)
        except Exception:
            return False
    
    def _load_cache(self) -> Optional[pd.DataFrame]:
        """Load stock universe from cache"""
        cache_path = self._get_cache_path()
        if cache_path.exists():
            try:
                df = pd.read_csv(cache_path)
                logger.info(f"Loaded {len(df)} stocks from cache")
                return df
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
        return None
    
    def _save_cache(self, df: pd.DataFrame) -> None:
        """Save stock universe to cache"""
        cache_path = self._get_cache_path()
        try:
            df.to_csv(cache_path, index=False)
            logger.info(f"Cached {len(df)} stocks to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _fetch_from_upstox(self) -> Optional[pd.DataFrame]:
        """
        Fetch stock universe from Upstox instrument master.
        Returns DataFrame with columns: ticker, exchange, name, instrument_key, etc.
        """
        try:
            # Try to get instruments from instrument master
            nse_df = self.instrument_master._ensure_instruments('NSE_EQ')
            bse_df = self.instrument_master._ensure_instruments('BSE_EQ')
            
            all_stocks = []
            
            def _sym(row):
                return str(row.get('tradingsymbol') or row.get('trading_symbol') or row.get('symbol') or '').strip()

            # Process NSE stocks
            if nse_df is not None and not nse_df.empty:
                for _, row in nse_df.iterrows():
                    tradingsymbol = _sym(row)
                    if tradingsymbol:
                        ticker = f"{tradingsymbol}.NS"
                        all_stocks.append({
                            'ticker': ticker,
                            'exchange': 'NSE',
                            'name': row.get('name', tradingsymbol),
                            'tradingsymbol': tradingsymbol,
                            'instrument_key': row.get('instrument_key') or row.get('instrument_token', ''),
                            'isin': row.get('isin', ''),
                        })
            
            # Process BSE stocks
            if bse_df is not None and not bse_df.empty:
                for _, row in bse_df.iterrows():
                    tradingsymbol = _sym(row)
                    if tradingsymbol:
                        ticker = f"{tradingsymbol}.BO"
                        all_stocks.append({
                            'ticker': ticker,
                            'exchange': 'BSE',
                            'name': row.get('name', tradingsymbol),
                            'tradingsymbol': tradingsymbol,
                            'instrument_key': row.get('instrument_key') or row.get('instrument_token', ''),
                            'isin': row.get('isin', ''),
                        })
            
            if all_stocks:
                df = pd.DataFrame(all_stocks)
                logger.info(f"Fetched {len(df)} stocks from Upstox instrument master")
                return df
            
        except Exception as e:
            logger.warning(f"Failed to fetch from Upstox: {e}")
        
        return None
    
    def _fetch_from_nse_api(self) -> Optional[pd.DataFrame]:
        """
        Fetch stock universe from NSE API (fallback).
        Note: NSE API may have rate limits.
        """
        try:
            # NSE equity list endpoint
            url = "https://www.nseindia.com/api/equity-stockIndices?index=SECURITIES%20IN%20F%26O"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                stocks = []
                
                if 'data' in data:
                    for item in data['data']:
                        symbol = item.get('symbol', '')
                        if symbol:
                            ticker = f"{symbol}.NS"
                            stocks.append({
                                'ticker': ticker,
                                'exchange': 'NSE',
                                'name': item.get('meta', {}).get('companyName', symbol),
                                'tradingsymbol': symbol,
                                'instrument_key': '',  # Will need to resolve via instrument master
                                'isin': item.get('meta', {}).get('isin', ''),
                            })
                
                if stocks:
                    df = pd.DataFrame(stocks)
                    logger.info(f"Fetched {len(df)} stocks from NSE API")
                    return df
        
        except Exception as e:
            logger.debug(f"NSE API fetch failed: {e}")
        
        return None
    
    def _build_universe(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Build stock universe from available sources.
        
        Args:
            force_refresh: Force refresh even if cache is valid
        
        Returns:
            DataFrame with stock universe
        """
        # Check cache first
        if not force_refresh and self._is_cache_valid():
            cached = self._load_cache()
            if cached is not None:
                self._universe_cache = cached
                self._cache_timestamp = datetime.now()
                return cached
        
        # Try Upstox first
        df = self._fetch_from_upstox()
        
        # Fallback to NSE API
        if df is None or df.empty:
            logger.info("Upstox fetch failed, trying NSE API...")
            df = self._fetch_from_nse_api()
        
        # If still no data, use fallback list
        if df is None or df.empty:
            logger.warning("All sources failed, using fallback list")
            from src.web.data.all_stocks_list import ALL_STOCKS_FALLBACK
            df = pd.DataFrame({
                'ticker': ALL_STOCKS_FALLBACK,
                'exchange': ['NSE' if t.endswith('.NS') else 'BSE' for t in ALL_STOCKS_FALLBACK],
                'name': [t.replace('.NS', '').replace('.BO', '') for t in ALL_STOCKS_FALLBACK],
                'tradingsymbol': [t.replace('.NS', '').replace('.BO', '') for t in ALL_STOCKS_FALLBACK],
                'instrument_key': [''] * len(ALL_STOCKS_FALLBACK),
                'isin': [''] * len(ALL_STOCKS_FALLBACK),
            })
        
        # Save to cache
        if df is not None and not df.empty:
            self._save_cache(df)
            self._universe_cache = df
            self._cache_timestamp = datetime.now()
        
        return df
    
    def get_all_stocks(self, force_refresh: bool = False) -> List[str]:
        """
        Get list of all stock tickers.
        
        Args:
            force_refresh: Force refresh from source
        
        Returns:
            List of Yahoo Finance tickers (e.g., ['RELIANCE.NS', 'TCS.NS', ...])
        """
        df = self._build_universe(force_refresh)
        if df is not None and 'ticker' in df.columns:
            return df['ticker'].tolist()
        return []
    
    def get_stocks_by_exchange(self, exchange: str) -> List[str]:
        """
        Get stocks filtered by exchange.
        
        Args:
            exchange: 'NSE' or 'BSE'
        
        Returns:
            List of tickers
        """
        df = self._build_universe()
        if df is not None and 'exchange' in df.columns:
            filtered = df[df['exchange'].str.upper() == exchange.upper()]
            return filtered['ticker'].tolist() if 'ticker' in filtered.columns else []
        return []
    
    def get_stocks_by_market_cap(
        self,
        min_mcap: Optional[float] = None,
        max_mcap: Optional[float] = None
    ) -> List[str]:
        """
        Get stocks filtered by market cap.
        
        Note: Market cap data may not be available in instrument master.
        This is a placeholder for future enhancement.
        
        Args:
            min_mcap: Minimum market cap (in crores)
            max_mcap: Maximum market cap (in crores)
        
        Returns:
            List of tickers matching criteria
        """
        # For now, return all stocks (market cap filtering requires additional data source)
        logger.debug("Market cap filtering not yet implemented, returning all stocks")
        return self.get_all_stocks()
    
    def get_stocks_by_sector(self, sector: str) -> List[str]:
        """
        Get stocks filtered by sector.
        
        Note: Sector data may not be available in instrument master.
        This is a placeholder for future enhancement.
        
        Args:
            sector: Sector name (e.g., 'BANKING', 'IT', 'PHARMA')
        
        Returns:
            List of tickers in the specified sector
        """
        # For now, return all stocks (sector filtering requires additional data source)
        logger.debug(f"Sector filtering not yet implemented, returning all stocks")
        return self.get_all_stocks()
    
    def get_stocks_by_liquidity(self, min_volume: Optional[float] = None) -> List[str]:
        """
        Get stocks filtered by liquidity (average daily volume).
        
        Note: Volume data requires historical data analysis.
        This is a placeholder for future enhancement.
        
        Args:
            min_volume: Minimum average daily volume
        
        Returns:
            List of tickers matching liquidity criteria
        """
        # For now, return all stocks (liquidity filtering requires historical data)
        logger.debug("Liquidity filtering not yet implemented, returning all stocks")
        return self.get_all_stocks()
    
    def refresh_universe(self) -> bool:
        """
        Force refresh stock universe from source.
        
        Returns:
            True if refresh successful
        """
        try:
            self._build_universe(force_refresh=True)
            logger.info("Stock universe refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh stock universe: {e}")
            return False
    
    def get_stocks_page(
        self,
        exchange: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> Dict:
        """
        Get paginated list of stocks for API/UI.
        
        Args:
            exchange: 'NSE' or 'BSE' or None for all
            limit: max items to return (capped at 2000)
            offset: skip this many items
            search: optional substring filter on ticker/name/tradingsymbol
        
        Returns:
            {"stocks": [{"ticker", "exchange", "name", "tradingsymbol", ...}], "total": int}
        """
        df = self._build_universe()
        if df is None or df.empty:
            return {"stocks": [], "total": 0}
        if exchange:
            df = df[df["exchange"].str.upper() == exchange.upper()].copy()
        if search:
            s = search.strip().upper()
            if s:
                def matches(r):
                    combined = (str(r.get("ticker", "")) + " " + str(r.get("name", "")) + " " + str(r.get("tradingsymbol", ""))).upper()
                    return s in combined
                df = df[df.apply(matches, axis=1)]
        total = len(df)
        limit = min(max(1, limit), 2000)
        df = df.iloc[offset : offset + limit]
        stocks = df.to_dict("records")
        return {"stocks": stocks, "total": total}

    def get_universe_info(self) -> Dict:
        """
        Get information about the stock universe.
        
        Returns:
            Dictionary with universe statistics
        """
        df = self._build_universe()
        if df is None or df.empty:
            return {
                'total_stocks': 0,
                'nse_stocks': 0,
                'bse_stocks': 0,
                'cache_age_hours': None,
                'last_refresh': None
            }
        
        nse_count = len(df[df['exchange'] == 'NSE']) if 'exchange' in df.columns else 0
        bse_count = len(df[df['exchange'] == 'BSE']) if 'exchange' in df.columns else 0
        
        cache_age = None
        if self._cache_timestamp:
            age = datetime.now() - self._cache_timestamp
            cache_age = age.total_seconds() / 3600
        
        return {
            'total_stocks': len(df),
            'nse_stocks': nse_count,
            'bse_stocks': bse_count,
            'cache_age_hours': cache_age,
            'last_refresh': self._cache_timestamp.isoformat() if self._cache_timestamp else None
        }


# Global instance
_stock_universe: Optional[StockUniverse] = None


def get_stock_universe() -> StockUniverse:
    """Get global stock universe instance"""
    global _stock_universe
    if _stock_universe is None:
        _stock_universe = StockUniverse()
    return _stock_universe
