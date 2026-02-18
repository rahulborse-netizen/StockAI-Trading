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


def _run_precompute(stocks: Optional[List[str]] = None, app=None, max_workers: int = 3):
    """
    Generate and cache signals for all stocks using optimized parallel processing.
    Prioritizes Upstox data when available to avoid Yahoo Finance rate limits.
    """
    global _precompute_done, _precompute_count
    tickers = stocks or DEFAULT_PRECOMPUTE_STOCKS
    try:
        from src.web.ai_models.elite_signal_generator import get_elite_signal_generator
        from src.web.signal_cache import get_cached_signal
        from src.web.upstox_connection import connection_manager

        generator = get_elite_signal_generator()
        success = 0
        failed = 0
        cached = 0
        start_time = time.time()
        
        # Check if Upstox is connected (prioritize live data)
        # Use app context to check Upstox connection status safely
        upstox_connected = False
        try:
            if app:
                with app.app_context():
                    try:
                        upstox_connected = connection_manager.is_connected()
                    except (RuntimeError, AttributeError):
                        # Flask session not available in background thread - this is OK
                        pass
        except Exception:
            # If app context fails, assume Upstox not connected
            pass
        
        if upstox_connected:
            logger.info("[Precompute] Upstox connected - using live data (faster, no rate limits)")
            # Can use more workers when Upstox is connected (no rate limits)
            max_workers = min(max_workers + 1, 4)
        else:
            logger.info("[Precompute] Upstox not connected - using Yahoo Finance (rate limited)")

        # Filter out tickers that already have fresh cache
        tickers_to_compute = []
        for ticker in tickers:
            cached_signal = get_cached_signal(ticker)
            if cached_signal:
                cached += 1
                logger.debug(f"[Precompute] {ticker}: using cached signal")
            else:
                tickers_to_compute.append(ticker)
        
        if not tickers_to_compute:
            logger.info(f"[Precompute] All {len(tickers)} signals already cached. Skipping computation.")
            _precompute_done = True
            _precompute_count = len(tickers)
            return

        logger.info(f"[Precompute] Computing {len(tickers_to_compute)} signals ({cached} already cached)")

        # Use ThreadPoolExecutor for parallel processing with optimized staggering
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit tasks with adaptive delay based on data source
            future_to_ticker = {}
            stagger_delay = 0.5 if upstox_connected else 2.0  # Faster when using Upstox
            
            for i, ticker in enumerate(tickers_to_compute):
                future = executor.submit(_generate_single_signal, ticker, generator, app)
                future_to_ticker[future] = ticker
                # Stagger submissions to avoid rate limits (less delay with Upstox)
                if i < len(tickers_to_compute) - 1:
                    time.sleep(stagger_delay)
            
            # Process completed tasks as they finish
            completed = 0
            rate_limited_count = 0
            for future in as_completed(future_to_ticker):
                completed += 1
                ticker = future_to_ticker[future]
                try:
                    result = future.result(timeout=60)  # 60s timeout per signal
                    if result['success']:
                        success += 1
                        logger.info(f"[Precompute] {result['ticker']}: {result['signal']} ({completed}/{len(tickers_to_compute)})")
                    else:
                        failed += 1
                        error_msg = str(result.get('error', 'error')).lower()
                        # Track rate limits separately
                        if 'rate limit' in error_msg:
                            rate_limited_count += 1
                            # Don't log rate limit errors as warnings (expected when Upstox not connected)
                            logger.debug(f"[Precompute] {result['ticker']}: rate limited (expected without Upstox)")
                        elif 'insufficient data' in error_msg:
                            logger.debug(f"[Precompute] {result['ticker']}: insufficient data")
                        else:
                            logger.debug(f"[Precompute] {result['ticker']}: skip ({result.get('error', 'error')})")
                except Exception as e:
                    failed += 1
                    error_msg = str(e).lower()
                    if 'rate limit' in error_msg:
                        rate_limited_count += 1
                        logger.debug(f"[Precompute] {ticker}: rate limited")
                    else:
                        logger.debug(f"[Precompute] {ticker}: {e}")
            
            if rate_limited_count > 0:
                logger.info(f"[Precompute] ⚠️ {rate_limited_count} signals rate limited by Yahoo Finance. Connect Upstox for unlimited data access.")

        elapsed = time.time() - start_time
        _precompute_done = True
        _precompute_count = success + cached
        logger.info(f"[Precompute] Done in {elapsed:.1f}s. Cached {success} new signals, {cached} from cache, {failed} failed/skipped.")
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


def _run_holdings_precompute(holdings: List[dict], app=None, max_workers: int = 3):
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
