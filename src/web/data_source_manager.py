"""
Unified Data Source Manager
Manages multiple data sources - Upstox prioritized, Yahoo fallback
"""
import os
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


def _get_yahoo_session(verify_ssl: bool = True):
    """Get requests session for yfinance - SSL workaround for Windows curl 60."""
    try:
        import requests
        s = requests.Session()
        if verify_ssl:
            try:
                import certifi
                s.verify = certifi.where()
            except ImportError:
                pass
        else:
            s.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return s
    except Exception:
        return None

# Map index names to Yahoo tickers - never append .NS to these
_YAHOO_INDEX_MAP = {
    'nifty': '^NSEI',
    'nifty50': '^NSEI',
    'banknifty': '^NSEBANK',
    'sensex': '^BSESN',
    'vix': '^INDIAVIX',
    'indiavix': '^INDIAVIX',
    'niftysmallcap': '^CNXSMALLCAP',
    'nifty100': '^CNX100',
    'nifty500': '^CNX500',
    'niftyit': '^CNXIT',
    'niftyfmcg': '^CNXFMCG',
    'niftypharma': '^CNXPHARMA',
    'niftyauto': '^CNXAUTO',
    'niftymetal': '^CNXMETAL',
    'niftyenergy': '^CNXENERGY',
    'niftyrealty': '^CNXREALTY',
    'niftypsu': '^CNXPSU',
    'niftymidcap': '^CNXMID',
}


def _yahoo_ticker(symbol: str) -> str:
    """Return correct Yahoo ticker. Indices map to ^NSEI etc; stocks get .NS."""
    s = str(symbol or '').strip().lower()
    if not s:
        return s
    if s.startswith('^'):
        return symbol.strip()
    mapped = _YAHOO_INDEX_MAP.get(s)
    if mapped:
        return mapped
    s_orig = str(symbol or '').strip()
    if '.' in s_orig:
        return s_orig
    return f"{s_orig}.NS"


class DataSource(Enum):
    """Available data sources - Upstox prioritized"""
    UPSTOX = 1  # Primary when connected - no blocking, no SSL issues
    YAHOO_FINANCE = 2  # Fallback when Upstox not connected
    NSE = 3  # Last resort - often blocked, rarely works


