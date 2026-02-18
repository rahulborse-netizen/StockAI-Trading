"""
Signal Pre-computation - Analyzes stocks at startup and caches signals
Run in background so signals are ready for next-day trading
Optimized with parallel processing for faster signal generation
"""
import logging
import threading
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

# Default stocks to pre-compute (NIFTY 50 top constituents + indices)
DEFAULT_PRECOMPUTE_STOCKS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "SBIN.NS",
    "BHARTIARTL.NS", "ITC.NS", "LT.NS", "HINDUNILVR.NS", "KOTAKBANK.NS", "AXISBANK.NS",
    "MARUTI.NS", "BAJFINANCE.NS", "HCLTECH.NS", "ASIANPAINT.NS", "WIPRO.NS", "ULTRACEMCO.NS",
    "NESTLEIND.NS", "SUNPHARMA.NS", "TITAN.NS", "ONGC.NS", "NTPC.NS", "POWERGRID.NS",
    "TATAMOTORS.NS", "M&M.NS", "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "^NSEI", "^NSEBANK"
]

_precompute_done = False
_precompute_count = 0


def _generate_single_signal(ticker: str, generator, app=None):
    """Generate signal for a single ticker (used in parallel processing)."""
    ctx = app.app_context() if app else None
    if ctx:
        ctx.push()
    try:
        from src.web.signal_cache import set_cached_signal
        result = generator.generate_signal(
            ticker=ticker,
            use_ensemble=True,
            use_multi_timeframe=True,
            instrument_key_override=None
        )
        if result and "error" not in result:
            set_cached_signal(ticker, result)
            return {'ticker': ticker, 'success': True, 'signal': result.get('signal', 'N/A')}
        else:
            return {'ticker': ticker, 'success': False, 'error': result.get('error', 'error') if result else 'no result'}
    except Exception as e:
        return {'ticker': ticker, 'success': False, 'error': str(e)}
    finally:
        if ctx:
            ctx.pop()


def _run_precompute(stocks: Optional[List[str]] = None, app=None, max_workers: int = 8):
    """Generate and cache signals for all stocks using parallel processing."""
    global _precompute_done, _precompute_count
    tickers = stocks or DEFAULT_PRECOMPUTE_STOCKS
    try:
        from src.web.ai_models.elite_signal_generator import get_elite_signal_generator

        generator = get_elite_signal_generator()
        success = 0
        failed = 0
        start_time = time.time()

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(_generate_single_signal, ticker, generator, app): ticker
                for ticker in tickers
            }
            
            # Process completed tasks as they finish
            completed = 0
            for future in as_completed(future_to_ticker):
                completed += 1
                ticker = future_to_ticker[future]
                try:
                    result = future.result()
                    if result['success']:
                        success += 1
                        logger.info(f"[Precompute] {result['ticker']}: {result['signal']} ({completed}/{len(tickers)})")
                    else:
                        failed += 1
                        logger.debug(f"[Precompute] {result['ticker']}: skip ({result.get('error', 'error')})")
                except Exception as e:
                    failed += 1
                    logger.debug(f"[Precompute] {ticker}: {e}")

        elapsed = time.time() - start_time
        _precompute_done = True
        _precompute_count = success
        logger.info(f"[Precompute] Done in {elapsed:.1f}s. Cached {success} signals, {failed} failed/skipped.")
    except Exception as e:
        logger.error(f"[Precompute] Error: {e}", exc_info=True)


def start_precompute_background(app=None, stocks: Optional[List[str]] = None):
    """Start signal pre-computation in a background thread."""
    def _bg():
        _run_precompute(stocks=stocks, app=app)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    logger.info(f"[Precompute] Started background pre-computation for {len(stocks or DEFAULT_PRECOMPUTE_STOCKS)} stocks.")


def _generate_holding_signal(holding: dict, generator, app=None):
    """Generate signal for a single holding (used in parallel processing)."""
    ctx = app.app_context() if app else None
    if ctx:
        ctx.push()
    try:
        from src.web.signal_cache import set_cached_signal
        ticker = holding.get("ticker") or holding.get("symbol")
        inst_key = holding.get("instrument_key") or holding.get("instrumentKey")
        if not ticker:
            return {'success': False, 'error': 'no ticker'}
        
        result = generator.generate_signal(
            ticker=ticker,
            use_ensemble=True,
            use_multi_timeframe=True,
            instrument_key_override=inst_key,
        )
        if result and "error" not in result:
            set_cached_signal(ticker, result)
            return {'ticker': ticker, 'success': True}
        return {'ticker': ticker, 'success': False, 'error': result.get('error') if result else 'no result'}
    except Exception as e:
        return {'ticker': holding.get('ticker', 'unknown'), 'success': False, 'error': str(e)}
    finally:
        if ctx:
            ctx.pop()


def _run_holdings_precompute(holdings: List[dict], app=None, max_workers: int = 6):
    """Pre-compute signals for demat holdings using parallel processing."""
    if not holdings:
        return
    try:
        from src.web.ai_models.elite_signal_generator import get_elite_signal_generator

        generator = get_elite_signal_generator()
        success = 0
        start_time = time.time()

        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_holding = {
                executor.submit(_generate_holding_signal, h, generator, app): h
                for h in holdings
            }
            
            for future in as_completed(future_to_holding):
                try:
                    result = future.result()
                    if result.get('success'):
                        success += 1
                except Exception:
                    pass
        
        elapsed = time.time() - start_time
        if success > 0:
            logger.info(f"[Precompute] Cached {success}/{len(holdings)} holdings signals in {elapsed:.1f}s")
    except Exception as e:
        logger.debug(f"[Precompute] Holdings precompute error: {e}")


def precompute_holdings_background(holdings: List[dict], app=None):
    """Pre-compute signals for demat holdings in background (uses instrument_key from instrument_token)."""
    if not holdings:
        return

    def _bg():
        _run_holdings_precompute(holdings=holdings, app=app)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    logger.info(f"[Precompute] Started holdings pre-computation for {len(holdings)} holdings.")


def is_precompute_done() -> bool:
    return _precompute_done


def get_precompute_count() -> int:
    return _precompute_count


def get_precompute_total() -> int:
    """Total number of stocks in the default pre-compute list (for progress display)."""
    return len(DEFAULT_PRECOMPUTE_STOCKS)
