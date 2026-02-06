"""
ELITE Trading System - All-in-One Trading Script
Combines all Phase 2 and Phase 3 Tier 1 features for best trading signals
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import time
import json
from datetime import datetime
from typing import List, Dict, Optional
import argparse

# Import all components
from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
from src.web.ai_models.model_registry import get_model_registry
from src.web.ai_models.ensemble_manager import get_ensemble_manager
from src.web.trading_mode import get_trading_mode_manager
from src.web.upstox_connection import connection_manager
from src.web.market_data import MarketDataClient

# Color codes for terminal (Windows compatible)
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")

def print_signal(ticker: str, signal_data: Dict):
    """Print trading signal in formatted way"""
    signal = signal_data.get('signal', 'HOLD')
    probability = signal_data.get('probability', 0)
    confidence = signal_data.get('confidence', 0)
    current_price = signal_data.get('current_price', 0)
    entry_level = signal_data.get('entry_level', 0)
    stop_loss = signal_data.get('stop_loss', 0)
    target_1 = signal_data.get('target_1', 0)
    target_2 = signal_data.get('target_2', 0)
    elite_system = signal_data.get('elite_system', False)
    model_count = signal_data.get('model_count', 0)
    
    # Color based on signal
    if signal in ['BUY', 'STRONG_BUY']:
        signal_color = Colors.GREEN
    elif signal in ['SELL', 'STRONG_SELL']:
        signal_color = Colors.RED
    else:
        signal_color = Colors.YELLOW
    
    print(f"{Colors.BOLD}{'-'*80}{Colors.END}")
    print(f"{Colors.BOLD}Ticker: {Colors.END}{ticker}")
    print(f"{Colors.BOLD}Signal: {Colors.END}{signal_color}{signal}{Colors.END}")
    print(f"{Colors.BOLD}Probability: {Colors.END}{probability:.2%}")
    print(f"{Colors.BOLD}Confidence: {Colors.END}{confidence:.2%}")
    print(f"{Colors.BOLD}Current Price: {Colors.END}₹{current_price:.2f}")
    
    if elite_system:
        print(f"{Colors.BOLD}ELITE System: {Colors.END}{Colors.GREEN}Active{Colors.END} ({model_count} models)")
    
    if entry_level:
        print(f"\n{Colors.BOLD}Trading Levels:{Colors.END}")
        print(f"  Entry: ₹{entry_level:.2f}")
        print(f"  Stop Loss: ₹{stop_loss:.2f}")
        print(f"  Target 1: ₹{target_1:.2f}")
        print(f"  Target 2: ₹{target_2:.2f}")
        
        # Calculate risk/reward
        if entry_level and stop_loss:
            risk = abs(entry_level - stop_loss)
            reward_1 = abs(target_1 - entry_level)
            reward_2 = abs(target_2 - entry_level)
            if risk > 0:
                rr1 = reward_1 / risk
                rr2 = reward_2 / risk
                print(f"\n{Colors.BOLD}Risk/Reward:{Colors.END}")
                print(f"  Target 1: {rr1:.2f}:1")
                print(f"  Target 2: {rr2:.2f}:1")

def generate_signals(tickers: List[str], use_elite: bool = True) -> Dict[str, Dict]:
    """Generate signals for multiple tickers"""
    print_header("ELITE AI SIGNAL GENERATION")
    
    generator = get_elite_signal_generator()
    signals = {}
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Analyzing {ticker}...")
        try:
            signal_data = generator.generate_signal(
                ticker=ticker,
                use_ensemble=use_elite,
                use_multi_timeframe=use_elite
            )
            
            if 'error' not in signal_data:
                signals[ticker] = signal_data
                print_signal(ticker, signal_data)
            else:
                error_msg = signal_data.get('error', 'Unknown error')
                # Check if it's a data availability issue (not a code issue)
                if '2023-09-30' in error_msg or '2024-09-30' in error_msg:
                    print(f"{Colors.YELLOW}[WARN] {ticker}: Data unavailable (dates correct, yfinance issue){Colors.END}")
                    print(f"      Try: pip install --upgrade yfinance")
                else:
                    print(f"{Colors.RED}[ERROR] {ticker}: {error_msg[:100]}{Colors.END}")
                signals[ticker] = {'error': error_msg}
                
        except Exception as e:
            print(f"{Colors.RED}[ERROR] {ticker}: {str(e)[:100]}{Colors.END}")
            signals[ticker] = {'error': str(e)}
        
        # Small delay between requests
        if i < len(tickers):
            time.sleep(1)
    
    return signals

def get_watchlist() -> List[str]:
    """Get default watchlist"""
    return [
        'RELIANCE.NS',
        'TCS.NS',
        'INFY.NS',
        'HDFCBANK.NS',
        'ICICIBANK.NS',
        'BHARTIARTL.NS',
        'SBIN.NS',
        'BAJFINANCE.NS',
        'WIPRO.NS',
        'HINDUNILVR.NS'
    ]

def print_summary(signals: Dict[str, Dict]):
    """Print summary of all signals"""
    print_header("SIGNAL SUMMARY")
    
    buy_signals = []
    sell_signals = []
    hold_signals = []
    errors = []
    
    for ticker, data in signals.items():
        if 'error' in data:
            errors.append(ticker)
        else:
            signal = data.get('signal', 'HOLD')
            if signal in ['BUY', 'STRONG_BUY']:
                buy_signals.append((ticker, data))
            elif signal in ['SELL', 'STRONG_SELL']:
                sell_signals.append((ticker, data))
            else:
                hold_signals.append((ticker, data))
    
    print(f"{Colors.BOLD}Total Analyzed: {Colors.END}{len(signals)}")
    print(f"{Colors.GREEN}Buy Signals: {Colors.END}{len(buy_signals)}")
    print(f"{Colors.RED}Sell Signals: {Colors.END}{len(sell_signals)}")
    print(f"{Colors.YELLOW}Hold Signals: {Colors.END}{len(hold_signals)}")
    if errors:
        print(f"{Colors.RED}Errors: {Colors.END}{len(errors)}")
    
    if buy_signals:
        print(f"\n{Colors.BOLD}{Colors.GREEN}TOP BUY OPPORTUNITIES:{Colors.END}")
        # Sort by probability
        buy_signals.sort(key=lambda x: x[1].get('probability', 0), reverse=True)
        for ticker, data in buy_signals[:5]:  # Top 5
            prob = data.get('probability', 0)
            conf = data.get('confidence', 0)
            print(f"  {ticker}: {prob:.1%} prob, {conf:.1%} confidence")
    
    if sell_signals:
        print(f"\n{Colors.BOLD}{Colors.RED}SELL SIGNALS:{Colors.END}")
        sell_signals.sort(key=lambda x: x[1].get('probability', 0), reverse=True)
        for ticker, data in sell_signals[:5]:
            prob = data.get('probability', 0)
            conf = data.get('confidence', 0)
            print(f"  {ticker}: {prob:.1%} prob, {conf:.1%} confidence")

def check_system_status():
    """Check system components status"""
    print_header("SYSTEM STATUS CHECK")
    
    status = {
        'elite_ai': False,
        'model_registry': False,
        'ensemble': False,
        'trading_mode': False,
        'upstox': False
    }
    
    # Check ELITE AI
    try:
        generator = get_elite_signal_generator()
        status['elite_ai'] = True
        print(f"{Colors.GREEN}[OK]{Colors.END} ELITE AI System")
    except Exception as e:
        print(f"{Colors.RED}[FAIL]{Colors.END} ELITE AI System: {e}")
    
    # Check Model Registry
    try:
        registry = get_model_registry()
        models = registry.get_active_models()
        status['model_registry'] = True
        print(f"{Colors.GREEN}[OK]{Colors.END} Model Registry ({len(models)} models)")
    except Exception as e:
        print(f"{Colors.RED}[FAIL]{Colors.END} Model Registry: {e}")
    
    # Check Ensemble
    try:
        ensemble = get_ensemble_manager()
        status['ensemble'] = True
        print(f"{Colors.GREEN}[OK]{Colors.END} Ensemble Manager")
    except Exception as e:
        print(f"{Colors.RED}[FAIL]{Colors.END} Ensemble Manager: {e}")
    
    # Check Trading Mode
    try:
        mode_manager = get_trading_mode_manager()
        current_mode = mode_manager.get_mode()
        status['trading_mode'] = True
        mode_str = "PAPER" if "PAPER" in str(current_mode) else "LIVE"
        print(f"{Colors.GREEN}[OK]{Colors.END} Trading Mode: {mode_str}")
    except Exception as e:
        print(f"{Colors.RED}[FAIL]{Colors.END} Trading Mode: {e}")
    
    # Check Upstox Connection (optional, skip if not in Flask context)
    try:
        # Try to check Upstox, but don't fail if not available
        print(f"{Colors.YELLOW}[INFO]{Colors.END} Upstox connection check skipped (optional)")
    except Exception as e:
        print(f"{Colors.YELLOW}[INFO]{Colors.END} Upstox check skipped (optional)")
    
    return status

def save_signals_to_file(signals: Dict[str, Dict], filename: str = None):
    """Save signals to JSON file"""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"signals_{timestamp}.json"
    
    output = {
        'timestamp': datetime.now().isoformat(),
        'signals': signals
    }
    
    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n{Colors.CYAN}Signals saved to: {filename}{Colors.END}")

def main():
    """Main trading system"""
    parser = argparse.ArgumentParser(description='ELITE Trading System - Best Trading Signals')
    parser.add_argument('--tickers', '-t', nargs='+', help='Tickers to analyze (e.g., RELIANCE.NS TCS.NS)')
    parser.add_argument('--watchlist', '-w', action='store_true', help='Use default watchlist')
    parser.add_argument('--file', '-f', help='Load tickers from file (one per line)')
    parser.add_argument('--continuous', '-c', action='store_true', help='Run continuously (every N minutes)')
    parser.add_argument('--interval', '-i', type=int, default=60, help='Interval in minutes for continuous mode')
    parser.add_argument('--save', '-s', action='store_true', help='Save signals to JSON file')
    parser.add_argument('--no-elite', action='store_true', help='Disable ELITE system (use basic)')
    parser.add_argument('--status', action='store_true', help='Check system status only')
    
    args = parser.parse_args()
    
    # Print banner
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("="*80)
    print("                    ELITE AI TRADING SYSTEM".center(80))
    print("              Best Trading Signals - All-in-One Script".center(80))
    print("="*80)
    print(f"{Colors.END}")
    print(f"{Colors.CYAN}Version: Phase 2 + Phase 3 Tier 1{Colors.END}")
    print(f"{Colors.CYAN}Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")
    
    # Check system status
    if args.status:
        check_system_status()
        return
    
    status = check_system_status()
    
    # Determine tickers
    tickers = []
    if args.tickers:
        tickers = args.tickers
    elif args.file:
        try:
            with open(args.file, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Failed to read file: {e}{Colors.END}")
            return
    elif args.watchlist:
        tickers = get_watchlist()
    else:
        # Default: use watchlist
        tickers = get_watchlist()
        print(f"{Colors.YELLOW}[INFO] Using default watchlist (use --tickers or --file for custom){Colors.END}")
    
    if not tickers:
        print(f"{Colors.RED}[ERROR] No tickers specified{Colors.END}")
        return
    
    print(f"\n{Colors.BOLD}Analyzing {len(tickers)} tickers...{Colors.END}")
    print(f"Tickers: {', '.join(tickers[:5])}{'...' if len(tickers) > 5 else ''}\n")
    
    use_elite = not args.no_elite
    
    if args.continuous:
        print(f"{Colors.CYAN}Continuous mode: Running every {args.interval} minutes{Colors.END}")
        print(f"{Colors.YELLOW}Press Ctrl+C to stop{Colors.END}\n")
        
        iteration = 1
        try:
            while True:
                print_header(f"ITERATION {iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                signals = generate_signals(tickers, use_elite=use_elite)
                print_summary(signals)
                
                if args.save:
                    save_signals_to_file(signals)
                
                iteration += 1
                
                if args.interval > 0:
                    print(f"\n{Colors.CYAN}Waiting {args.interval} minutes until next run...{Colors.END}")
                    time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}Stopped by user{Colors.END}")
    else:
        # Single run
        signals = generate_signals(tickers, use_elite=use_elite)
        print_summary(signals)
        
        if args.save:
            save_signals_to_file(signals)
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}Analysis Complete!{Colors.END}\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Interrupted by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}[FATAL ERROR] {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
