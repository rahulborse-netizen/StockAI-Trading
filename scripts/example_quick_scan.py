#!/usr/bin/env python3
"""
Quick Example: Scan a few stocks and get trading signals
Simple example showing how to use the trading signal algorithm
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.live_trading_signals import (
    scan_stocks,
    EliteSignalGenerator,
    NSEDataClient,
    print_signals
)

def main():
    """Quick scan example"""
    
    # Popular stocks to scan
    tickers = [
        'RELIANCE.NS',
        'TCS.NS',
        'HDFCBANK.NS',
        'INFY.NS',
        'ICICIBANK.NS'
    ]
    
    print("="*80)
    print("QUICK TRADING SIGNAL SCAN")
    print("="*80)
    print(f"Scanning {len(tickers)} stocks...")
    print()
    
    # Initialize components
    signal_generator = EliteSignalGenerator()
    nse_client = NSEDataClient()
    
    # Scan stocks with minimum confidence of 0.55
    signals = scan_stocks(tickers, signal_generator, nse_client, min_confidence=0.55)
    
    # Print results
    print_signals(signals)
    
    # Show summary
    buy_count = len([s for s in signals if s['action'] == 'BUY'])
    sell_count = len([s for s in signals if s['action'] == 'SELL'])
    
    print(f"\nSummary: {buy_count} BUY signals, {sell_count} SELL signals")
    print("="*80)

if __name__ == '__main__':
    main()
