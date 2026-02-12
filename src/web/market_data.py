"""
Upstox Market Data API Integration
Phase 2.1: Real-time data integration with caching
"""
import requests
from typing import Optional, Dict, List
import logging
from datetime import datetime, timedelta
from threading import Lock
import time

logger = logging.getLogger(__name__)

class MarketDataCache:
    """Cache for market data quotes with TTL"""
    
    def __init__(self, default_ttl: int = 5):
        self.cache: Dict[str, Dict] = {}
        self.cache_lock = Lock()
        self.default_ttl = default_ttl  # seconds
    
    def cache_quote(self, instrument_key: str, quote_data: Dict, ttl: Optional[int] = None) -> None:
        """Cache a quote with TTL"""
        ttl = ttl or self.default_ttl
        with self.cache_lock:
            self.cache[instrument_key] = {
                'data': quote_data,
                'timestamp': datetime.now(),
                'ttl': ttl
            }
    
    def get_cached_quote(self, instrument_key: str) -> Optional[Dict]:
        """Get cached quote if still valid"""
        with self.cache_lock:
            if instrument_key not in self.cache:
                return None
            
            cached = self.cache[instrument_key]
            age = (datetime.now() - cached['timestamp']).total_seconds()
            
            if age > cached['ttl']:
                # Expired, remove from cache
                del self.cache[instrument_key]
                return None
            
            return cached['data']
    
    def update_from_websocket(self, instrument_key: str, price_data: Dict) -> None:
        """Update cache from WebSocket data"""
        with self.cache_lock:
            # Convert WebSocket price data to quote format
            quote_data = {
                'last_price': price_data.get('price', price_data.get('ltp', 0)),
                'ohlc': {
                    'open': price_data.get('open', price_data.get('price', 0)),
                    'high': price_data.get('high', price_data.get('price', 0)),
                    'low': price_data.get('low', price_data.get('price', 0)),
                    'close': price_data.get('close', price_data.get('price', 0))
                },
                'volume': price_data.get('volume', 0),
                'change': price_data.get('change', 0),
                'change_pct': price_data.get('change_pct', 0)
            }
            self.cache_quote(instrument_key, quote_data, ttl=60)  # Longer TTL for WebSocket data
    
    def clear_cache(self) -> None:
        """Clear all cached data"""
        with self.cache_lock:
            self.cache.clear()
    
    def get_all_cached(self) -> Dict[str, Dict]:
        """Get all valid cached quotes"""
        with self.cache_lock:
            valid_cache = {}
            now = datetime.now()
            for key, cached in list(self.cache.items()):
                age = (now - cached['timestamp']).total_seconds()
                if age <= cached['ttl']:
                    valid_cache[key] = cached['data']
                else:
                    del self.cache[key]
            return valid_cache


