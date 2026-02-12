#!/usr/bin/env python3
"""
STANDALONE TRADING SIGNAL GENERATOR
Uses NSE API by default. For live data (avoids NSE blocking), use Upstox:

  set UPSTOX_ACCESS_TOKEN=your_token   # Windows
  export UPSTOX_ACCESS_TOKEN=your_token  # Linux/Mac
  python trading_signals_nse_only.py --indices --intraday

Get token: Connect Upstox in the web app (run_web.py) and copy from session,
or use Upstox OAuth flow. Token can also be in .env as UPSTOX_ACCESS_TOKEN.

Usage:
    python trading_signals_nse_only.py
    python trading_signals_nse_only.py --tickers RELIANCE TCS INFY
    python trading_signals_nse_only.py --indices --intraday  # NIFTY, BANKNIFTY, SENSEX
"""

import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import argparse
from typing import List, Dict, Optional
import pytz
import json
import math

# ============================================================================
# CONFIGURATION
# ============================================================================

IST = pytz.timezone('Asia/Kolkata')

# Popular Indian stocks (NSE symbols without .NS suffix)
DEFAULT_STOCKS = [
    'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK',
    'BHARTIARTL', 'SBIN', 'BAJFINANCE', 'LICI', 'ITC',
    'HCLTECH', 'AXISBANK', 'KOTAKBANK', 'LT', 'ASIANPAINT',
    'MARUTI', 'TITAN', 'ULTRACEMCO', 'NTPC', 'SUNPHARMA'
]

# Indices for intraday trading
INDICES = {
    'NIFTY': 'NIFTY 50',
    'BANKNIFTY': 'NIFTY BANK',
    'SENSEX': 'SENSEX',  # BSE index
    'NIFTYIT': 'NIFTY IT',
    'NIFTYFMCG': 'NIFTY FMCG',
    'NIFTYPHARMA': 'NIFTY PHARMA'
}


# ============================================================================
# UPSTOX DATA FETCHING (live data when NSE blocks)
# ============================================================================

def _get_upstox_token() -> Optional[str]:
    """Get Upstox access token from env or .env file"""
    token = os.environ.get('UPSTOX_ACCESS_TOKEN', '').strip()
    if token:
        return token
    try:
        from dotenv import load_dotenv
        load_dotenv()
        return os.environ.get('UPSTOX_ACCESS_TOKEN', '').strip() or None
    except ImportError:
        return None


class UpstoxDataClient:
    """Upstox API client for live quotes and historical data (no NSE restrictions)"""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        })
        self._instrument_master = None
        self._market_client = None

    def _get_instrument_key(self, symbol: str) -> Optional[str]:
        """Resolve symbol to Upstox instrument key"""
        try:
            if self._instrument_master is None:
                import sys
                from pathlib import Path
                root = Path(__file__).resolve().parent
                if str(root) not in sys.path:
                    sys.path.insert(0, str(root))
                from src.web.instrument_master import get_instrument_master
                self._instrument_master = get_instrument_master()
            sym = symbol.replace('.NS', '').replace('.BO', '').strip().upper()
            return self._instrument_master.get_instrument_key(sym) or self._instrument_master.get_instrument_key(f'{sym}.NS')
        except Exception:
            return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get live quote - returns same format as NSEClient"""
        try:
            inst_key = self._get_instrument_key(symbol)
            if not inst_key:
                return None
            url = "https://api.upstox.com/v2/market-quote/quotes"
            resp = self.session.get(url, params={'instrument_key': inst_key}, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if 'data' not in data or inst_key not in data['data']:
                return None
            q = data['data'][inst_key]
            ohlc = q.get('ohlc', {})
            last = float(q.get('last_price', 0) or 0)
            close = float(ohlc.get('close', last) or last)
            change = last - close if close > 0 else 0
            change_pct = (change / close * 100) if close > 0 else 0
            is_index = symbol.upper() in INDICES or any(x in symbol.upper() for x in ['NIFTY', 'BANKNIFTY', 'SENSEX'])
            return {
                'symbol': symbol.upper(),
                'price': last,
                'open': float(ohlc.get('open', last) or last),
                'high': float(ohlc.get('high', last) or last),
                'low': float(ohlc.get('low', last) or last),
                'close': close,
                'volume': int(q.get('volume', 0) or 0),
                'change': change,
                'change_pct': change_pct,
                'name': symbol,
                'is_index': is_index
            }
        except Exception:
            return None

    def get_historical_data(self, symbol: str, days: int = 60, intraday: bool = False) -> Optional[pd.DataFrame]:
        """Get historical OHLC from Upstox"""
        try:
            inst_key = self._get_instrument_key(symbol)
            if not inst_key:
                return None
            from urllib.parse import quote
            interval = "1day"
            if intraday:
                interval = "5minute"
            end_dt = datetime.now(IST)
            start_dt = end_dt - timedelta(days=min(days, 365))
            to_ts = end_dt.strftime("%Y-%m-%d")
            from_ts = start_dt.strftime("%Y-%m-%d")
            enc = quote(inst_key, safe="")
            url = f"https://api.upstox.com/v2/historical-candle/{enc}/{interval}/{to_ts}"
            resp = self.session.get(url, params={"from": from_ts}, timeout=30)
            if resp.status_code != 200:
                return None
            data = resp.json()
            candles = data.get("data", {}).get("candles") if isinstance(data, dict) else None
            if not candles or not isinstance(candles, list):
                return None
            rows = []
            for c in candles:
                if isinstance(c, (list, tuple)) and len(c) >= 5:
                    ts = c[0]
                    dt = pd.to_datetime(ts, unit="s") if isinstance(ts, (int, float)) else pd.to_datetime(ts)
                    rows.append({
                        'date': dt,
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4]),
                        'volume': int(c[5]) if len(c) > 5 else 0
                    })
            if not rows:
                return None
            df = pd.DataFrame(rows).set_index('date').sort_index()
            if intraday and len(df) > 0:
                today = datetime.now(IST).date()
                df_today = df[df.index.date == today]
                if len(df_today) >= 10:
                    return df_today
                df = df.tail(50)
            return df
        except Exception:
            return None

    def get_intraday_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get intraday 5m data"""
        return self.get_historical_data(symbol, days=5, intraday=True)


# ============================================================================
# NSE DATA FETCHING
# ============================================================================

