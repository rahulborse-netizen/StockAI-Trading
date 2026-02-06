"""
NSE Official API Integration
Primary data source for Indian stock market data
"""
import requests
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class NSEDataClient:
    """
    Client for NSE Official API
    Provides equity data, index data, and historical data
    """
    
    BASE_URL = "https://www.nseindia.com/api"
    
    def __init__(self):
        self.session = requests.Session()
        # NSE requires specific headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self._cookies_set = False
    
    def _ensure_session(self):
        """Ensure NSE session cookies are set by visiting homepage"""
        if not self._cookies_set:
            try:
                # Visit NSE homepage to get session cookies
                self.session.get('https://www.nseindia.com', timeout=10)
                self._cookies_set = True
                logger.debug("NSE session cookies set")
            except Exception as e:
                logger.warning(f"Error setting NSE session: {e}")
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """
        Get real-time quote for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE', 'TCS')
        
        Returns:
            Quote data dictionary or None if error
        """
        try:
            self._ensure_session()
            
            # NSE quote endpoint
            url = f"{self.BASE_URL}/quote-equity"
            params = {'symbol': symbol}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_quote(data)
            else:
                logger.warning(f"NSE quote API returned {response.status_code} for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching NSE quote for {symbol}: {e}")
            return None
    
    def _parse_quote(self, data: Dict) -> Dict:
        """Parse NSE quote response to standard format"""
        try:
            info = data.get('info', {})
            price_info = data.get('priceInfo', {})
            pre_open_market = data.get('preOpenMarket', {})
            
            current_price = price_info.get('lastPrice', 0)
            open_price = price_info.get('open', 0)
            high_price = price_info.get('intraDayHighLow', {}).get('max', 0)
            low_price = price_info.get('intraDayHighLow', {}).get('min', 0)
            close_price = price_info.get('close', 0)
            volume = price_info.get('totalTradedVolume', 0)
            
            # Calculate change
            change = current_price - close_price if close_price > 0 else 0
            change_pct = (change / close_price * 100) if close_price > 0 else 0
            
            return {
                'symbol': info.get('symbol', ''),
                'company_name': info.get('companyName', ''),
                'current_price': current_price,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'close': close_price,
                'volume': volume,
                'change': change,
                'change_pct': change_pct,
                'timestamp': datetime.now().isoformat(),
                'source': 'nse'
            }
        except Exception as e:
            logger.error(f"Error parsing NSE quote: {e}")
            return {}
    
    def get_index_data(self, index_name: str) -> Optional[Dict]:
        """
        Get index data (NIFTY, BANKNIFTY, etc.)
        
        Args:
            index_name: Index name (e.g., 'NIFTY 50', 'NIFTY BANK')
        
        Returns:
            Index data dictionary or None
        """
        try:
            self._ensure_session()
            
            # Map common names to NSE index names
            index_map = {
                'nifty': 'NIFTY 50',
                'nifty50': 'NIFTY 50',
                'banknifty': 'NIFTY BANK',
                'niftybank': 'NIFTY BANK',
                'sensex': 'SENSEX',  # Note: SENSEX is BSE, not NSE
                'vix': 'INDIA VIX',
                'indiavix': 'INDIA VIX'
            }
            
            nse_index_name = index_map.get(index_name.lower(), index_name)
            
            # NSE index endpoint
            url = f"{self.BASE_URL}/market-data-index"
            params = {'index': nse_index_name}
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_index_data(data, nse_index_name)
            else:
                logger.warning(f"NSE index API returned {response.status_code} for {nse_index_name}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching NSE index data for {index_name}: {e}")
            return None
    
    def _parse_index_data(self, data: Dict, index_name: str) -> Dict:
        """Parse NSE index response"""
        try:
            # NSE index data structure
            current_value = data.get('last', 0) or data.get('lastPrice', 0)
            open_value = data.get('open', 0)
            high_value = data.get('intraDayHighLow', {}).get('max', 0) or data.get('high', 0)
            low_value = data.get('intraDayHighLow', {}).get('min', 0) or data.get('low', 0)
            previous_close = data.get('previousClose', 0) or data.get('close', 0)
            
            change = current_value - previous_close if previous_close > 0 else 0
            change_pct = (change / previous_close * 100) if previous_close > 0 else 0
            
            return {
                'index_name': index_name,
                'value': current_value,
                'open': open_value,
                'high': high_value,
                'low': low_value,
                'close': previous_close,
                'change': change,
                'change_pct': change_pct,
                'timestamp': datetime.now().isoformat(),
                'source': 'nse'
            }
        except Exception as e:
            logger.error(f"Error parsing NSE index data: {e}")
            return {}
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
        """
        Get historical OHLCV data
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            List of OHLCV records or None
        """
        try:
            self._ensure_session()
            
            # NSE historical data endpoint
            url = f"{self.BASE_URL}/historical/equity"
            params = {
                'symbol': symbol,
                'from': start_date,
                'to': end_date
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return self._parse_historical_data(data)
            else:
                logger.warning(f"NSE historical API returned {response.status_code} for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching NSE historical data for {symbol}: {e}")
            return None
    
    def _parse_historical_data(self, data: Dict) -> List[Dict]:
        """Parse NSE historical data response"""
        try:
            records = []
            data_list = data.get('data', [])
            
            for record in data_list:
                records.append({
                    'date': record.get('CH_TIMESTAMP', ''),
                    'open': float(record.get('CH_OPENING_PRICE', 0)),
                    'high': float(record.get('CH_TRADE_HIGH_PRICE', 0)),
                    'low': float(record.get('CH_TRADE_LOW_PRICE', 0)),
                    'close': float(record.get('CH_CLOSING_PRICE', 0)),
                    'volume': int(record.get('CH_TOT_TRADED_QTY', 0))
                })
            
            return records
        except Exception as e:
            logger.error(f"Error parsing NSE historical data: {e}")
            return []


# Global instance
_nse_client = None

def get_nse_client() -> NSEDataClient:
    """Get global NSE client instance"""
    global _nse_client
    if _nse_client is None:
        _nse_client = NSEDataClient()
    return _nse_client
