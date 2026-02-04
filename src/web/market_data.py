"""
Upstox Market Data API Integration
Phase 2.1: Real-time data integration
"""
import requests
from typing import Optional, Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MarketDataClient:
    """Client for Upstox Market Data API"""
    
    BASE_URL = "https://api.upstox.com/v2"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        })
    
    def get_quote(self, instrument_key: str) -> Optional[Dict]:
        """
        Get real-time quote for a single instrument.
        
        Args:
            instrument_key: Upstox instrument key (e.g., 'NSE_EQ|INE467B01029')
        
        Returns:
            Quote data or None if error
        """
        try:
            url = f"{self.BASE_URL}/market-quote/quotes"
            params = {'instrument_key': instrument_key}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data and instrument_key in data['data']:
                return data['data'][instrument_key]
            return None
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout getting quote for {instrument_key}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting quote for {instrument_key}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting quote for {instrument_key}: {e}")
            return None
    
    def get_quotes(self, instrument_keys: List[str]) -> Dict[str, Dict]:
        """
        Get real-time quotes for multiple instruments.
        
        Args:
            instrument_keys: List of Upstox instrument keys
        
        Returns:
            Dictionary of instrument_key -> quote data
        """
        if not instrument_keys:
            return {}
        
        try:
            url = f"{self.BASE_URL}/market-quote/quotes"
            # Upstox API accepts comma-separated instrument keys
            params = {'instrument_key': ','.join(instrument_keys)}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' in data:
                return data['data']
            return {}
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout getting quotes for {len(instrument_keys)} instruments")
            return {}
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error getting quotes: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error getting quotes: {e}")
            return {}
    
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
