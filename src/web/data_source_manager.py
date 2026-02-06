"""
Unified Data Source Manager
Manages multiple data sources with priority-based failover
"""
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DataSource(Enum):
    """Available data sources in priority order"""
    NSE = 1  # Primary - Official NSE API
    UPSTOX = 2  # Secondary - Upstox API (if connected)
    YAHOO_FINANCE = 3  # Fallback - Yahoo Finance


class DataSourceManager:
    """
    Unified interface for multiple data sources
    Implements priority-based fetching with automatic failover
    """
    
    def __init__(self):
        self.sources = []
        self._initialize_sources()
    
    def _initialize_sources(self):
        """Initialize available data sources"""
        # NSE is always available
        try:
            from src.web.nse_data_client import get_nse_client
            self.sources.append({
                'source': DataSource.NSE,
                'client': get_nse_client(),
                'available': True,
                'priority': 1
            })
            logger.info("NSE data source initialized")
        except Exception as e:
            logger.warning(f"Could not initialize NSE source: {e}")
        
        # Upstox is available if connected
        try:
            from src.web.upstox_api import UpstoxAPI
            from src.web.upstox_connection import connection_manager
            
            client = connection_manager.get_client()
            if client and client.access_token:
                self.sources.append({
                    'source': DataSource.UPSTOX,
                    'client': client,
                    'available': True,
                    'priority': 2
                })
                logger.info("Upstox data source initialized")
        except Exception as e:
            logger.debug(f"Upstox source not available: {e}")
        
        # Yahoo Finance is always available as fallback
        try:
            import yfinance as yf
            self.sources.append({
                'source': DataSource.YAHOO_FINANCE,
                'client': yf,
                'available': True,
                'priority': 3
            })
            logger.info("Yahoo Finance data source initialized")
        except Exception as e:
            logger.warning(f"Could not initialize Yahoo Finance source: {e}")
        
        # Sort by priority
        self.sources.sort(key=lambda x: x['priority'])
    
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
                    # Try Upstox Market Data API
                    from src.web.market_data import MarketDataClient
                    from src.web.instrument_master import InstrumentMaster
                    
                    market_client = MarketDataClient(client.access_token)
                    instrument_master = InstrumentMaster()
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
                    # Yahoo Finance fallback
                    ticker = symbol if '.' in symbol else f"{symbol}.NS"
                    stock = client.Ticker(ticker)
                    hist = stock.history(period="1d", interval="1m")
                    
                    if not hist.empty:
                        latest = hist.iloc[-1]
                        prev_close = stock.history(period="2d", interval="1d")
                        prev_close_price = float(prev_close.iloc[-2]['Close']) if len(prev_close) >= 2 else float(latest['Close'])
                        
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
                    # Try Upstox for indices
                    from src.web.market_data import MarketDataClient
                    
                    market_client = MarketDataClient(client.access_token)
                    
                    # Map index names to Upstox keys
                    index_map = {
                        'nifty': 'NSE_INDEX|Nifty 50',
                        'nifty50': 'NSE_INDEX|Nifty 50',
                        'banknifty': 'NSE_INDEX|Nifty Bank',
                        'sensex': 'BSE_INDEX|SENSEX',
                        'vix': 'NSE_INDEX|India VIX',
                        'indiavix': 'NSE_INDEX|India VIX'
                    }
                    
                    upstox_key = index_map.get(index_name.lower())
                    if upstox_key:
                        quote = market_client.get_quote(upstox_key, use_cache=True)
                        if quote:
                            parsed = market_client.parse_quote(quote)
                            if parsed.get('price', 0) > 0:
                                parsed['index_name'] = index_name
                                parsed['source'] = 'upstox'
                                logger.debug(f"Got index data for {index_name} from Upstox")
                                return parsed, DataSource.UPSTOX
                
                elif source == DataSource.YAHOO_FINANCE:
                    # Yahoo Finance fallback
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
                        stock = client.Ticker(ticker)
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
    
    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> Tuple[Optional[List[Dict]], DataSource]:
        """
        Get historical data from best available source
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
        
        Returns:
            Tuple of (historical_data, source_used) or (None, None) if all sources fail
        """
        # Try NSE first
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
                        return hist_data, DataSource.NSE
                
                elif source == DataSource.YAHOO_FINANCE:
                    # Yahoo Finance fallback
                    ticker = symbol if '.' in symbol else f"{symbol}.NS"
                    stock = client.Ticker(ticker)
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
                        return records, DataSource.YAHOO_FINANCE
                
            except Exception as e:
                logger.debug(f"Source {source_info['source']} failed for historical data {symbol}: {e}")
                continue
        
        logger.warning(f"All data sources failed for historical data {symbol}")
        return None, None
    
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