class MarketDataClient:
    """Client for Upstox Market Data API with caching"""
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        })
        # Phase 2.1: Add caching
        self.cache = MarketDataCache(default_ttl=5)
    
    def get_quote(self, instrument_key: str, use_cache: bool = True) -> Optional[Dict]:
        """
        Get real-time quote for a single instrument.
        
        Args:
            instrument_key: Upstox instrument key (e.g., 'NSE_EQ|INE467B01029')
            use_cache: Whether to use cached data if available
        
        Returns:
            Quote data or None if error
        """
        # Phase 2.1: Check cache first
        if use_cache:
            cached = self.cache.get_cached_quote(instrument_key)
            if cached:
                logger.debug(f"Returning cached quote for {instrument_key}")
                return cached
        
        try:
            url = f"{self.BASE_URL}/market-quote/quotes"
            params = {'instrument_key': instrument_key}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data:
                return None
            quote_data = data['data']
            quote = quote_data.get(instrument_key)
            if quote is None and len(quote_data) == 1:
                quote = next(iter(quote_data.values()))
            if quote:
                self.cache.cache_quote(instrument_key, quote)
                return quote
            return None

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                logger.warning(f"Upstox 401 for {instrument_key} - token may be expired. Reconnect or refresh token.")
            if use_cache:
                return self.cache.get_cached_quote(instrument_key)
            return None
        except requests.exceptions.Timeout:
            logger.error(f"Timeout getting quote for {instrument_key}")
            # Return cached data if available as fallback
            if use_cache:
                return self.cache.get_cached_quote(instrument_key)
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting quote for {instrument_key}: {e}")
            # Return cached data if available as fallback
            if use_cache:
                return self.cache.get_cached_quote(instrument_key)
            return None
        except Exception as e:
            logger.error(f"Error getting quote for {instrument_key}: {e}")
            # Return cached data if available as fallback
            if use_cache:
                return self.cache.get_cached_quote(instrument_key)
            return None
    
    def get_quotes(self, instrument_keys: List[str], use_cache: bool = True) -> Dict[str, Dict]:
        """
        Get real-time quotes for multiple instruments.
        
        Args:
            instrument_keys: List of Upstox instrument keys
            use_cache: Whether to use cached data if available
        
        Returns:
            Dictionary of instrument_key -> quote data
        """
        if not instrument_keys:
            return {}
        
        quotes = {}
        keys_to_fetch = []
        
        # Phase 2.1: Check cache first
        if use_cache:
            for inst_key in instrument_keys:
                cached = self.cache.get_cached_quote(inst_key)
                if cached:
                    quotes[inst_key] = cached
                else:
                    keys_to_fetch.append(inst_key)
        else:
            keys_to_fetch = instrument_keys
        
        # Fetch remaining quotes from API
        if keys_to_fetch:
            try:
                url = f"{self.BASE_URL}/market-quote/quotes"
                # Upstox API accepts comma-separated instrument keys
                params = {'instrument_key': ','.join(keys_to_fetch)}
                
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                if 'data' in data:
                    # Cache fetched quotes
                    for inst_key, quote in data['data'].items():
                        self.cache.cache_quote(inst_key, quote)
                        quotes[inst_key] = quote
                
            except requests.exceptions.Timeout:
                logger.error(f"Timeout getting quotes for {len(keys_to_fetch)} instruments")
                # Try to get from cache as fallback
                if use_cache:
                    for inst_key in keys_to_fetch:
                        cached = self.cache.get_cached_quote(inst_key)
                        if cached:
                            quotes[inst_key] = cached
            except requests.exceptions.ConnectionError as e:
                logger.error(f"Connection error getting quotes: {e}")
                # Try to get from cache as fallback
                if use_cache:
                    for inst_key in keys_to_fetch:
                        cached = self.cache.get_cached_quote(inst_key)
                        if cached:
                            quotes[inst_key] = cached
            except Exception as e:
                logger.error(f"Error getting quotes: {e}")
                # Try to get from cache as fallback
                if use_cache:
                    for inst_key in keys_to_fetch:
                        cached = self.cache.get_cached_quote(inst_key)
                        if cached:
                            quotes[inst_key] = cached
        
        return quotes
    
    def get_market_indices(self) -> Dict[str, Dict]:
        """
        Get market indices (NIFTY50, BankNifty, Sensex).
        
        Returns:
            Dictionary of index name -> quote data
        """
        # Common index instrument keys
        index_keys = {
            'NIFTY50': 'NSE_INDEX|Nifty 50',
            'BANKNIFTY': 'NSE_INDEX|Nifty Bank',
            'SENSEX': 'BSE_INDEX|SENSEX'
        }
        
        instrument_keys = list(index_keys.values())
        quotes = self.get_quotes(instrument_keys)
        
        # Map back to friendly names
        result = {}
        for name, key in index_keys.items():
            if key in quotes:
                result[name] = quotes[key]
        
        return result
    
    def parse_quote(self, quote_data: Dict) -> Dict:
        """
        Parse Upstox quote response into a standardized format.
        
        Args:
            quote_data: Raw quote data from Upstox API
        
        Returns:
            Parsed quote data
        """
        try:
            # Upstox quote structure (may vary)
            ohlc = quote_data.get('ohlc', {})
            last_price = quote_data.get('last_price', 0)
            open_price = ohlc.get('open', last_price)
            high = ohlc.get('high', last_price)
            low = ohlc.get('low', last_price)
            close = ohlc.get('close', last_price)
            
            # Calculate change
            change = last_price - close if close > 0 else 0
            change_pct = (change / close * 100) if close > 0 else 0
            
            return {
                'price': float(last_price),
                'open': float(open_price),
                'high': float(high),
                'low': float(low),
                'close': float(close),
                'change': float(change),
                'change_pct': float(change_pct),
                'volume': float(quote_data.get('volume', 0)),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error parsing quote: {e}")
            return {
                'price': 0,
                'change': 0,
                'change_pct': 0,
                'volume': 0,
                'timestamp': datetime.now().isoformat()
            }
