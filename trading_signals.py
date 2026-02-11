#!/usr/bin/env python3
"""
STANDALONE TRADING SIGNAL GENERATOR
Single file - just run this to get buy/sell signals!

Usage:
    python trading_signals.py
    python trading_signals.py --tickers RELIANCE.NS TCS.NS INFY.NS
    python trading_signals.py --top-n 20
"""

# Fix SSL certificate issues BEFORE importing anything
import ssl
import os
import urllib3

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Now import other modules
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import argparse
from typing import List, Dict, Optional
import pytz

# ============================================================================
# CONFIGURATION
# ============================================================================

IST = pytz.timezone('Asia/Kolkata')
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30

# Popular Indian stocks (default watchlist)
DEFAULT_STOCKS = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
    'BHARTIARTL.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'LICI.NS', 'ITC.NS',
    'HCLTECH.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'LT.NS', 'ASIANPAINT.NS',
    'MARUTI.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'NTPC.NS', 'SUNPHARMA.NS'
]


# ============================================================================
# DATA FETCHING
# ============================================================================

def get_nse_quote(symbol: str) -> Optional[Dict]:
    """Get live quote from NSE API"""
    try:
        import ssl
        import urllib3
        
        # Disable SSL warnings
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        # Set session cookies (disable SSL verification for this)
        try:
            session.get('https://www.nseindia.com', timeout=10, verify=False)
        except:
            pass
        
        # Get quote
        symbol_clean = symbol.replace('.NS', '').replace('.BO', '')
        url = f"https://www.nseindia.com/api/quote-equity"
        params = {'symbol': symbol_clean}
        
        try:
            response = session.get(url, params=params, timeout=15, verify=False)
        except:
            return None
        
        if response.status_code == 200:
            data = response.json()
            price_info = data.get('priceInfo', {})
            info = data.get('info', {})
            
            if not price_info:
                return None
            
            return {
                'symbol': symbol,
                'price': price_info.get('lastPrice', 0),
                'open': price_info.get('open', 0),
                'high': price_info.get('intraDayHighLow', {}).get('max', 0) if isinstance(price_info.get('intraDayHighLow'), dict) else 0,
                'low': price_info.get('intraDayHighLow', {}).get('min', 0) if isinstance(price_info.get('intraDayHighLow'), dict) else 0,
                'close': price_info.get('close', 0),
                'volume': price_info.get('totalTradedVolume', 0),
                'change': price_info.get('change', 0),
                'change_pct': price_info.get('pChange', 0),
                'name': info.get('companyName', symbol) if info else symbol
            }
    except Exception:
        # Silent fail - will use Yahoo Finance fallback
        pass
    
    return None


def get_yahoo_data(ticker: str, days: int = 60) -> Optional[pd.DataFrame]:
    """Get historical data from Yahoo Finance"""
    try:
        import yfinance as yf
        
        # Suppress yfinance warnings
        import warnings
        warnings.filterwarnings('ignore')
        
        # Create ticker with SSL disabled
        stock = yf.Ticker(ticker)
        
        # Try with period first (more reliable)
        df = None
        try:
            df = stock.history(period=f"{min(days, 90)}d", timeout=10)
        except Exception as e1:
            # Fallback to date range
            try:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                df = stock.history(start=start_date, end=end_date, timeout=10)
            except Exception as e2:
                # Last resort: try shorter period
                try:
                    df = stock.history(period="1mo", timeout=10)
                except:
                    return None
        
        if df is None or df.empty or len(df) < 20:
            return None
        
        # Rename columns to lowercase
        df.columns = [col.lower() for col in df.columns]
        
        # Ensure we have required columns
        required = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required):
            return None
        
        # Filter out invalid data
        df = df[df['close'] > 0].copy()
        if df.empty or len(df) < 20:
            return None
        
        return df[required]
    except Exception:
        # Silent fail - will try NSE API or other methods
        return None


