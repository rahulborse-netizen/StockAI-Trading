#!/usr/bin/env python3
"""
Live Trading Signal Algorithm
Tracks live NSE/BSE data and generates buy/sell trading signals
No dashboard required - pure algorithm output
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import time
import logging
from typing import List, Dict, Optional
import pandas as pd
import pytz

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web.ai_models.elite_signal_generator import EliteSignalGenerator
from src.web.stock_universe import StockUniverse
from src.web.nse_data_client import NSEDataClient
from src.research.data import download_yahoo_ohlcv
from src.web.intraday_data_manager import get_intraday_data_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# IST timezone
IST = pytz.timezone('Asia/Kolkata')

# Market hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def is_market_hours() -> bool:
    """Check if current time is during market hours"""
    now = datetime.now(IST)
    hour = now.hour
    minute = now.minute
    
    # Before market open
    if hour < MARKET_OPEN_HOUR or (hour == MARKET_OPEN_HOUR and minute < MARKET_OPEN_MINUTE):
        return False
    
    # After market close
    if hour > MARKET_CLOSE_HOUR or (hour == MARKET_CLOSE_HOUR and minute > MARKET_CLOSE_MINUTE):
        return False
    
    return True


def get_live_price(ticker: str, nse_client: NSEDataClient) -> Optional[Dict]:
    """
    Get live price data for a ticker
    Returns: {'price': float, 'change': float, 'volume': int, 'timestamp': datetime}
    """
    try:
        # Extract symbol from ticker (e.g., 'RELIANCE.NS' -> 'RELIANCE')
        symbol = ticker.replace('.NS', '').replace('.BO', '')
        
        # Try NSE API first
        quote = nse_client.get_quote(symbol)
        if quote:
            return {
                'price': quote.get('current_price', 0),
                'change': quote.get('change', 0),
                'change_pct': quote.get('change_pct', 0),
                'volume': quote.get('volume', 0),
                'high': quote.get('high', 0),
                'low': quote.get('low', 0),
                'open': quote.get('open', 0),
                'timestamp': datetime.now(IST)
            }
        
        # Fallback: Use Yahoo Finance (may have delay)
        logger.warning(f"Using Yahoo Finance for {ticker} (may have delay)")
        end_date = datetime.now(IST)
        start_date = end_date - timedelta(days=5)
        
        df = download_yahoo_ohlcv(ticker, start_date, end_date)
        if not df.empty:
            latest = df.iloc[-1]
            return {
                'price': float(latest['close']),
                'change': 0,  # Yahoo doesn't provide real-time change
                'change_pct': 0,
                'volume': int(latest.get('volume', 0)),
                'high': float(latest.get('high', latest['close'])),
                'low': float(latest.get('low', latest['close'])),
                'open': float(latest.get('open', latest['close'])),
                'timestamp': df.index[-1]
            }
        
        return None
    except Exception as e:
        logger.error(f"Error getting live price for {ticker}: {e}")
        return None


def generate_signal_for_ticker(
    ticker: str,
    signal_generator: EliteSignalGenerator,
    nse_client: NSEDataClient
) -> Optional[Dict]:
    """
    Generate trading signal for a single ticker
    Returns: {'ticker': str, 'signal': str, 'confidence': float, 'price': float, 'reason': str}
    """
    try:
        logger.info(f"Generating signal for {ticker}...")
        
        # Get live price
        live_data = get_live_price(ticker, nse_client)
        if not live_data:
            logger.warning(f"Could not get live data for {ticker}")
            return None
        
        current_price = live_data['price']
        if current_price <= 0:
            logger.warning(f"Invalid price for {ticker}: {current_price}")
            return None
        
        # Generate signal using ELITE generator
        signal_result = signal_generator.generate_signal(ticker)
        
        if not signal_result:
            return None
        
        signal_type = signal_result.get('signal', 'HOLD')
        confidence = signal_result.get('confidence', 0.0)
        model_id = signal_result.get('model_id', 'unknown')
        
        # Determine buy/sell/hold
        if signal_type == 'BUY' and confidence >= 0.6:
            action = 'BUY'
            reason = f"Strong {model_id} signal with {confidence:.2%} confidence"
        elif signal_type == 'SELL' and confidence >= 0.6:
            action = 'SELL'
            reason = f"Strong {model_id} signal with {confidence:.2%} confidence"
        elif signal_type == 'BUY' and confidence >= 0.5:
            action = 'BUY'
            reason = f"Moderate {model_id} signal with {confidence:.2%} confidence"
        elif signal_type == 'SELL' and confidence >= 0.5:
            action = 'SELL'
            reason = f"Moderate {model_id} signal with {confidence:.2%} confidence"
        else:
            action = 'HOLD'
            reason = f"Weak signal (confidence: {confidence:.2%})"
        
        return {
            'ticker': ticker,
            'action': action,
            'signal': signal_type,
            'confidence': confidence,
            'price': current_price,
            'change_pct': live_data.get('change_pct', 0),
            'volume': live_data.get('volume', 0),
            'reason': reason,
            'model_id': model_id,
            'timestamp': datetime.now(IST).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error generating signal for {ticker}: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return None


def scan_stocks(
    tickers: List[str],
    signal_generator: EliteSignalGenerator,
    nse_client: NSEDataClient,
    min_confidence: float = 0.55
) -> List[Dict]:
    """
    Scan multiple stocks and generate signals
    Returns list of signals with confidence >= min_confidence
    """
    signals = []
    
    logger.info(f"Scanning {len(tickers)} stocks...")
    
    for i, ticker in enumerate(tickers, 1):
        try:
            signal = generate_signal_for_ticker(ticker, signal_generator, nse_client)
            
            if signal and signal['confidence'] >= min_confidence:
                signals.append(signal)
                logger.info(
                    f"[{i}/{len(tickers)}] {ticker}: {signal['action']} "
                    f"(confidence: {signal['confidence']:.2%}, price: ₹{signal['price']:.2f})"
                )
            else:
                logger.debug(f"[{i}/{len(tickers)}] {ticker}: HOLD or low confidence")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except KeyboardInterrupt:
            logger.info("Scan interrupted by user")
            break
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue
    
    return signals


def print_signals(signals: List[Dict]):
    """Print signals in a readable format"""
    if not signals:
        print("\n" + "="*80)
        print("NO TRADING SIGNALS FOUND")
        print("="*80)
        return
    
    # Sort by confidence (highest first)
    signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Separate BUY and SELL signals
    buy_signals = [s for s in signals if s['action'] == 'BUY']
    sell_signals = [s for s in signals if s['action'] == 'SELL']
    
    print("\n" + "="*80)
    print(f"TRADING SIGNALS - {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
    print("="*80)
    
    if buy_signals:
        print(f"\n🟢 BUY SIGNALS ({len(buy_signals)}):")
        print("-" * 80)
        for sig in buy_signals:
            print(
                f"  {sig['ticker']:15s} | "
                f"Price: ₹{sig['price']:8.2f} | "
                f"Confidence: {sig['confidence']:6.2%} | "
                f"Change: {sig['change_pct']:6.2f}% | "
                f"Volume: {sig['volume']:,}"
            )
            print(f"    → {sig['reason']}")
    
    if sell_signals:
        print(f"\n🔴 SELL SIGNALS ({len(sell_signals)}):")
        print("-" * 80)
        for sig in sell_signals:
            print(
                f"  {sig['ticker']:15s} | "
                f"Price: ₹{sig['price']:8.2f} | "
                f"Confidence: {sig['confidence']:6.2%} | "
                f"Change: {sig['change_pct']:6.2f}% | "
                f"Volume: {sig['volume']:,}"
            )
            print(f"    → {sig['reason']}")
    
    print("\n" + "="*80)


def save_signals_to_file(signals: List[Dict], output_file: Path):
    """Save signals to CSV file"""
    if not signals:
        return
    
    df = pd.DataFrame(signals)
    df.to_csv(output_file, index=False)
    logger.info(f"Saved {len(signals)} signals to {output_file}")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Live Trading Signal Algorithm')
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='List of tickers to scan (e.g., RELIANCE.NS TCS.NS)',
        default=None
    )
    parser.add_argument(
        '--watchlist',
        type=str,
        help='File containing list of tickers (one per line)',
        default=None
    )
    parser.add_argument(
        '--top-n',
        type=int,
        help='Scan top N stocks by volume (default: 50)',
        default=50
    )
    parser.add_argument(
        '--min-confidence',
        type=float,
        help='Minimum confidence threshold (default: 0.55)',
        default=0.55
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV file path',
        default=None
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuously (scan every 5 minutes during market hours)',
        default=False
    )
    parser.add_argument(
        '--interval',
        type=int,
        help='Scan interval in minutes (default: 5)',
        default=5
    )
    
    args = parser.parse_args()
    
    # Initialize components
    logger.info("Initializing signal generator...")
    signal_generator = EliteSignalGenerator()
    
    logger.info("Initializing NSE data client...")
    nse_client = NSEDataClient()
    
    # Get tickers to scan
    tickers = []
    
    if args.tickers:
        tickers = args.tickers
    elif args.watchlist:
        watchlist_path = Path(args.watchlist)
        if watchlist_path.exists():
            with open(watchlist_path, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]
        else:
            logger.error(f"Watchlist file not found: {watchlist_path}")
            return
    else:
        # Get top N stocks from universe
        logger.info(f"Loading top {args.top_n} stocks from universe...")
        universe = StockUniverse()
        stocks_df = universe.get_universe()
        
        if stocks_df is not None and not stocks_df.empty:
            # Sort by volume or market cap if available, take top N
            tickers = stocks_df.head(args.top_n)['ticker'].tolist()
        else:
            # Fallback: Use popular stocks
            tickers = [
                'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
                'ICICIBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'LICI.NS',
                'ITC.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'KOTAKBANK.NS', 'LT.NS',
                'ASIANPAINT.NS', 'MARUTI.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'NTPC.NS'
            ]
            logger.info(f"Using default watchlist of {len(tickers)} stocks")
    
    logger.info(f"Will scan {len(tickers)} stocks")
    
    # Run scan
    if args.continuous:
        logger.info("Running in continuous mode...")
        logger.info(f"Scan interval: {args.interval} minutes")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                if is_market_hours():
                    logger.info(f"\n{'='*80}")
                    logger.info(f"Starting scan at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')}")
                    logger.info(f"{'='*80}")
                    
                    signals = scan_stocks(tickers, signal_generator, nse_client, args.min_confidence)
                    print_signals(signals)
                    
                    if args.output:
                        output_path = Path(args.output)
                        timestamp = datetime.now(IST).strftime('%Y%m%d_%H%M%S')
                        output_path = output_path.parent / f"{output_path.stem}_{timestamp}{output_path.suffix}"
                        save_signals_to_file(signals, output_path)
                    
                    logger.info(f"\nWaiting {args.interval} minutes until next scan...")
                    time.sleep(args.interval * 60)
                else:
                    logger.info("Market is closed. Waiting for market hours...")
                    time.sleep(60)  # Check every minute
                    
        except KeyboardInterrupt:
            logger.info("\nStopped by user")
    else:
        # Single scan
        if not is_market_hours():
            logger.warning("Market is currently closed. Results may be based on last close prices.")
        
        signals = scan_stocks(tickers, signal_generator, nse_client, args.min_confidence)
        print_signals(signals)
        
        if args.output:
            save_signals_to_file(signals, Path(args.output))


if __name__ == '__main__':
    main()
