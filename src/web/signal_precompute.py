"""
Signal Pre-computation - Analyzes stocks at startup and caches signals
Run in background so signals are ready for next-day trading
"""
import logging
import threading
from typing import List, Optional

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


def _run_precompute(stocks: Optional[List[str]] = None, app=None):
    """Generate and cache signals for all stocks. Runs in background thread."""
    global _precompute_done, _precompute_count
    tickers = stocks or DEFAULT_PRECOMPUTE_STOCKS
    try:
        from src.web.signal_cache import set_cached_signal
        from src.web.ai_models.elite_signal_generator import get_elite_signal_generator

        generator = get_elite_signal_generator()
        success = 0
        failed = 0

        # Use app context if provided (e.g. when Upstox connected)
        ctx = app.app_context() if app else None
        if ctx:
            ctx.push()

        try:
            for i, ticker in enumerate(tickers):
                try:
                    result = generator.generate_signal(
                        ticker=ticker,
                        use_ensemble=True,
                        use_multi_timeframe=True,
                        instrument_key_override=None
                    )
                    if result and "error" not in result:
                        set_cached_signal(ticker, result)
                        success += 1
                        logger.info(f"[Precompute] {ticker}: {result.get('signal', 'N/A')} ({(i+1)}/{len(tickers)})")
                    else:
                        failed += 1
                        logger.debug(f"[Precompute] {ticker}: skip ({result.get('error', 'error')})")
                except Exception as e:
                    failed += 1
                    logger.debug(f"[Precompute] {ticker}: {e}")
        finally:
            if ctx:
                ctx.pop()

        _precompute_done = True
        _precompute_count = success
        logger.info(f"[Precompute] Done. Cached {success} signals, {failed} failed/skipped.")
    except Exception as e:
        logger.error(f"[Precompute] Error: {e}", exc_info=True)


def start_precompute_background(app=None, stocks: Optional[List[str]] = None):
    """Start signal pre-computation in a background thread."""
    def _bg():
        _run_precompute(stocks=stocks, app=app)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    logger.info(f"[Precompute] Started background pre-computation for {len(stocks or DEFAULT_PRECOMPUTE_STOCKS)} stocks.")


def is_precompute_done() -> bool:
    return _precompute_done


def get_precompute_count() -> int:
    return _precompute_count