def get_stock_data(ticker: str) -> Optional[Dict]:
    """Get live price and historical data for a ticker"""
    # Try NSE API first for live data (no SSL issues)
    quote = get_nse_quote(ticker)
    
    # Get historical data (try Yahoo Finance with SSL disabled)
    hist_df = None
    
    # Try multiple approaches to get historical data
    attempts = [
        (ticker, 60),
        (ticker, 30),
        (ticker.replace('.NS', ''), 30),  # Try without .NS
    ]
    
    for attempt_ticker, days in attempts:
        hist_df = get_yahoo_data(attempt_ticker if '.' in attempt_ticker else f"{attempt_ticker}.NS", days=days)
        if hist_df is not None and not hist_df.empty:
            break
    
    # If still no data, return None
    if hist_df is None or hist_df.empty:
        # If we have NSE quote, we can still generate signal with limited data
        if quote and quote.get('price', 0) > 0:
            # Create minimal historical data from quote
            # This is a fallback - signals will be less accurate
            return None  # Skip if no historical data
        return None
    
    # Get latest price
    if quote and quote.get('price', 0) > 0:
        live_price = quote['price']
        change_pct = quote.get('change_pct', 0)
        volume = quote.get('volume', int(hist_df['volume'].iloc[-1]) if len(hist_df) > 0 else 0)
        name = quote.get('name', ticker)
    else:
        # Use last close from historical data
        live_price = float(hist_df['close'].iloc[-1])
        change_pct = 0
        volume = int(hist_df['volume'].iloc[-1])
        name = ticker
    
    # Combine live quote with historical data
    result = {
        'ticker': ticker,
        'historical': hist_df,
        'live_price': live_price,
        'change_pct': change_pct,
        'volume': volume,
        'name': name
    }
    
    return result


# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================

