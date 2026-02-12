"""
Signal Cache - Store pre-computed trading signals for instant access
Signals are persisted so they're ready when you start the server next day
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/signals")
CACHE_FILE = CACHE_DIR / "signals_cache.json"
CACHE_MAX_AGE_HOURS = 24  # Consider cache fresh for 24h (e.g. overnight pre-compute)


def _ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cached_signal(ticker: str, max_age_hours: float = CACHE_MAX_AGE_HOURS) -> Optional[Dict[str, Any]]:
    """
    Get cached signal for ticker. Returns None if not cached or expired.
    """
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"[SignalCache] Failed to read cache: {e}")
        return None
    signals = data.get("signals", {})
    meta = data.get("meta", {})
    if ticker not in signals:
        return None
    sig = signals[ticker]
    cached_at = sig.get("_cached_at") or meta.get("computed_at")
    if cached_at and max_age_hours > 0:
        try:
            s = str(cached_at)[:19].replace("Z", "")
            dt = datetime.fromisoformat(s)
            age_sec = (datetime.now() - dt).total_seconds()
            if age_sec > max_age_hours * 3600:
                logger.debug(f"[SignalCache] Cache for {ticker} expired ({age_sec/3600:.1f}h old)")
                return None
        except Exception:
            pass
    # Return copy without internal fields
    out = {k: v for k, v in sig.items() if not k.startswith("_")}
    out["source"] = out.get("source", "cache")
    return out


def set_cached_signal(ticker: str, signal: Dict[str, Any]) -> None:
    """Store a signal in cache."""
    _ensure_cache_dir()
    data = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    signals = data.setdefault("signals", {})
    sig_copy = dict(signal)
    sig_copy["_cached_at"] = datetime.now().isoformat()
    signals[ticker] = sig_copy
    data.setdefault("meta", {})["last_updated"] = datetime.now().isoformat()
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.warning(f"[SignalCache] Failed to write cache: {e}")


def get_all_cached_signals(max_age_hours: float = CACHE_MAX_AGE_HOURS) -> Dict[str, Dict[str, Any]]:
    """Get all cached signals that are still fresh."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    signals = data.get("signals", {})
    result = {}
    for ticker, sig in signals.items():
        s = get_cached_signal(ticker, max_age_hours)
        if s:
            result[ticker] = s
    return result


def get_cache_meta() -> Dict[str, Any]:
    """Get cache metadata (last computed, count, etc)."""
    if not CACHE_FILE.exists():
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    meta = data.get("meta", {})
    signals = data.get("signals", {})
    return {
        "last_updated": meta.get("last_updated"),
        "computed_at": meta.get("computed_at"),
        "count": len(signals),
    }