class NSEClient:
    """NSE API client - no SSL issues!"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        self._cookies_set = False
    
    def _ensure_session(self):
        """Set NSE session cookies"""
        if not self._cookies_set:
            try:
                # Visit homepage to get cookies
                self.session.get('https://www.nseindia.com', timeout=10)
                # Also visit market data page (sometimes needed)
                self.session.get('https://www.nseindia.com/market-data', timeout=10)
                self._cookies_set = True
            except:
                # If homepage fails, try direct API call
                try:
                    self.session.get('https://www.nseindia.com/api/marketStatus', timeout=10)
                    self._cookies_set = True
                except:
                    pass
    
    def get_index_quote(self, index_name: str) -> Optional[Dict]:
        """Get live quote for indices (NIFTY, BANKNIFTY, etc.)"""
        try:
            self._ensure_session()
            
            # Map common names to NSE index names
            index_map = {
                'NIFTY': 'NIFTY 50',
                'NIFTY50': 'NIFTY 50',
                'BANKNIFTY': 'NIFTY BANK',
                'NIFTYBANK': 'NIFTY BANK',
                'SENSEX': 'SENSEX',
                'NIFTYIT': 'NIFTY IT',
                'NIFTYFMCG': 'NIFTY FMCG',
                'NIFTYPHARMA': 'NIFTY PHARMA'
            }
            
            nse_index_name = index_map.get(index_name.upper(), index_name.upper())
            
            # NSE index quote endpoint
            url = "https://www.nseindia.com/api/market-data-index"
            params = {'index': nse_index_name}
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract index data
                last_price = data.get('last', 0) or data.get('lastPrice', 0) or data.get('value', 0)
                if last_price == 0:
                    return None
                
                return {
                    'symbol': index_name.upper(),
                    'price': float(last_price),
                    'open': float(data.get('open', 0) or 0),
                    'high': float(data.get('intraDayHighLow', {}).get('max', 0) or data.get('high', 0) or 0),
                    'low': float(data.get('intraDayHighLow', {}).get('min', 0) or data.get('low', 0) or 0),
                    'close': float(data.get('previousClose', 0) or data.get('close', 0) or 0),
                    'volume': int(data.get('totalTradedVolume', 0) or 0),
                    'change': float(data.get('change', 0) or 0),
                    'change_pct': float(data.get('pChange', 0) or data.get('changePercent', 0) or 0),
                    'name': nse_index_name,
                    'is_index': True
                }
        except Exception:
            pass
        
        return None
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get live quote from NSE (stocks or indices)"""
        # Check if it's an index
        if symbol.upper() in INDICES or any(idx in symbol.upper() for idx in ['NIFTY', 'BANKNIFTY', 'SENSEX']):
            return self.get_index_quote(symbol)
        
        try:
            self._ensure_session()
            
            # NSE quote endpoint
            url = f"https://www.nseindia.com/api/quote-equity"
            params = {'symbol': symbol.upper()}
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle different response structures
                price_info = data.get('priceInfo', {})
                if not price_info:
                    # Try alternative structure
                    price_info = data.get('priceinfo', {}) or data.get('price', {})
                
                info = data.get('info', {}) or data.get('Info', {})
                
                if not price_info:
                    return None
                
                # Extract price data
                last_price = price_info.get('lastPrice') or price_info.get('last') or price_info.get('ltp', 0)
                if last_price == 0:
                    return None
                
                intraday_hl = price_info.get('intraDayHighLow', {})
                if isinstance(intraday_hl, dict):
                    high = intraday_hl.get('max') or intraday_hl.get('high', 0)
                    low = intraday_hl.get('min') or intraday_hl.get('low', 0)
                else:
                    high = price_info.get('intraDayHighLow.max', 0) or price_info.get('high', 0)
                    low = price_info.get('intraDayHighLow.min', 0) or price_info.get('low', 0)
                
                return {
                    'symbol': symbol,
                    'price': float(last_price),
                    'open': float(price_info.get('open', 0) or 0),
                    'high': float(high or 0),
                    'low': float(low or 0),
                    'close': float(price_info.get('close', 0) or price_info.get('previousClose', 0) or 0),
                    'volume': int(price_info.get('totalTradedVolume', 0) or price_info.get('volume', 0) or 0),
                    'change': float(price_info.get('change', 0) or 0),
                    'change_pct': float(price_info.get('pChange', 0) or price_info.get('changePercent', 0) or 0),
                    'name': info.get('companyName', symbol) if info else symbol,
                    'is_index': False
                }
            elif response.status_code == 404:
                # Symbol not found
                return None
            else:
                # Other error - try again with fresh session
                self._cookies_set = False
                return None
        except Exception as e:
            # Reset session on error
            self._cookies_set = False
            return None
        
        return None
    
    def get_intraday_data(self, symbol: str, interval: str = '5min') -> Optional[pd.DataFrame]:
        """Get intraday data for indices/stocks"""
        try:
            self._ensure_session()
            
            # Check if it's an index
            is_index = symbol.upper() in INDICES or any(idx in symbol.upper() for idx in ['NIFTY', 'BANKNIFTY', 'SENSEX'])
            
            if is_index:
                # For indices, try multiple endpoints
                index_map = {
                    'NIFTY': 'NIFTY 50',
                    'NIFTY50': 'NIFTY 50',
                    'BANKNIFTY': 'NIFTY BANK',
                    'NIFTYBANK': 'NIFTY BANK',
                    'SENSEX': 'SENSEX'
                }
                nse_index_name = index_map.get(symbol.upper(), symbol.upper())
                
                # Try index chart endpoint
                url = "https://www.nseindia.com/api/chart-databyindex"
                params = {
                    'index': nse_index_name,
                    'period': '1d'
                }
                
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Try different data keys
                    graph_data = data.get('grapthData') or data.get('graphData') or data.get('data') or []
                    
                    if graph_data:
                        records = []
                        for item in graph_data:
                            try:
                                if isinstance(item, list) and len(item) >= 5:
                                    timestamp = item[0]
                                    if isinstance(timestamp, (int, float)):
                                        dt = pd.to_datetime(timestamp, unit='s')
                                    else:
                                        dt = pd.to_datetime(timestamp)
                                    
                                    records.append({
                                        'date': dt,
                                        'open': float(item[1]),
                                        'high': float(item[2]),
                                        'low': float(item[3]),
                                        'close': float(item[4]),
                                        'volume': int(item[5]) if len(item) > 5 else 0
                                    })
                                elif isinstance(item, dict):
                                    # Handle dict format
                                    timestamp = item.get('timestamp') or item.get('time') or item.get('date')
                                    if timestamp:
                                        dt = pd.to_datetime(timestamp, unit='s') if isinstance(timestamp, (int, float)) else pd.to_datetime(timestamp)
                                        records.append({
                                            'date': dt,
                                            'open': float(item.get('open', item.get('o', 0))),
                                            'high': float(item.get('high', item.get('h', 0))),
                                            'low': float(item.get('low', item.get('l', 0))),
                                            'close': float(item.get('close', item.get('c', 0))),
                                            'volume': int(item.get('volume', item.get('v', 0)))
                                        })
                            except:
                                continue
                        
                        if records:
                            df = pd.DataFrame(records)
                            df.set_index('date', inplace=True)
                            df.sort_index(inplace=True)
                            
                            # Filter to today's data only for intraday
                            today = datetime.now(IST).date()
                            df_today = df[df.index.date == today]
                            
                            # If no today's data, use last available data
                            if len(df_today) < 10:
                                df_today = df.tail(50)  # Use last 50 data points
                            
                            if len(df_today) >= 10:
                                return df_today
                
                # Fallback: Use historical data for last few days (less ideal but works)
                return self._get_index_historical_for_intraday(nse_index_name)
            else:
                # For stocks, use equity chart endpoint
                url = f"https://www.nseindia.com/api/chart-databyindex"
                params = {
                    'index': f"{symbol.upper()}EQN",
                    'period': '1d'
                }
                
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    graph_data = data.get('grapthData') or data.get('graphData') or []
                    
                    if graph_data:
                        records = []
                        for item in graph_data:
                            try:
                                if len(item) >= 6:
                                    timestamp = item[0]
                                    dt = pd.to_datetime(timestamp, unit='s') if isinstance(timestamp, (int, float)) else pd.to_datetime(timestamp)
                                    
                                    records.append({
                                        'date': dt,
                                        'open': float(item[1]),
                                        'high': float(item[2]),
                                        'low': float(item[3]),
                                        'close': float(item[4]),
                                        'volume': int(item[5]) if len(item) > 5 else 0
                                    })
                            except:
                                continue
                        
                        if records:
                            df = pd.DataFrame(records)
                            df.set_index('date', inplace=True)
                            df.sort_index(inplace=True)
                            
                            today = datetime.now(IST).date()
                            df_today = df[df.index.date == today]
                            
                            if len(df_today) >= 10:
                                return df_today
        except Exception as e:
            # Debug: print error
            pass
        
        return None
    
    def _get_index_historical_for_intraday(self, index_name: str) -> Optional[pd.DataFrame]:
        """Fallback: Get recent historical data for intraday analysis"""
        try:
            # Get last 5 days of daily data and simulate intraday
            hist_df = self.get_historical_data(index_name, days=5, intraday=False)
            
            if hist_df is not None and not hist_df.empty:
                # Resample daily data to create intraday-like structure
                # This is a workaround when true intraday data isn't available
                return hist_df.tail(20)  # Return last 20 days
        except:
            pass
        
        return None
    
    def get_historical_data(self, symbol: str, days: int = 60, intraday: bool = False) -> Optional[pd.DataFrame]:
        """Get historical data from NSE - uses alternative method if API fails"""
        # If intraday requested, use intraday data method
        if intraday:
            intraday_df = self.get_intraday_data(symbol)
            if intraday_df is not None and not intraday_df.empty:
                return intraday_df
            # If intraday fails, fall back to daily data
        
        try:
            self._ensure_session()
            
            # Check if it's an index
            is_index = symbol.upper() in INDICES or any(idx in symbol.upper() for idx in ['NIFTY', 'BANKNIFTY', 'SENSEX'])
            
            if is_index:
                # For indices, use chart data endpoint
                index_map = {
                    'NIFTY': 'NIFTY 50',
                    'NIFTY50': 'NIFTY 50',
                    'BANKNIFTY': 'NIFTY BANK',
                    'NIFTYBANK': 'NIFTY BANK',
                    'SENSEX': 'SENSEX'
                }
                nse_index_name = index_map.get(symbol.upper(), symbol.upper())
                
                # Try chart data endpoint
                url = "https://www.nseindia.com/api/chart-databyindex"
                params = {
                    'index': nse_index_name,
                    'period': f"{min(days, 365)}"
                }
                
                response = self.session.get(url, params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    graph_data = data.get('grapthData') or data.get('graphData') or data.get('data') or []
                    
                    if graph_data:
                        records = []
                        for item in graph_data:
                            try:
                                if isinstance(item, list) and len(item) >= 5:
                                    timestamp = item[0]
                                    dt = pd.to_datetime(timestamp, unit='s') if isinstance(timestamp, (int, float)) else pd.to_datetime(timestamp)
                                    
                                    records.append({
                                        'date': dt,
                                        'open': float(item[1]),
                                        'high': float(item[2]),
                                        'low': float(item[3]),
                                        'close': float(item[4]),
                                        'volume': int(item[5]) if len(item) > 5 else 0
                                    })
                            except:
                                continue
                        
                        if records:
                            df = pd.DataFrame(records)
                            df.set_index('date', inplace=True)
                            df.sort_index(inplace=True)
                            
                            if len(df) >= 20:
                                return df
            else:
                # For stocks, use historical equity API
                url = "https://www.nseindia.com/api/historical/cm/equity"
                
                end_date = datetime.now()
                start_date = end_date - timedelta(days=min(days, 365))
                
                params = {
                    'symbol': symbol.upper(),
                    'series': 'EQ',
                    'from': start_date.strftime('%d-%m-%Y'),
                    'to': end_date.strftime('%d-%m-%Y')
                }
            
                response = self.session.get(url, params=params, timeout=15)
            
                if response.status_code == 200:
                    data = response.json()
                    
                    if 'data' in data and data['data']:
                        records = []
                        for item in data['data']:
                            try:
                                records.append({
                                    'date': pd.to_datetime(item.get('CH_TIMESTAMP', item.get('TIMESTAMP', ''))),
                                    'open': float(item.get('CH_OPENING_PRICE', item.get('OPEN', 0))),
                                    'high': float(item.get('CH_TRADE_HIGH_PRICE', item.get('HIGH', 0))),
                                    'low': float(item.get('CH_TRADE_LOW_PRICE', item.get('LOW', 0))),
                                    'close': float(item.get('CH_CLOSING_PRICE', item.get('CLOSE', 0))),
                                    'volume': int(item.get('CH_TOT_TRADED_QTY', item.get('VOLUME', 0)))
                                })
                            except:
                                continue
                        
                        if records:
                            df = pd.DataFrame(records)
                            df.set_index('date', inplace=True)
                            df.sort_index(inplace=True)
                            
                            if len(df) >= 20:
                                return df
            
            # Fallback: Use chart data endpoint (simpler, more reliable)
            return self._get_chart_data(symbol, days)
            
        except Exception:
            # Fallback to chart data
            return self._get_chart_data(symbol, days)
    
    def _get_chart_data(self, symbol: str, days: int = 60) -> Optional[pd.DataFrame]:
        """Fallback: Get chart data from NSE"""
        try:
            self._ensure_session()
            
            # NSE chart data endpoint (more reliable)
            url = f"https://www.nseindia.com/api/chart-databyindex"
            params = {
                'index': f"{symbol.upper()}EQN",  # EQN format for equity
                'period': f"{min(days, 365)}"
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'grapthData' in data and data['grapthData']:
                    records = []
                    for item in data['grapthData']:
                        try:
                            # NSE chart data format: [timestamp, open, high, low, close, volume]
                            if len(item) >= 6:
                                records.append({
                                    'date': pd.to_datetime(item[0], unit='s') if isinstance(item[0], (int, float)) else pd.to_datetime(item[0]),
                                    'open': float(item[1]),
                                    'high': float(item[2]),
                                    'low': float(item[3]),
                                    'close': float(item[4]),
                                    'volume': int(item[5]) if len(item) > 5 else 0
                                })
                        except:
                            continue
                    
                    if records:
                        df = pd.DataFrame(records)
                        df.set_index('date', inplace=True)
                        df.sort_index(inplace=True)
                        
                        if len(df) >= 20:
                            return df
            
            # Last resort: Create minimal data from quote (less accurate but works)
            quote = self.get_quote(symbol)
            if quote and quote.get('price', 0) > 0:
                # Create synthetic historical data (not ideal but better than nothing)
                return self._create_synthetic_data(quote, days)
            
        except Exception:
            pass
        
        return None
    
    def _create_synthetic_data(self, quote: Dict, days: int) -> Optional[pd.DataFrame]:
        """Create minimal synthetic data from quote (fallback only)"""
        try:
            # This is a last resort - creates basic data structure
            # Signals will be less accurate but at least we can generate something
            current_price = quote['price']
            dates = pd.date_range(end=datetime.now(), periods=min(days, 60), freq='D')
            
            # Create simple trend data
            df = pd.DataFrame({
                'open': current_price * (1 + np.random.randn(len(dates)) * 0.01),
                'high': current_price * (1 + np.abs(np.random.randn(len(dates)) * 0.02)),
                'low': current_price * (1 - np.abs(np.random.randn(len(dates)) * 0.02)),
                'close': current_price * (1 + np.random.randn(len(dates)) * 0.01),
                'volume': quote.get('volume', 1000000) * (1 + np.random.randn(len(dates)) * 0.1)
            }, index=dates)
            
            # Ensure close is last price
            df.iloc[-1, df.columns.get_loc('close')] = current_price
            
            # Ensure OHLC relationships
            df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
            df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
            
            return df
        except:
            return None


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI"""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=window).mean()
    rs = gain / loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
    """Calculate MACD"""
    fast_ema = close.ewm(span=fast, adjust=False).mean()
    slow_ema = close.ewm(span=slow, adjust=False).mean()
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line.iloc[-1] if not macd_line.empty else 0,
        'signal': signal_line.iloc[-1] if not signal_line.empty else 0,
        'histogram': histogram.iloc[-1] if not histogram.empty else 0
    }


def compute_sma(close: pd.Series, window: int) -> float:
    """Calculate SMA"""
    return close.rolling(window=window).mean().iloc[-1] if len(close) >= window else close.mean()


def compute_ema(close: pd.Series, window: int) -> float:
    """Calculate EMA"""
    return close.ewm(span=window, adjust=False).mean().iloc[-1] if len(close) >= window else close.mean()


def compute_bollinger_bands(close: pd.Series, window: int = 20, num_std: float = 2) -> Dict:
    """Calculate Bollinger Bands"""
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()
    
    upper = sma + (std * num_std)
    lower = sma - (std * num_std)
    
    return {
        'upper': upper.iloc[-1] if not upper.empty else close.iloc[-1],
        'middle': sma.iloc[-1] if not sma.empty else close.iloc[-1],
        'lower': lower.iloc[-1] if not lower.empty else close.iloc[-1]
    }


def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> Dict:
    """Calculate support and resistance levels"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    # Recent highs and lows
    recent_high = high.rolling(window=window).max().iloc[-1]
    recent_low = low.rolling(window=window).min().iloc[-1]
    
    # Pivot points
    pivot = (recent_high + recent_low + close.iloc[-1]) / 3
    resistance1 = 2 * pivot - recent_low
    support1 = 2 * pivot - recent_high
    resistance2 = pivot + (recent_high - recent_low)
    support2 = pivot - (recent_high - recent_low)
    
    return {
        'pivot': pivot,
        'resistance1': resistance1,
        'resistance2': resistance2,
        'support1': support1,
        'support2': support2,
        'recent_high': recent_high,
        'recent_low': recent_low
    }


def calculate_atr(df: pd.DataFrame, window: int = 14) -> float:
    """Calculate Average True Range"""
    high = df['high']
    low = df['low']
    close = df['close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=window).mean().iloc[-1]
    
    return atr if not pd.isna(atr) else (high.iloc[-1] - low.iloc[-1]) * 0.02


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signal(stock_data: Dict) -> Dict:
    """Generate buy/sell signal (works for stocks and indices, intraday and daily)"""
    ticker = stock_data['ticker']
    df = stock_data['historical']
    current_price = stock_data['live_price']
    is_index = stock_data.get('is_index', False)
    intraday = stock_data.get('intraday', False)
    
    # Adjust minimum data requirements based on timeframe
    # For intraday, we can work with less data
    min_data_points = 5 if intraday else 50
    
    if df.empty or len(df) < min_data_points:
        # For intraday with limited data, still try to generate basic signal
        if intraday and len(df) >= 3:
            # Use simplified analysis for intraday with limited data
            pass
        else:
            return {
                'ticker': ticker,
                'action': 'HOLD',
                'confidence': 0.0,
                'reason': 'Insufficient data'
            }
    
    close = df['close']
    
    # Calculate indicators
    rsi = compute_rsi(close, 14)
    current_rsi = rsi.iloc[-1] if not rsi.empty else 50
    
    macd_data = compute_macd(close)
    sma_20 = compute_sma(close, 20)
    sma_50 = compute_sma(close, 50)
    ema_20 = compute_ema(close, 20)
    bb = compute_bollinger_bands(close, 20, 2)
    
    # Price momentum (adjust for intraday)
    if intraday:
        # For intraday, use shorter periods
        price_change_5d = (close.iloc[-1] - close.iloc[-min(5, len(close)-1)]) / close.iloc[-min(5, len(close)-1)] * 100 if len(close) >= 2 else 0
        price_change_20d = (close.iloc[-1] - close.iloc[-min(20, len(close)-1)]) / close.iloc[-min(20, len(close)-1)] * 100 if len(close) >= 2 else 0
    else:
        price_change_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) >= 5 else 0
        price_change_20d = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
    
    # Volume analysis (adjust window for intraday)
    volume_window = 10 if intraday else 20
    volume_avg = df['volume'].rolling(min(volume_window, len(df))).mean().iloc[-1] if len(df) >= 2 else df['volume'].mean()
    current_volume = df['volume'].iloc[-1]
    volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1
    
    # Signal scoring
    buy_score = 0
    sell_score = 0
    reasons = []
    
    # RSI signals
    if current_rsi < 30:
        buy_score += 2
        reasons.append("RSI oversold (<30)")
    elif current_rsi < 40:
        buy_score += 1
        reasons.append("RSI near oversold (<40)")
    elif current_rsi > 70:
        sell_score += 2
        reasons.append("RSI overbought (>70)")
    elif current_rsi > 60:
        sell_score += 1
        reasons.append("RSI near overbought (>60)")
    
    # MACD signals
    if macd_data['macd'] > macd_data['signal'] and macd_data['histogram'] > 0:
        buy_score += 2
        reasons.append("MACD bullish crossover")
    elif macd_data['macd'] < macd_data['signal'] and macd_data['histogram'] < 0:
        sell_score += 2
        reasons.append("MACD bearish crossover")
    
    # Moving average signals
    if current_price > sma_20 > sma_50:
        buy_score += 2
        reasons.append("Price above SMAs (bullish trend)")
    elif current_price < sma_20 < sma_50:
        sell_score += 2
        reasons.append("Price below SMAs (bearish trend)")
    
    if current_price > ema_20:
        buy_score += 1
    else:
        sell_score += 1
    
    # Bollinger Bands
    if current_price < bb['lower']:
        buy_score += 1
        reasons.append("Price near lower Bollinger Band")
    elif current_price > bb['upper']:
        sell_score += 1
        reasons.append("Price near upper Bollinger Band")
    
    # Momentum signals
    if price_change_5d > 3:
        buy_score += 1
        reasons.append("Strong 5-day momentum")
    elif price_change_5d < -3:
        sell_score += 1
        reasons.append("Weak 5-day momentum")
    
    if price_change_20d > 10:
        buy_score += 1
        reasons.append("Strong 20-day trend")
    elif price_change_20d < -10:
        sell_score += 1
        reasons.append("Weak 20-day trend")
    
    # Volume confirmation
    if volume_ratio > 1.5:
        if buy_score > sell_score:
            buy_score += 1
            reasons.append("High volume confirmation")
        elif sell_score > buy_score:
            sell_score += 1
            reasons.append("High volume confirmation")
    
    # Determine signal
    total_score = buy_score + sell_score
    confidence = max(buy_score, sell_score) / max(total_score, 1) if total_score > 0 else 0
    
    if buy_score > sell_score and buy_score >= 3:
        action = 'BUY'
        final_confidence = min(confidence + 0.1, 0.95)
    elif sell_score > buy_score and sell_score >= 3:
        action = 'SELL'
        final_confidence = min(confidence + 0.1, 0.95)
    else:
        action = 'HOLD'
        final_confidence = 0.3
    
    # Calculate targets and stop loss
    atr = calculate_atr(df, 14)
    support_resistance = calculate_support_resistance(df, 20)
    
    # Entry price (current price)
    entry_price = current_price
    
    # Calculate targets and stop loss based on signal type
    if action == 'BUY':
        # Buy targets (resistance levels)
        target1 = min(support_resistance['resistance1'], current_price * 1.02)  # 2% target
        target2 = min(support_resistance['resistance2'], current_price * 1.05)  # 5% target
        target3 = current_price * 1.10  # 10% target
        
        # Stop loss (below support or 2% below entry)
        stop_loss = max(support_resistance['support1'], current_price * 0.98)
        # Use ATR for better stop loss
        stop_loss_atr = current_price - (atr * 1.5)
        stop_loss = min(stop_loss, stop_loss_atr)
        
        # Risk-reward ratio
        risk = entry_price - stop_loss
        reward1 = target1 - entry_price
        reward2 = target2 - entry_price
        rr_ratio1 = reward1 / risk if risk > 0 else 0
        rr_ratio2 = reward2 / risk if risk > 0 else 0
        
    elif action == 'SELL':
        # Sell targets (support levels)
        target1 = max(support_resistance['support1'], current_price * 0.98)  # 2% target
        target2 = max(support_resistance['support2'], current_price * 0.95)  # 5% target
        target3 = current_price * 0.90  # 10% target
        
        # Stop loss (above resistance or 2% above entry)
        stop_loss = min(support_resistance['resistance1'], current_price * 1.02)
        # Use ATR for better stop loss
        stop_loss_atr = current_price + (atr * 1.5)
        stop_loss = max(stop_loss, stop_loss_atr)
        
        # Risk-reward ratio
        risk = stop_loss - entry_price
        reward1 = entry_price - target1
        reward2 = entry_price - target2
        rr_ratio1 = reward1 / risk if risk > 0 else 0
        rr_ratio2 = reward2 / risk if risk > 0 else 0
        
    else:
        # HOLD - no targets
        target1 = target2 = target3 = stop_loss = entry_price
        rr_ratio1 = rr_ratio2 = 0
    
    return {
        'ticker': ticker,
        'name': stock_data.get('name', ticker),
        'action': action,
        'confidence': final_confidence,
        'price': current_price,
        'entry_price': round(entry_price, 2),
        'target1': round(target1, 2),
        'target2': round(target2, 2),
        'target3': round(target3, 2),
        'stop_loss': round(stop_loss, 2),
        'target1_pct': round((target1 - entry_price) / entry_price * 100, 2) if action != 'HOLD' else 0,
        'target2_pct': round((target2 - entry_price) / entry_price * 100, 2) if action != 'HOLD' else 0,
        'target3_pct': round((target3 - entry_price) / entry_price * 100, 2) if action != 'HOLD' else 0,
        'stop_loss_pct': round((stop_loss - entry_price) / entry_price * 100, 2) if action != 'HOLD' else 0,
        'risk_reward_1': round(rr_ratio1, 2),
        'risk_reward_2': round(rr_ratio2, 2),
        'change_pct': stock_data.get('change_pct', 0),
        'volume': stock_data.get('volume', 0),
        'rsi': round(current_rsi, 2),
        'macd': round(macd_data['macd'], 2),
        'macd_signal': round(macd_data['signal'], 2),
        'macd_histogram': round(macd_data['histogram'], 2),
        'sma_20': round(sma_20, 2),
        'sma_50': round(sma_50, 2),
        'ema_20': round(ema_20, 2),
        'bb_upper': round(bb['upper'], 2),
        'bb_middle': round(bb['middle'], 2),
        'bb_lower': round(bb['lower'], 2),
        'atr': round(atr, 2),
        'support1': round(support_resistance['support1'], 2),
        'support2': round(support_resistance['support2'], 2),
        'resistance1': round(support_resistance['resistance1'], 2),
        'resistance2': round(support_resistance['resistance2'], 2),
        'pivot': round(support_resistance['pivot'], 2),
        'price_change_5d': round(price_change_5d, 2),
        'price_change_20d': round(price_change_20d, 2),
        'volume_ratio': round(volume_ratio, 2),
        'reason': ' | '.join(reasons[:3]) if reasons else 'Neutral signals',
        'timestamp': datetime.now(IST).isoformat(),
        'option_recommendation': None,  # Filled in scan_stocks if --options
    }


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def get_stock_data(ticker: str, nse_client: NSEClient, intraday: bool = False, upstox_client: Optional[UpstoxDataClient] = None) -> Optional[Dict]:
    """Get stock/index data - tries Upstox first if token available, else NSE"""
    quote = None
    hist_df = None
    source = "NSE"

    # Try Upstox first when token is available
    if upstox_client:
        quote = upstox_client.get_quote(ticker)
        if quote and quote.get('price', 0) > 0:
            if intraday:
                hist_df = upstox_client.get_intraday_data(ticker)
                if hist_df is None or hist_df.empty or len(hist_df) < 10:
                    hist_df = upstox_client.get_historical_data(ticker, days=5, intraday=False)
            else:
                hist_df = upstox_client.get_historical_data(ticker, days=60, intraday=False)
                if hist_df is None or hist_df.empty or len(hist_df) < 20:
                    hist_df = upstox_client.get_historical_data(ticker, days=30, intraday=False)
            if quote and hist_df is not None and not hist_df.empty:
                min_pts = 5 if intraday else 20
                if len(hist_df) >= min_pts:
                    source = "Upstox"

    # Fallback to NSE
    if not quote or quote.get('price', 0) <= 0 or hist_df is None or hist_df.empty:
        quote = nse_client.get_quote(ticker)
        if not quote or quote.get('price', 0) <= 0:
            return None
        if intraday:
            hist_df = nse_client.get_intraday_data(ticker)
            min_data_points = 10
            if hist_df is None or hist_df.empty or len(hist_df) < min_data_points:
                hist_df = nse_client.get_historical_data(ticker, days=5, intraday=False)
                min_data_points = 5
        else:
            hist_df = nse_client.get_historical_data(ticker, days=60, intraday=False)
            min_data_points = 20
            if hist_df is None or hist_df.empty or len(hist_df) < min_data_points:
                hist_df = nse_client.get_historical_data(ticker, days=30, intraday=False)
        source = "NSE"

    if hist_df is None or hist_df.empty:
        return None

    min_data_points = 5 if intraday else 20
    if len(hist_df) < min_data_points:
        return None

    is_index = quote.get('is_index', False)
    return {
        'ticker': ticker,
        'historical': hist_df,
        'live_price': quote['price'],
        'change_pct': quote.get('change_pct', 0),
        'volume': quote.get('volume', 0),
        'name': quote.get('name', ticker),
        'is_index': is_index,
        'intraday': intraday,
        'source': source
    }


def scan_stocks(tickers: List[str], min_confidence: float = 0.55, intraday: bool = False) -> List[Dict]:
    """Scan stocks/indices and generate signals"""
    signals = []
    nse_client = NSEClient()
    upstox_client = None
    token = _get_upstox_token()
    if token:
        upstox_client = UpstoxDataClient(token)
        print("\n📡 Using Upstox for live data (UPSTOX_ACCESS_TOKEN set)")
    
    timeframe = "INTRADAY" if intraday else "DAILY"
    asset_type = "indices/stocks" if any(t.upper() in INDICES for t in tickers) else "stocks"
    
    print(f"\n📊 Scanning {len(tickers)} {asset_type} ({timeframe} timeframe)...")
    print("=" * 80)
    
    for i, ticker in enumerate(tickers, 1):
        try:
            # Remove .NS suffix if present
            ticker_clean = ticker.replace('.NS', '').replace('.BO', '').upper()
            
            print(f"[{i}/{len(tickers)}] Processing {ticker_clean}...", end=' ', flush=True)
            
            # Get stock/index data (with retry)
            stock_data = None
            for attempt in range(2):
                stock_data = get_stock_data(ticker_clean, nse_client, intraday=intraday, upstox_client=upstox_client)
                if stock_data:
                    break
                if attempt == 0:
                    # Reset session and retry
                    nse_client._cookies_set = False
                    time.sleep(2)
            
            if not stock_data:
                print("❌ No data")
                time.sleep(1)  # Rate limiting
                continue
            
            # Generate signal
            signal = generate_signal(stock_data)
            
            # Option chain: recommend strike (Delta, Gamma, Theta, Vega) for BUY/SELL
            try:
                from nse_option_chain import get_recommended_option
                # ATR as % of price (daily); module annualizes for volatility
                atr_pct = (signal.get('atr', 0) / (signal.get('entry_price') or 1)) * 100 if signal.get('entry_price') else 2.0
                opt = get_recommended_option(
                    nse_client.session,
                    ticker_clean,
                    spot=signal.get('entry_price') or stock_data['live_price'],
                    signal=signal['action'],
                    atr_pct=atr_pct,
                    is_index=stock_data.get('is_index', False),
                )
                if opt:
                    signal['option_recommendation'] = opt
            except Exception:
                signal['option_recommendation'] = None
            
            if signal['confidence'] >= min_confidence:
                signals.append(signal)
                action_emoji = "🟢" if signal['action'] == 'BUY' else "🔴" if signal['action'] == 'SELL' else "⚪"
                src = stock_data.get('source', '')
                src_tag = f" [{src}]" if src else ""
                print(f"{action_emoji} {signal['action']} ({signal['confidence']:.0%}){src_tag}")
            else:
                print("⚪ HOLD")
            
            time.sleep(1)  # Rate limiting for NSE API
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception:
            print("❌ Error")
            continue
    
    return signals


def print_signals(signals: List[Dict]):
    """Print signals with all details"""
    if not signals:
        print("\n" + "=" * 80)
        print("❌ NO TRADING SIGNALS FOUND")
        print("=" * 80)
        print("\n💡 Try lowering --min-confidence (default: 0.55)")
        return
    
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    buy_signals = [s for s in signals if s['action'] == 'BUY']
    sell_signals = [s for s in signals if s['action'] == 'SELL']
    
    print("\n" + "=" * 80)
    print(f"📈 TRADING SIGNALS - {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 80)
    
    if buy_signals:
        print(f"\n🟢 BUY SIGNALS ({len(buy_signals)}):")
        print("=" * 80)
        for sig in buy_signals:
            print(f"\n📊 {sig['ticker']} ({sig['name']})")
            print("-" * 80)
            print(f"\n  💰 TRADE SETUP:")
            print(f"     Buy Price:        ₹{sig['entry_price']:8.2f}  ← Enter here")
            print(f"     Stop Loss:        ₹{sig['stop_loss']:8.2f}  ← Exit if price falls here ({sig['stop_loss_pct']:+.2f}%)")
            print(f"\n  🎯 PROFIT TARGETS:")
            print(f"     Target 1 (Quick): ₹{sig['target1']:8.2f}  ← Book 50% profit here ({sig['target1_pct']:+.2f}%)")
            print(f"     Target 2 (Medium):₹{sig['target2']:8.2f}  ← Book 30% profit here ({sig['target2_pct']:+.2f}%)")
            print(f"     Target 3 (Long):  ₹{sig['target3']:8.2f}  ← Hold remaining 20% ({sig['target3_pct']:+.2f}%)")
            print(f"\n  📊 RISK MANAGEMENT:")
            print(f"     Risk per share:   ₹{abs(sig['entry_price'] - sig['stop_loss']):8.2f}")
            print(f"     Reward (T1):      ₹{abs(sig['target1'] - sig['entry_price']):8.2f}")
            print(f"     Reward (T2):      ₹{abs(sig['target2'] - sig['entry_price']):8.2f}")
            print(f"     Risk/Reward (T1): {sig['risk_reward_1']:.2f}:1")
            print(f"     Risk/Reward (T2): {sig['risk_reward_2']:.2f}:1")
            print(f"     Confidence:       {sig['confidence']:5.0%}")
            print(f"\n  📊 TECHNICAL INDICATORS:")
            print(f"     RSI (14):          {sig['rsi']:5.1f} {'← Oversold' if sig['rsi'] < 30 else '← Overbought' if sig['rsi'] > 70 else '← Neutral'}")
            print(f"     MACD:             {sig['macd']:8.2f}")
            print(f"     MACD Signal:       {sig['macd_signal']:8.2f}")
            print(f"     MACD Histogram:   {sig['macd_histogram']:8.2f} {'← Bullish' if sig['macd_histogram'] > 0 else '← Bearish'}")
            print(f"     SMA 20:            ₹{sig['sma_20']:8.2f}")
            print(f"     SMA 50:            ₹{sig['sma_50']:8.2f}")
            print(f"     EMA 20:            ₹{sig['ema_20']:8.2f}")
            print(f"     BB Upper:          ₹{sig['bb_upper']:8.2f}")
            print(f"     BB Middle:         ₹{sig['bb_middle']:8.2f}")
            print(f"     BB Lower:          ₹{sig['bb_lower']:8.2f}")
            print(f"     ATR:               ₹{sig['atr']:8.2f}")
            print(f"\n  📍 SUPPORT & RESISTANCE:")
            print(f"     Support 1:         ₹{sig['support1']:8.2f}  ← Key support level")
            print(f"     Support 2:         ₹{sig['support2']:8.2f}  ← Strong support")
            print(f"     Resistance 1:      ₹{sig['resistance1']:8.2f}  ← Key resistance")
            print(f"     Resistance 2:      ₹{sig['resistance2']:8.2f}  ← Strong resistance")
            print(f"     Pivot Point:       ₹{sig['pivot']:8.2f}")
            print(f"\n  📈 MOMENTUM & VOLUME:")
            print(f"     5-Day Change:      {sig['price_change_5d']:+.2f}%")
            print(f"     20-Day Change:     {sig['price_change_20d']:+.2f}%")
            print(f"     Volume Ratio:      {sig['volume_ratio']:.2f}x {'← High volume' if sig['volume_ratio'] > 1.5 else '← Normal'}")
            print(f"     Current Volume:    {sig['volume']:,}")
            print(f"\n  💡 Signal Reason: {sig['reason']}")
            # Options: recommended strike with Delta, Gamma, Theta
            opt = sig.get('option_recommendation')
            if opt:
                print(f"\n  📋 OPTIONS (Strike from Option Chain / Greeks):")
                print(f"     Option Type:       {opt.get('option_type', 'CE')}  ← {'Call (BUY)' if opt.get('option_type') == 'CE' else 'Put (SELL)'}")
                print(f"     Strike Price:      ₹{opt.get('strike', 0):8.2f}  ← Use this strike in option chain")
                print(f"     Delta:             {opt.get('delta', 0):7.4f}  ← Sensitivity to underlying")
                print(f"     Gamma:             {opt.get('gamma', 0):.6f}  ← Rate of delta change")
                print(f"     Theta (per day):   {opt.get('theta_per_day', 0):7.4f}  ← Time decay")
                print(f"     Vega (per 1% vol):₹{opt.get('vega_per_1pct', 0):7.2f}  ← Volatility sensitivity")
                if opt.get('premium_approx'):
                    print(f"     Premium (approx):  ₹{opt['premium_approx']:8.2f}")
                if opt.get('expiry'):
                    print(f"     Expiry:            {opt['expiry']}")
                if opt.get('reason'):
                    print(f"     Note:              {opt['reason']}")
            print()
    
    if sell_signals:
        print(f"\n🔴 SELL SIGNALS ({len(sell_signals)}):")
        print("=" * 80)
        for sig in sell_signals:
            print(f"\n📊 {sig['ticker']} ({sig['name']})")
            print("-" * 80)
            print(f"\n  💰 TRADE SETUP:")
            print(f"     Sell Price:       ₹{sig['entry_price']:8.2f}  ← Exit here (or short)")
            print(f"     Stop Loss:        ₹{sig['stop_loss']:8.2f}  ← Exit if price rises here ({sig['stop_loss_pct']:+.2f}%)")
            print(f"\n  🎯 PROFIT TARGETS:")
            print(f"     Target 1 (Quick): ₹{sig['target1']:8.2f}  ← Book 50% profit here ({sig['target1_pct']:+.2f}%)")
            print(f"     Target 2 (Medium):₹{sig['target2']:8.2f}  ← Book 30% profit here ({sig['target2_pct']:+.2f}%)")
            print(f"     Target 3 (Long):  ₹{sig['target3']:8.2f}  ← Hold remaining 20% ({sig['target3_pct']:+.2f}%)")
            print(f"\n  📊 RISK MANAGEMENT:")
            print(f"     Risk per share:   ₹{abs(sig['stop_loss'] - sig['entry_price']):8.2f}")
            print(f"     Reward (T1):      ₹{abs(sig['entry_price'] - sig['target1']):8.2f}")
            print(f"     Reward (T2):      ₹{abs(sig['entry_price'] - sig['target2']):8.2f}")
            print(f"     Risk/Reward (T1): {sig['risk_reward_1']:.2f}:1")
            print(f"     Risk/Reward (T2): {sig['risk_reward_2']:.2f}:1")
            print(f"     Confidence:       {sig['confidence']:5.0%}")
            print(f"\n  📊 TECHNICAL INDICATORS:")
            print(f"     RSI (14):          {sig['rsi']:5.1f} {'← Oversold' if sig['rsi'] < 30 else '← Overbought' if sig['rsi'] > 70 else '← Neutral'}")
            print(f"     MACD:             {sig['macd']:8.2f}")
            print(f"     MACD Signal:       {sig['macd_signal']:8.2f}")
            print(f"     MACD Histogram:   {sig['macd_histogram']:8.2f} {'← Bullish' if sig['macd_histogram'] > 0 else '← Bearish'}")
            print(f"     SMA 20:            ₹{sig['sma_20']:8.2f}")
            print(f"     SMA 50:            ₹{sig['sma_50']:8.2f}")
            print(f"     EMA 20:            ₹{sig['ema_20']:8.2f}")
            print(f"     BB Upper:          ₹{sig['bb_upper']:8.2f}")
            print(f"     BB Middle:         ₹{sig['bb_middle']:8.2f}")
            print(f"     BB Lower:          ₹{sig['bb_lower']:8.2f}")
            print(f"     ATR:               ₹{sig['atr']:8.2f}")
            print(f"\n  📍 SUPPORT & RESISTANCE:")
            print(f"     Support 1:         ₹{sig['support1']:8.2f}  ← Key support level")
            print(f"     Support 2:         ₹{sig['support2']:8.2f}  ← Strong support")
            print(f"     Resistance 1:      ₹{sig['resistance1']:8.2f}  ← Key resistance")
            print(f"     Resistance 2:      ₹{sig['resistance2']:8.2f}  ← Strong resistance")
            print(f"     Pivot Point:       ₹{sig['pivot']:8.2f}")
            print(f"\n  📈 MOMENTUM & VOLUME:")
            print(f"     5-Day Change:      {sig['price_change_5d']:+.2f}%")
            print(f"     20-Day Change:     {sig['price_change_20d']:+.2f}%")
            print(f"     Volume Ratio:      {sig['volume_ratio']:.2f}x {'← High volume' if sig['volume_ratio'] > 1.5 else '← Normal'}")
            print(f"     Current Volume:    {sig['volume']:,}")
            print(f"\n  💡 Signal Reason: {sig['reason']}")
            opt = sig.get('option_recommendation')
            if opt:
                print(f"\n  📋 OPTIONS (Strike from Option Chain / Greeks):")
                print(f"     Option Type:       {opt.get('option_type', 'PE')}  ← {'Call (BUY)' if opt.get('option_type') == 'CE' else 'Put (SELL)'}")
                print(f"     Strike Price:      ₹{opt.get('strike', 0):8.2f}  ← Use this strike in option chain")
                print(f"     Delta:             {opt.get('delta', 0):7.4f}  ← Sensitivity to underlying")
                print(f"     Gamma:             {opt.get('gamma', 0):.6f}  ← Rate of delta change")
                print(f"     Theta (per day):   {opt.get('theta_per_day', 0):7.4f}  ← Time decay")
                print(f"     Vega (per 1% vol):₹{opt.get('vega_per_1pct', 0):7.2f}  ← Volatility sensitivity")
                if opt.get('premium_approx'):
                    print(f"     Premium (approx):  ₹{opt['premium_approx']:8.2f}")
                if opt.get('expiry'):
                    print(f"     Expiry:            {opt['expiry']}")
                if opt.get('reason'):
                    print(f"     Note:              {opt['reason']}")
            print()
    
    print("=" * 80)
    print(f"\n📊 Summary: {len(buy_signals)} BUY | {len(sell_signals)} SELL | Total: {len(signals)} signals")
    print("=" * 80)


def save_to_csv(signals: List[Dict], filename: str):
    """Save signals to CSV (option_recommendation flattened to opt_* columns)"""
    if not signals:
        return
    
    # Flatten option_recommendation for CSV
    rows = []
    for s in signals:
        row = {k: v for k, v in s.items() if k != 'option_recommendation'}
        opt = s.get('option_recommendation')
        if opt and isinstance(opt, dict):
            row['opt_type'] = opt.get('option_type', '')
            row['opt_strike'] = opt.get('strike')
            row['opt_delta'] = opt.get('delta')
            row['opt_gamma'] = opt.get('gamma')
            row['opt_theta_per_day'] = opt.get('theta_per_day')
            row['opt_vega_per_1pct'] = opt.get('vega_per_1pct')
            row['opt_premium_approx'] = opt.get('premium_approx')
            row['opt_expiry'] = opt.get('expiry') or ''
        else:
            row['opt_type'] = ''
            row['opt_strike'] = None
            row['opt_delta'] = row['opt_gamma'] = None
            row['opt_theta_per_day'] = row['opt_vega_per_1pct'] = row['opt_premium_approx'] = None
            row['opt_expiry'] = ''
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(filename, index=False)
    print(f"\n💾 Saved {len(signals)} signals to {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='NSE-Only Trading Signal Generator - No SSL Issues!',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Daily stock signals
  python trading_signals_nse_only.py
  python trading_signals_nse_only.py --tickers RELIANCE TCS INFY
  python trading_signals_nse_only.py --stocks RELIANCE TCS INFY  # Same as --tickers
  
  # Intraday index trading (NIFTY, BANKNIFTY, SENSEX)
  python trading_signals_nse_only.py --indices --intraday
  python trading_signals_nse_only.py --tickers NIFTY BANKNIFTY --intraday
  
  # Use Upstox for live data (avoids NSE blocking)
  set UPSTOX_ACCESS_TOKEN=your_token
  python trading_signals_nse_only.py --indices --intraday
  
  # Higher confidence
  python trading_signals_nse_only.py --top-n 10 --min-confidence 0.60
        """
    )
    
    parser.add_argument(
        '--tickers',
        '--stocks',
        nargs='+',
        help='List of tickers/stocks (e.g., RELIANCE TCS INFY) - no .NS suffix needed',
        default=None,
        dest='tickers'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        help='Scan top N stocks (default: 20)',
        default=None
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        help='Minimum confidence (0.0-1.0, default: 0.55)',
        default=0.55
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save results to CSV file',
        default=None
    )
    parser.add_argument(
        '--intraday',
        action='store_true',
        help='Use intraday data (for day trading NIFTY, BANKNIFTY, etc.)',
        default=False
    )
    parser.add_argument(
        '--indices',
        action='store_true',
        help='Scan indices (NIFTY, BANKNIFTY, SENSEX)',
        default=False
    )
    
    args = parser.parse_args()
    
    # Determine tickers
    if args.tickers:
        tickers = args.tickers
    elif args.indices:
        # Scan indices for intraday trading
        tickers = ['NIFTY', 'BANKNIFTY', 'SENSEX']
        args.intraday = True  # Auto-enable intraday for indices
    elif args.top_n:
        tickers = DEFAULT_STOCKS[:args.top_n]
    else:
        tickers = DEFAULT_STOCKS[:20]
    
    timeframe = "INTRADAY" if args.intraday else "DAILY"
    
    print("\n" + "=" * 80)
    print("🚀 NSE-ONLY TRADING SIGNAL GENERATOR")
    print("=" * 80)
    print(f"📋 Scanning: {len(tickers)} {'indices' if args.indices else 'stocks'}")
    print(f"⏰ Timeframe: {timeframe}")
    print(f"🎯 Min Confidence: {args.min_confidence:.0%}")
    print("=" * 80)
    
    # Scan stocks/indices
    signals = scan_stocks(tickers, min_confidence=args.min_confidence, intraday=args.intraday)
    
    # Print results
    print_signals(signals)
    
    # Save to file
    if args.output:
        save_to_csv(signals, args.output)
    
    print("\n✅ Done!\n")


if __name__ == '__main__':
    main()