def compute_rsi(close: pd.Series, window: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index)"""
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
    """Calculate Simple Moving Average"""
    return close.rolling(window=window).mean().iloc[-1] if len(close) >= window else close.mean()


def compute_ema(close: pd.Series, window: int) -> float:
    """Calculate Exponential Moving Average"""
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


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signal(stock_data: Dict) -> Dict:
    """Generate buy/sell signal based on technical indicators"""
    ticker = stock_data['ticker']
    df = stock_data['historical']
    current_price = stock_data['live_price']
    
    if df.empty or len(df) < 50:
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
    
    # Price momentum
    price_change_5d = (close.iloc[-1] - close.iloc[-5]) / close.iloc[-5] * 100 if len(close) >= 5 else 0
    price_change_20d = (close.iloc[-1] - close.iloc[-20]) / close.iloc[-20] * 100 if len(close) >= 20 else 0
    
    # Volume analysis
    volume_avg = df['volume'].rolling(20).mean().iloc[-1] if len(df) >= 20 else df['volume'].mean()
    current_volume = df['volume'].iloc[-1]
    volume_ratio = current_volume / volume_avg if volume_avg > 0 else 1
    
    # Signal scoring system
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
    
    return {
        'ticker': ticker,
        'name': stock_data.get('name', ticker),
        'action': action,
        'confidence': final_confidence,
        'price': current_price,
        'change_pct': stock_data.get('change_pct', 0),
        'volume': stock_data.get('volume', 0),
        'rsi': round(current_rsi, 2),
        'macd': round(macd_data['macd'], 2),
        'sma_20': round(sma_20, 2),
        'sma_50': round(sma_50, 2),
        'reason': ' | '.join(reasons[:3]) if reasons else 'Neutral signals',
        'timestamp': datetime.now(IST).isoformat()
    }


# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def scan_stocks(tickers: List[str], min_confidence: float = 0.55) -> List[Dict]:
    """Scan multiple stocks and generate signals"""
    signals = []
    
    print(f"\n📊 Scanning {len(tickers)} stocks...")
    print("=" * 80)
    
    for i, ticker in enumerate(tickers, 1):
        try:
            print(f"[{i}/{len(tickers)}] Processing {ticker}...", end=' ', flush=True)
            
            # Get stock data (with retry and longer timeout)
            stock_data = None
            max_attempts = 3
            
            for attempt in range(max_attempts):
                try:
                    stock_data = get_stock_data(ticker)
                    if stock_data:
                        break
                except Exception:
                    pass
                
                if attempt < max_attempts - 1:
                    time.sleep(2)  # Wait before retry
            
            if not stock_data:
                print("❌ No data")
                continue
            
            # Generate signal
            signal = generate_signal(stock_data)
            
            if signal['confidence'] >= min_confidence:
                signals.append(signal)
                action_emoji = "🟢" if signal['action'] == 'BUY' else "🔴" if signal['action'] == 'SELL' else "⚪"
                print(f"{action_emoji} {signal['action']} ({signal['confidence']:.0%})")
            else:
                print("⚪ HOLD")
            
            # Small delay to avoid rate limiting
            time.sleep(0.3)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Interrupted by user")
            break
        except Exception as e:
            print(f"❌ Error")
            # Don't print full error to keep output clean
            continue
    
    return signals


def print_signals(signals: List[Dict]):
    """Print signals in a readable format"""
    if not signals:
        print("\n" + "=" * 80)
        print("❌ NO TRADING SIGNALS FOUND")
        print("=" * 80)
        print("\n💡 Try lowering --min-confidence (default: 0.55)")
        return
    
    # Sort by confidence
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Separate BUY and SELL
    buy_signals = [s for s in signals if s['action'] == 'BUY']
    sell_signals = [s for s in signals if s['action'] == 'SELL']
    
    print("\n" + "=" * 80)
    print(f"📈 TRADING SIGNALS - {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("=" * 80)
    
    if buy_signals:
        print(f"\n🟢 BUY SIGNALS ({len(buy_signals)}):")
        print("-" * 80)
        for sig in buy_signals:
            print(f"  {sig['ticker']:15s} | ₹{sig['price']:8.2f} | Confidence: {sig['confidence']:5.0%} | RSI: {sig['rsi']:5.1f}")
            print(f"    → {sig['reason']}")
            print()
    
    if sell_signals:
        print(f"\n🔴 SELL SIGNALS ({len(sell_signals)}):")
        print("-" * 80)
        for sig in sell_signals:
            print(f"  {sig['ticker']:15s} | ₹{sig['price']:8.2f} | Confidence: {sig['confidence']:5.0%} | RSI: {sig['rsi']:5.1f}")
            print(f"    → {sig['reason']}")
            print()
    
    print("=" * 80)
    print(f"\n📊 Summary: {len(buy_signals)} BUY | {len(sell_signals)} SELL | Total: {len(signals)} signals")
    print("=" * 80)


def save_to_csv(signals: List[Dict], filename: str):
    """Save signals to CSV file"""
    if not signals:
        return
    
    df = pd.DataFrame(signals)
    df.to_csv(filename, index=False)
    print(f"\n💾 Saved {len(signals)} signals to {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Standalone Trading Signal Generator - Single File Solution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python trading_signals.py
  python trading_signals.py --tickers RELIANCE.NS TCS.NS INFY.NS
  python trading_signals.py --top-n 20 --min-confidence 0.60
  python trading_signals.py --tickers RELIANCE.NS --output signals.csv
        """
    )
    
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='List of tickers to scan (e.g., RELIANCE.NS TCS.NS)',
        default=None
    )
    parser.add_argument(
        '--top-n',
        type=int,
        help='Scan top N stocks from default list (default: 20)',
        default=None
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        help='Minimum confidence threshold (0.0-1.0, default: 0.55)',
        default=0.55
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Save results to CSV file',
        default=None
    )
    
    args = parser.parse_args()
    
    # Determine tickers to scan
    if args.tickers:
        tickers = args.tickers
    elif args.top_n:
        tickers = DEFAULT_STOCKS[:args.top_n]
    else:
        tickers = DEFAULT_STOCKS[:20]  # Default: top 20
    
    print("\n" + "=" * 80)
    print("🚀 STANDALONE TRADING SIGNAL GENERATOR")
    print("=" * 80)
    print(f"📋 Scanning: {len(tickers)} stocks")
    print(f"🎯 Min Confidence: {args.min_confidence:.0%}")
    print("=" * 80)
    
    # Scan stocks
    signals = scan_stocks(tickers, min_confidence=args.min_confidence)
    
    # Print results
    print_signals(signals)
    
    # Save to file if requested
    if args.output:
        save_to_csv(signals, args.output)
    
    print("\n✅ Done!\n")


if __name__ == '__main__':
    main()
