#!/usr/bin/env python3
"""
Simple CLI tool to get trading signals from Adaptive Elite Strategy

Usage:
    python get_signals.py RELIANCE.NS
    python get_signals.py --watchlist
    python get_signals.py --all
    python get_signals.py TCS.NS INFY.NS HDFCBANK.NS
"""
import sys
import argparse
import json
from typing import List, Dict
import requests
from datetime import datetime

# Color codes for terminal
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    GRAY = '\033[90m'

def get_signal(ticker: str, base_url: str = "http://localhost:5000") -> Dict:
    """Get signal for a single ticker"""
    try:
        response = requests.post(
            f"{base_url}/api/trading/signals",
            json={"ticker": ticker},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to server. Is it running? (python run_web.py)"}
    except Exception as e:
        return {"error": str(e)}

def get_watchlist(base_url: str = "http://localhost:5000") -> List[str]:
    """Get watchlist from server"""
    try:
        response = requests.get(f"{base_url}/api/watchlist", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def format_signal(signal_data: Dict) -> str:
    """Format signal data for display"""
    if "error" in signal_data:
        return f"{Colors.RED}❌ Error: {signal_data['error']}{Colors.RESET}\n"
    
    if signal_data.get("status") != "success":
        return f"{Colors.RED}❌ Failed to get signal{Colors.RESET}\n"
    
    ticker = signal_data.get("ticker", "UNKNOWN")
    signal = signal_data.get("signal", "HOLD")
    confidence = signal_data.get("confidence", 0.0)
    current_price = signal_data.get("current_price", 0)
    entry_price = signal_data.get("entry_price", 0)
    stop_loss = signal_data.get("stop_loss", 0)
    target_1 = signal_data.get("target_1", 0)
    target_2 = signal_data.get("target_2", 0)
    regime_type = signal_data.get("regime_type", "UNKNOWN")
    market_phase = signal_data.get("market_phase", "NEUTRAL")
    trend_strength = signal_data.get("trend_strength", 0)
    volatility_pct = signal_data.get("volatility_pct", 0)
    
    # Signal emoji and color
    if signal == "BUY":
        signal_emoji = "🟢"
        signal_color = Colors.GREEN
    elif signal == "SELL":
        signal_emoji = "🔴"
        signal_color = Colors.RED
    else:
        signal_emoji = "⚪"
        signal_color = Colors.YELLOW
    
    # Confidence color
    if confidence >= 0.75:
        conf_color = Colors.GREEN
    elif confidence >= 0.65:
        conf_color = Colors.YELLOW
    else:
        conf_color = Colors.GRAY
    
    # Format output
    output = f"\n{Colors.BOLD}{Colors.CYAN}{ticker}{Colors.RESET}\n"
    output += f"  {signal_color}{signal_emoji} Signal: {signal}{Colors.RESET}\n"
    output += f"  {Colors.BOLD}Confidence:{Colors.RESET} {conf_color}{confidence:.0%}{Colors.RESET}\n"
    output += f"  {Colors.BOLD}Current:{Colors.RESET} ₹{current_price:,.2f}\n"
    
    if signal in ["BUY", "SELL"]:
        output += f"  {Colors.BOLD}Entry:{Colors.RESET} ₹{entry_price:,.2f} | "
        output += f"{Colors.BOLD}Stop:{Colors.RESET} ₹{stop_loss:,.2f} | "
        output += f"{Colors.BOLD}Target:{Colors.RESET} ₹{target_1:,.2f}\n"
        if target_2:
            output += f"  {Colors.BOLD}Target 2:{Colors.RESET} ₹{target_2:,.2f}\n"
    
    output += f"  {Colors.GRAY}Regime: {regime_type} ({market_phase}) | "
    output += f"Trend: {trend_strength:.1f} | Vol: {volatility_pct:.1f}%{Colors.RESET}\n"
    
    return output

def print_header():
    """Print header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print("📊 Trading Signals - Adaptive Elite Strategy")
    print(f"{'='*60}{Colors.RESET}\n")

def print_summary(signals: List[Dict]):
    """Print summary of signals"""
    buy_count = sum(1 for s in signals if s.get("signal") == "BUY")
    sell_count = sum(1 for s in signals if s.get("signal") == "SELL")
    hold_count = sum(1 for s in signals if s.get("signal") == "HOLD")
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}")
    print(f"Summary: {Colors.GREEN}BUY: {buy_count}{Colors.RESET} | "
          f"{Colors.RED}SELL: {sell_count}{Colors.RESET} | "
          f"{Colors.YELLOW}HOLD: {hold_count}{Colors.RESET}")
    print(f"{'='*60}{Colors.RESET}\n")

def main():
    parser = argparse.ArgumentParser(
        description="Get trading signals from Adaptive Elite Strategy",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python get_signals.py RELIANCE.NS
  python get_signals.py --watchlist
  python get_signals.py --all
  python get_signals.py TCS.NS INFY.NS HDFCBANK.NS
        """
    )
    
    parser.add_argument(
        "tickers",
        nargs="*",
        help="Stock tickers (e.g., RELIANCE.NS)"
    )
    parser.add_argument(
        "--watchlist",
        action="store_true",
        help="Get signals for all watchlist stocks"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Get signals for popular stocks"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:5000",
        help="Base URL of the trading server (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    
    args = parser.parse_args()
    
    # Determine which tickers to process
    tickers = []
    
    if args.watchlist:
        tickers = get_watchlist(args.url)
        if not tickers:
            print(f"{Colors.YELLOW}⚠️  Watchlist is empty. Add stocks first.{Colors.RESET}")
            return
    elif args.all:
        # Popular stocks
        tickers = [
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "BHARTIARTL.NS",
            "SBIN.NS",
            "BAJFINANCE.NS",
            "WIPRO.NS",
            "HINDUNILVR.NS"
        ]
    elif args.tickers:
        tickers = args.tickers
    else:
        parser.print_help()
        return
    
    if not tickers:
        print(f"{Colors.RED}❌ No tickers specified{Colors.RESET}")
        return
    
    # Print header
    if not args.json:
        print_header()
    
    # Get signals
    signals = []
    for i, ticker in enumerate(tickers, 1):
        if not args.json:
            print(f"{Colors.GRAY}[{i}/{len(tickers)}] Fetching signal for {ticker}...{Colors.RESET}", end="\r")
        
        signal_data = get_signal(ticker, args.url)
        
        if args.json:
            signals.append(signal_data)
        else:
            print(" " * 80, end="\r")  # Clear line
            print(format_signal(signal_data))
    
    # Print JSON output
    if args.json:
        print(json.dumps(signals, indent=2))
    else:
        print_summary(signals)
        print(f"{Colors.GRAY}Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}\n")

if __name__ == "__main__":
    main()