class DataSourceManager:
    """
    Unified interface for multiple data sources
    Implements priority-based fetching with automatic failover
    """
    
    def __init__(self):
        self.sources = []
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize data sources. Upstox first (when connected), then Yahoo. NSE disabled (often blocked)."""
        # Upstox - primary when connected
        self.sources.append({
            'source': DataSource.UPSTOX,
            'client': None,  # Lazy: get via _get_upstox_client()
            'available': True,
            'priority': 1
        })
        # Yahoo Finance - fallback when Upstox not connected
        try:
            import yfinance as yf
            self.sources.append({
                'source': DataSource.YAHOO_FINANCE,
                'client': yf,
                'available': True,
                'priority': 2
            })
            logger.info("Yahoo Finance data source initialized (fallback)")
        except Exception as e:
            logger.warning(f"Could not initialize Yahoo Finance source: {e}")
        # NSE - disabled by default (often blocked); enable via UPSTOX_USE_NSE=1 if needed
        if os.environ.get("UPSTOX_USE_NSE", "").strip() == "1":
            try:
                from src.web.nse_data_client import get_nse_client
                self.sources.append({
                    'source': DataSource.NSE,
                    'client': get_nse_client(),
                    'available': True,
                    'priority': 3
                })
                logger.info("NSE data source initialized (optional)")
            except Exception as e:
                logger.warning(f"Could not initialize NSE source: {e}")
        self.sources.sort(key=lambda x: x['priority'])

    def _get_upstox_client(self):
        """Get Upstox client lazily (requires Flask request context for session)."""
        try:
            from src.web.upstox_connection import connection_manager
            client = connection_manager.get_client()
            if client and client.access_token:
                return client
        except Exception:
            pass
        return None
    
    def get_quote(self, symbol: str, use_cache: bool = True) -> Tuple[Optional[Dict], DataSource]:
        """
        Get quote for a symbol from best available source
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'RELIANCE.NS')
            use_cache: Whether to use cached data if available
        
        Returns:
            Tuple of (quote_data, source_used) or (None, None) if all sources fail
        """
        # Normalize symbol (remove .NS suffix for NSE)
        nse_symbol = symbol.replace('.NS', '').replace('.BO', '')
        
        for source_info in self.sources:
            if not source_info['available']:
                continue
            
            try:
                source = source_info['source']
                client = source_info['client']
                
                if source == DataSource.NSE:
                    quote = client.get_quote(nse_symbol)
                    if quote and quote.get('current_price', 0) > 0:
                        logger.debug(f"Got quote for {symbol} from NSE")
                        return quote, DataSource.NSE
                
                elif source == DataSource.UPSTOX:
                    # Try Upstox Market Data API (lazy client - needs request context)
                    upstox_client = self._get_upstox_client()
                    if not upstox_client or not upstox_client.access_token:
                        continue
                    from src.web.market_data import MarketDataClient
                    from src.web.instrument_master import get_instrument_master
                    
                    market_client = MarketDataClient(upstox_client.access_token)
                    instrument_master = get_instrument_master()
                    inst_key = instrument_master.get_instrument_key(symbol)
                    
                    if inst_key:
                        quote = market_client.get_quote(inst_key, use_cache=use_cache)
                        if quote:
                            parsed = market_client.parse_quote(quote)
                            if parsed.get('price', 0) > 0:
                                logger.debug(f"Got quote for {symbol} from Upstox")
                                parsed['source'] = 'upstox'
                                return parsed, DataSource.UPSTOX
                
                elif source == DataSource.YAHOO_FINANCE:
                    ticker = _yahoo_ticker(symbol)
                    session = _get_yahoo_session()
                    stock = client.Ticker(ticker, session=session) if session else client.Ticker(ticker)
                    hist = stock.history(period="1d", interval="1m")
                    if hist is None or hist.empty:
                        continue
                    latest = hist.iloc[-1]
                    prev_close = stock.history(period="2d", interval="1d")
                    prev_close_price = float(prev_close.iloc[-2]['Close']) if prev_close is not None and not prev_close.empty and len(prev_close) >= 2 else float(latest['Close'])
                    current_price = float(latest['Close'])
                    change = current_price - prev_close_price
                    change_pct = (change / prev_close_price * 100) if prev_close_price > 0 else 0
                    quote = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'close': prev_close_price,
                        'volume': int(latest['Volume']),
                        'change': change,
                        'change_pct': change_pct,
                        'timestamp': datetime.now().isoformat(),
                        'source': 'yahoo_finance'
                    }
                    logger.debug(f"Got quote for {symbol} from Yahoo Finance")
                    return quote, DataSource.YAHOO_FINANCE
                
            except Exception as e:
                logger.debug(f"Source {source_info['source']} failed for {symbol}: {e}")
                continue
        
        logger.warning(f"All data sources failed for {symbol}")
        return None, None
    
    def get_index_data(self, index_name: str) -> Tuple[Optional[Dict], DataSource]:
        """
        Get index data from best available source
        
        Args:
            index_name: Index name (e.g., 'nifty', 'banknifty', 'sensex')
        
        Returns:
            Tuple of (index_data, source_used) or (None, None) if all sources fail
        """
        # Try NSE first
        for source_info in self.sources:
            if not source_info['available']:
                continue
            
            try:
                source = source_info['source']
                client = source_info['client']
                
                if source == DataSource.NSE:
                    index_data = client.get_index_data(index_name)
                    if index_data and index_data.get('value', 0) > 0:
                        logger.debug(f"Got index data for {index_name} from NSE")
                        return index_data, DataSource.NSE
                
                elif source == DataSource.UPSTOX:
                    # Try Upstox for indices (lazy client)
                    upstox_client = self._get_upstox_client()
                    if not upstox_client or not upstox_client.access_token:
                        continue
                    from src.web.market_data import MarketDataClient
                    
                    market_client = MarketDataClient(upstox_client.access_token)
                    
                    # Map index names to Upstox keys (all major + sectoral indices)
                    index_map = {
                        'nifty': 'NSE_INDEX|Nifty 50',
                        'nifty50': 'NSE_INDEX|Nifty 50',
                        'banknifty': 'NSE_INDEX|Nifty Bank',
                        'sensex': 'BSE_INDEX|SENSEX',
                        'vix': 'NSE_INDEX|India VIX',
                        'indiavix': 'NSE_INDEX|India VIX',
                        'niftyit': 'NSE_INDEX|Nifty IT',
                        'niftyfmcg': 'NSE_INDEX|Nifty FMCG',
                        'niftypharma': 'NSE_INDEX|Nifty Pharma',
                        'niftyauto': 'NSE_INDEX|Nifty Auto',
                        'niftymetal': 'NSE_INDEX|Nifty Metal',
                        'niftyenergy': 'NSE_INDEX|Nifty Energy',
                        'niftyrealty': 'NSE_INDEX|Nifty Realty',
                        'niftypsu': 'NSE_INDEX|Nifty PSU Bank',
                        'niftymidcap': 'NSE_INDEX|Nifty Midcap 100',
                        'niftysmallcap': 'NSE_INDEX|Nifty Smallcap 100',
                    }
                    
                    upstox_key = index_map.get(index_name.lower())
                    if upstox_key:
                        quote = market_client.get_quote(upstox_key, use_cache=True)
                        if quote:
                            parsed = market_client.parse_quote(quote)
                            if parsed.get('price', 0) > 0:
                                parsed['value'] = parsed.get('price', 0)  # App expects 'value'
                                parsed['index_name'] = index_name
                                parsed['source'] = 'upstox'
                                logger.debug(f"Got index data for {index_name} from Upstox")
                                return parsed, DataSource.UPSTOX
                
                elif source == DataSource.YAHOO_FINANCE:
                    ticker_map = {
                        'nifty': '^NSEI',
                        'nifty50': '^NSEI',
                        'banknifty': '^NSEBANK',
                        'sensex': '^BSESN',
                        'vix': '^INDIAVIX',
                        'indiavix': '^INDIAVIX'
                    }
                    
                    ticker = ticker_map.get(index_name.lower())
                    if ticker:
                        session = _get_yahoo_session()
                        stock = client.Ticker(ticker, session=session) if session else client.Ticker(ticker)
                        hist = stock.history(period="2d", interval="1d")
                        
                        if not hist.empty and len(hist) >= 1:
                            latest = hist.iloc[-1]
                            current_value = float(latest['Close'])
                            
                            if len(hist) >= 2:
                                prev_close = float(hist.iloc[-2]['Close'])
                            else:
                                prev_close = current_value
                            
                            change = current_value - prev_close
                            change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                            
                            index_data = {
                                'index_name': index_name,
                                'value': current_value,
                                'open': float(latest['Open']),
                                'high': float(latest['High']),
                                'low': float(latest['Low']),
                                'close': prev_close,
                                'change': change,
                                'change_pct': change_pct,
                                'timestamp': datetime.now().isoformat(),
                                'source': 'yahoo_finance'
                            }
                            logger.debug(f"Got index data for {index_name} from Yahoo Finance")
                            return index_data, DataSource.YAHOO_FINANCE
                
            except Exception as e:
                logger.debug(f"Source {source_info['source']} failed for index {index_name}: {e}")
                continue
        
        logger.warning(f"All data sources failed for index {index_name}")
        return None, None
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str, instrument_key_override: Optional[str] = None) -> Tuple[Optional[List[Dict]], DataSource, Optional[str]]:
        """
        Get historical data from best available source
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            instrument_key_override: Optional Upstox instrument_key (e.g. from holdings) - bypasses instrument master lookup
        
        Returns:
            Tuple of (historical_data, source_used, error_hint) or (None, None, hint) if all sources fail
        """
        last_hint: Optional[str] = "Historical data unavailable for this ticker"
        # Try Upstox first (when connected) - no SSL/blocking issues
        upstox_client = self._get_upstox_client()
        if upstox_client and upstox_client.access_token:
            try:
                from urllib.parse import quote
                inst_key = instrument_key_override
                if not inst_key:
                    from src.web.instrument_master import get_instrument_master
                    inst_master = get_instrument_master()
                    inst_key = inst_master.get_instrument_key(symbol)
                if inst_key:
                    inst_key_enc = quote(inst_key, safe="")
                    # Upstox API: interval must be 'day' not '1day'; path is .../interval/to_date/from_date
                    url = f"https://api.upstox.com/v2/historical-candle/{inst_key_enc}/day/{end_date}/{start_date}"
                    resp = upstox_client.session.get(url, timeout=30)
                    if resp.status_code == 200:
                        data = resp.json()
                        candles = data.get("data", {}).get("candles") if isinstance(data, dict) else None
                        if candles and isinstance(candles, list):
                            records = []
                            for c in candles:
                                if isinstance(c, (list, tuple)) and len(c) >= 5:
                                    ts, o, h, l, cl = c[0], float(c[1]), float(c[2]), float(c[3]), float(c[4])
                                    v = float(c[5]) if len(c) > 5 else 0
                                    if isinstance(ts, (int, float)):
                                        ts_sec = ts / 1000.0 if ts > 1e12 else ts  # handle ms
                                        dt = datetime.fromtimestamp(ts_sec)
                                    elif isinstance(ts, str):
                                        try:
                                            dt = datetime.strptime(ts[:10], '%Y-%m-%d')
                                        except Exception:
                                            dt = datetime.now()
                                    else:
                                        dt = datetime.now()
                                    date_str = dt.strftime('%Y-%m-%d') if hasattr(dt, 'strftime') else str(ts)[:10]
                                    records.append({'date': date_str, 'open': o, 'high': h, 'low': l, 'close': cl, 'volume': int(v)})
                            if records:
                                logger.info(f"Got {len(records)} historical candles for {symbol} from Upstox")
                                return records, DataSource.UPSTOX, None
                    else:
                        err_body = resp.text[:200] if resp.text else ""
                        last_hint = f"Upstox historical API returned {resp.status_code}"
                        if resp.status_code == 401:
                            last_hint = "Upstox token expired or invalid. Reconnect Upstox."
                        elif "UDAPI1021" in err_body or "invalid format" in err_body.lower():
                            last_hint = "Invalid instrument key for this ticker."
                        elif "UDAPI100011" in err_body or "Invalid Instrument" in err_body:
                            last_hint = "Ticker not found in Upstox. Yahoo fallback will be tried."
                        logger.warning(f"[Historical] {last_hint} for {symbol}: {err_body}")
                else:
                    last_hint = "Instrument key not found for this ticker."
            except Exception as e:
                last_hint = f"Upstox error: {str(e)[:80]}"
                logger.debug(f"Upstox historical failed for {symbol}: {e}")

        # Try other sources
        for source_info in self.sources:
            if not source_info['available']:
                continue
            
            try:
                source = source_info['source']
                client = source_info['client']
                
                if source == DataSource.NSE:
                    nse_symbol = symbol.replace('.NS', '').replace('.BO', '')
                    hist_data = client.get_historical_data(nse_symbol, start_date, end_date)
                    if hist_data and len(hist_data) > 0:
                        logger.debug(f"Got historical data for {symbol} from NSE")
                        return hist_data, DataSource.NSE, None
                
                elif source == DataSource.YAHOO_FINANCE:
                    ticker = _yahoo_ticker(symbol)
                    session = _get_yahoo_session()
                    stock = client.Ticker(ticker, session=session) if session else client.Ticker(ticker)
                    hist = stock.history(start=start_date, end=end_date)
                    
                    if not hist.empty:
                        records = []
                        for date, row in hist.iterrows():
                            records.append({
                                'date': date.strftime('%Y-%m-%d'),
                                'open': float(row['Open']),
                                'high': float(row['High']),
                                'low': float(row['Low']),
                                'close': float(row['Close']),
                                'volume': int(row['Volume'])
                            })
                        logger.debug(f"Got historical data for {symbol} from Yahoo Finance")
                        return records, DataSource.YAHOO_FINANCE, None
                
            except Exception as e:
                last_hint = f"Data source failed: {str(e)[:60]}"
                logger.debug(f"Source {source_info['source']} failed for historical data {symbol}: {e}")
                continue
        
        logger.warning(f"All data sources failed for historical data {symbol}: {last_hint}")
        return None, None, last_hint
    
    def refresh_sources(self):
        """Refresh available data sources (e.g., after Upstox connection)"""
        self.sources = []
        self._initialize_sources()


# Global instance
_data_source_manager = None

def get_data_source_manager() -> DataSourceManager:
    """Get global data source manager instance"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager
