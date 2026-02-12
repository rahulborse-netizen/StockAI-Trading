"""
Upstox Instrument Master - Download and cache instrument mappings
Maps NSE/BSE tickers to Upstox instrument_key for order placement
"""
import gzip
import io
import json
import requests
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Upstox instrument master URLs (CSV and JSON gzip fallback)
INSTRUMENT_MASTER_URLS = {
    'NSE_EQ': 'https://assets.upstox.com/market-quote/instruments/exchange/NSE_EQ.csv',
    'BSE_EQ': 'https://assets.upstox.com/market-quote/instruments/exchange/BSE_EQ.csv',
    'NSE_INDEX': 'https://assets.upstox.com/market-quote/instruments/exchange/NSE_INDEX.csv',
    'BSE_INDEX': 'https://assets.upstox.com/market-quote/instruments/exchange/BSE_INDEX.csv',
}
# JSON gzip fallback (better coverage, different column names)
INSTRUMENT_JSON_URLS = {
    'NSE_EQ': 'https://assets.upstox.com/market-quote/instruments/exchange/NSE_EQ.json.gz',
    'BSE_EQ': 'https://assets.upstox.com/market-quote/instruments/exchange/BSE_EQ.json.gz',
    'NSE_INDEX': 'https://assets.upstox.com/market-quote/instruments/exchange/NSE_INDEX.json.gz',
    'BSE_INDEX': 'https://assets.upstox.com/market-quote/instruments/exchange/BSE_INDEX.json.gz',
}

# Comprehensive ticker mapping (expanded for common NSE stocks)
# Format: Yahoo Finance ticker -> Upstox instrument_key
TICKER_MAP = {
    # NIFTY 50 stocks
    'RELIANCE.NS': 'NSE_EQ|INE467B01029',
    'TCS.NS': 'NSE_EQ|INE467B01029',  # Will need actual ISIN
    'HDFCBANK.NS': 'NSE_EQ|INE040A01034',
    'ICICIBANK.NS': 'NSE_EQ|INE090A01021',
    'INFY.NS': 'NSE_EQ|INE009A01021',
    'HINDUNILVR.NS': 'NSE_EQ|INE030A01027',
    'ITC.NS': 'NSE_EQ|INE154A01016',
    'LT.NS': 'NSE_EQ|INE018A01030',
    'SBIN.NS': 'NSE_EQ|INE062A01020',
    'BHARTIARTL.NS': 'NSE_EQ|INE397D01024',
    'KOTAKBANK.NS': 'NSE_EQ|INE237A01028',
    'AXISBANK.NS': 'NSE_EQ|INE238A01034',
    'ASIANPAINT.NS': 'NSE_EQ|INE021A01026',
    'MARUTI.NS': 'NSE_EQ|INE585B01010',
    'HCLTECH.NS': 'NSE_EQ|INE860A01027',
    'SUNPHARMA.NS': 'NSE_EQ|INE044A01036',
    'TITAN.NS': 'NSE_EQ|INE280A01028',
    'BAJFINANCE.NS': 'NSE_EQ|INE296A01024',
    'BAJAJFINSV.NS': 'NSE_EQ|INE918I01026',
    'ULTRACEMCO.NS': 'NSE_EQ|INE481G01011',
    'NESTLEIND.NS': 'NSE_EQ|INE239A01016',
    'WIPRO.NS': 'NSE_EQ|INE075A01022',
    'ONGC.NS': 'NSE_EQ|INE213A01029',
    'NTPC.NS': 'NSE_EQ|INE733E01010',
    'POWERGRID.NS': 'NSE_EQ|INE752E01010',
    'M&M.NS': 'NSE_EQ|INE101A01026',
    'TATAMOTORS.NS': 'NSE_EQ|INE155A01022',
    'JSWSTEEL.NS': 'NSE_EQ|INE019A01038',
    'TATASTEEL.NS': 'NSE_EQ|INE081A01012',
    'ADANIENT.NS': 'NSE_EQ|INE423A01024',
    'ADANIPORTS.NS': 'NSE_EQ|INE742F01042',
    'COALINDIA.NS': 'NSE_EQ|INE522F01014',
    'GRASIM.NS': 'NSE_EQ|INE047A01021',
    'DIVISLAB.NS': 'NSE_EQ|INE361B01024',
    'CIPLA.NS': 'NSE_EQ|INE059A01026',
    'DRREDDY.NS': 'NSE_EQ|INE089A01023',
    'EICHERMOT.NS': 'NSE_EQ|INE066A01013',
    'HEROMOTOCO.NS': 'NSE_EQ|INE158A01026',
    'INDUSINDBK.NS': 'NSE_EQ|INE095A01012',
    'TECHM.NS': 'NSE_EQ|INE669C01036',
    'APOLLOHOSP.NS': 'NSE_EQ|INE437A01024',
    'BAJAJ-AUTO.NS': 'NSE_EQ|INE917I01010',
    'BRITANNIA.NS': 'NSE_EQ|INE216A01030',
    'HDFCLIFE.NS': 'NSE_EQ|INE795G01014',
    'HDFCAMC.NS': 'NSE_EQ|INE127D01025',
    'SBILIFE.NS': 'NSE_EQ|INE472M01021',
    'TATACONSUM.NS': 'NSE_EQ|INE192A01025',
    # Indices
    '^NSEI': 'NSE_INDEX|Nifty 50',
    '^NSEBANK': 'NSE_INDEX|Nifty Bank',
    '^BSESN': 'BSE_INDEX|SENSEX',
    '^INDIAVIX': 'NSE_INDEX|India VIX',
    # Common index aliases (without ^ prefix)
    'NIFTY': 'NSE_INDEX|Nifty 50',
    'NIFTY50': 'NSE_INDEX|Nifty 50',
    'BANKNIFTY': 'NSE_INDEX|Nifty Bank',
    'SENSEX': 'BSE_INDEX|SENSEX',
    'VIX': 'NSE_INDEX|India VIX',
    'INDIAVIX': 'NSE_INDEX|India VIX',
    # Common ticker variations
    'HDFC.NS': 'NSE_EQ|INE040A01034',  # HDFC Bank
    'HDCF': 'NSE_EQ|INE040A01034',  # Common typo/variation
    # Demat holdings (expanded for signal generation)
    'IREDA.NS': 'NSE_EQ|INE202E01016',  # Indian Renewable Energy Development Agency
    'NTPCGREEN.NS': 'NSE_EQ|INE0ONG01011',  # NTPC Green Energy (from Upstox)
    'TEXRAIL.NS': 'NSE_EQ|INE778L01019',  # Texmaco Rail & Engineering
    'URBANCO.NS': 'NSE_EQ|INE0CAZ01013',  # Urban Company (from Upstox)
    'BSE.NS': 'NSE_EQ|INE118H01025',  # BSE Ltd
    'FSL.NS': 'NSE_EQ|INE684F01012',  # Firstsource Solutions
}

CACHE_DIR = Path('data/instruments')
CACHE_EXPIRY_HOURS = 24  # Refresh daily


class InstrumentMaster:
    """Manages Upstox instrument master data for ticker -> instrument_key mapping"""
    
    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._instruments: Dict[str, pd.DataFrame] = {}
        self._ticker_map: Dict[str, str] = {}
        self._download_failed: set = set()  # Track exchanges that failed to download
        self._load_cached()
    
    def _get_cache_path(self, exchange: str) -> Path:
        """Get cache file path for an exchange (CSV)"""
        return self.cache_dir / f"{exchange}.csv"

    def _get_json_cache_path(self, exchange: str) -> Path:
        """Get cache file path for JSON instrument list"""
        return self.cache_dir / f"{exchange}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache is still valid (not expired)"""
        if not cache_path.exists():
            return False
        try:
            mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
            age = datetime.now() - mtime
            return age < timedelta(hours=CACHE_EXPIRY_HOURS)
        except:
            return False
    
    def _download_instruments(self, exchange: str) -> Optional[pd.DataFrame]:
        """Download instrument master CSV for an exchange"""
        # Skip if we know this exchange fails to download
        if exchange in self._download_failed:
            return None
            
        url = INSTRUMENT_MASTER_URLS.get(exchange)
        if not url:
            logger.warning(f"No URL configured for exchange: {exchange}")
            return None
        
        try:
            logger.info(f"Downloading instrument master for {exchange}...")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (compatible; StockAI-Trading/1.0)'}
            response = requests.get(url, headers=headers, timeout=60)
            response.raise_for_status()
            
            # Read CSV from response content (avoid double fetch)
            df = pd.read_csv(io.BytesIO(response.content))
            logger.info(f"Downloaded {len(df)} instruments for {exchange}")
            
            # Cache it
            cache_path = self._get_cache_path(exchange)
            df.to_csv(cache_path, index=False)
            logger.info(f"Cached to {cache_path}")
            
            # Remove from failed set if successful
            self._download_failed.discard(exchange)
            
            return df
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                # 403 Forbidden - mark as failed to avoid repeated attempts
                self._download_failed.add(exchange)
                logger.warning(f"Access forbidden (403) for {exchange} instruments. Using cached data or TICKER_MAP only.")
            else:
                logger.error(f"Failed to download {exchange} instruments: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to download {exchange} instruments: {e}")
            return None

    def _download_instruments_json(self, exchange: str) -> Optional[pd.DataFrame]:
        """Download instrument master JSON (gzip) as fallback when CSV fails"""
        if exchange in self._download_failed:
            return None
        url = INSTRUMENT_JSON_URLS.get(exchange)
        if not url:
            return None
        try:
            logger.info(f"Downloading instrument master JSON for {exchange}...")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (compatible; StockAI-Trading/1.0)'}
            response = requests.get(url, headers=headers, timeout=90)
            response.raise_for_status()
            with gzip.GzipFile(fileobj=io.BytesIO(response.content), mode='rb') as gf:
                data = json.load(gf)
            if not isinstance(data, list):
                data = data if isinstance(data, list) else []
            rows = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                tradingsymbol = item.get('tradingsymbol') or item.get('trading_symbol', '')
                inst_key = item.get('instrument_key') or item.get('instrument_token', '')
                name = item.get('name') or item.get('symbol', '')
                if tradingsymbol or inst_key:
                    rows.append({
                        'tradingsymbol': str(tradingsymbol).strip(),
                        'instrument_key': inst_key,
                        'instrument_token': inst_key,
                        'name': str(name) if name else ''
                    })
            if not rows:
                return None
            df = pd.DataFrame(rows)
            cache_path = self._get_json_cache_path(exchange)
            df.to_csv(cache_path, index=False)
            logger.info(f"Downloaded {len(df)} instruments (JSON) for {exchange}")
            self._download_failed.discard(exchange)
            return df
        except Exception as e:
            logger.warning(f"Failed to download JSON instruments for {exchange}: {e}")
            return None

    def _load_cached(self):
        """Load instruments from cache (CSV or JSON-derived CSV)"""
        for exchange in INSTRUMENT_MASTER_URLS.keys():
            for cache_path in [self._get_cache_path(exchange), self._get_json_cache_path(exchange)]:
                if cache_path.exists():
                    try:
                        df = pd.read_csv(cache_path)
                        if not df.empty and ('tradingsymbol' in df.columns or 'trading_symbol' in df.columns or 'instrument_key' in df.columns):
                            self._instruments[exchange] = df
                            logger.info(f"Loaded {len(df)} cached instruments for {exchange}")
                            break
                    except Exception as e:
                        logger.warning(f"Failed to load cache for {exchange}: {e}")
    
    def _ensure_instruments(self, exchange: str) -> Optional[pd.DataFrame]:
        """Ensure instruments are loaded (from cache or download)"""
        if exchange in self._instruments:
            cache_path = self._get_cache_path(exchange)
            if self._is_cache_valid(cache_path):
                return self._instruments[exchange]
        
        # Skip download if we know it fails
        if exchange in self._download_failed:
            return None
        
        # Cache expired or missing, download fresh (CSV first, JSON fallback)
        df = self._download_instruments(exchange)
        if df is None:
            df = self._download_instruments_json(exchange)
        if df is not None:
            self._instruments[exchange] = df
        return df
    
    def get_instrument_key(self, ticker: str) -> Optional[str]:
        """
        Convert Yahoo Finance ticker to Upstox instrument_key
        
        Args:
            ticker: Yahoo Finance format (e.g., 'RELIANCE.NS', '^NSEI', 'TCS.BO')
        
        Returns:
            Upstox instrument_key (e.g., 'NSE_EQ|INE467B01029') or None if not found
        """
        # Normalize ticker and save original for warning suppression
        original_ticker = ticker.strip().upper()
        ticker = original_ticker
        
        # First, try hardcoded map (fastest, most reliable) - check BEFORE conversion
        if ticker in TICKER_MAP:
            return TICKER_MAP[ticker]
        
        # Handle common variations and aliases (only if not found in TICKER_MAP)
        ticker_variations = {
            'NIFTY': '^NSEI',
            'NIFTY50': '^NSEI',
            'BANKNIFTY': '^NSEBANK',
            'SENSEX': '^BSESN',
            'VIX': '^INDIAVIX',
            'INDIAVIX': '^INDIAVIX',
        }
        
        # Try variation mapping if not found in TICKER_MAP
        if ticker in ticker_variations:
            ticker = ticker_variations[ticker]
            # Check TICKER_MAP again after conversion
            if ticker in TICKER_MAP:
                return TICKER_MAP[ticker]
        
        # Try downloading instrument master (may fail due to 403, but worth trying)
        # Handle indices
        if ticker.startswith('^'):
            if 'NSE' in ticker:
                exchange = 'NSE_INDEX'
                symbol = ticker.replace('^', '').replace('NSE', '').strip()
                if symbol == 'I':
                    symbol = 'Nifty 50'
                elif symbol == 'BANK':
                    symbol = 'Nifty Bank'
            elif 'BSE' in ticker:
                exchange = 'BSE_INDEX'
                symbol = ticker.replace('^', '').replace('BSE', '').strip()
                if symbol == 'SN':
                    symbol = 'SENSEX'
            else:
                return None
            
            df = self._ensure_instruments(exchange)
            if df is not None and not df.empty:
                # Match by name
                if 'name' in df.columns:
                    match = df[df['name'].str.contains(symbol, case=False, na=False)]
                    if not match.empty:
                        instrument_key = match.iloc[0].get('instrument_key') or match.iloc[0].get('instrument_token')
                        if instrument_key:
                            return instrument_key
        
        # Handle equity stocks
        if ticker.endswith('.NS'):
            exchange = 'NSE_EQ'
            symbol = ticker.replace('.NS', '')
        elif ticker.endswith('.BO'):
            exchange = 'BSE_EQ'
            symbol = ticker.replace('.BO', '')
        else:
            # Try NSE by default
            exchange = 'NSE_EQ'
            symbol = ticker
        
        df = self._ensure_instruments(exchange)
        if df is not None and not df.empty:
            # Normalize symbol for matching (case-insensitive)
            symbol_upper = symbol.upper()
            # Try exact match on tradingsymbol (handle both column names)
            sym_col = 'tradingsymbol' if 'tradingsymbol' in df.columns else ('trading_symbol' if 'trading_symbol' in df.columns else None)
            if sym_col:
                try:
                    match = df[df[sym_col].astype(str).str.upper() == symbol_upper]
                    if not match.empty:
                        instrument_key = match.iloc[0].get('instrument_key') or match.iloc[0].get('instrument_token')
                        if instrument_key:
                            return instrument_key
                except Exception:
                    pass
            # Try partial match on name
            if 'name' in df.columns:
                match = df[df['name'].str.contains(symbol, case=False, na=False)]
                if not match.empty:
                    instrument_key = match.iloc[0].get('instrument_key') or match.iloc[0].get('instrument_token')
                    if instrument_key:
                        return instrument_key
        
        # Only log warning if not a common index/alias that we've already tried
        # Check original_ticker to catch variations before conversion
        common_tickers = ['NIFTY', 'NIFTY50', 'BANKNIFTY', 'SENSEX', 'VIX', 'INDIAVIX', 'HDCF', '^NSEI', '^NSEBANK', '^BSESN', '^INDIAVIX']
        if original_ticker not in common_tickers and ticker not in common_tickers:
            logger.warning(f"Could not find instrument_key for ticker: {original_ticker}. Add it to TICKER_MAP or use Upstox API search.")
        return None
    
    def refresh_cache(self):
        """Force refresh all instrument caches"""
        logger.info("Refreshing instrument master cache...")
        for exchange in INSTRUMENT_MASTER_URLS.keys():
            self._download_instruments(exchange)
        self._load_cached()


# Global instance
_instrument_master: Optional[InstrumentMaster] = None

def get_instrument_master() -> InstrumentMaster:
    """Get global instrument master instance"""
    global _instrument_master
    if _instrument_master is None:
        _instrument_master = InstrumentMaster()
    return _instrument_master
