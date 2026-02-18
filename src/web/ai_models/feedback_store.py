"""
Agentic Feedback Store
Stores signal context and outcomes so the system can learn from its own errors.
Used by the agentic loop to record predictions per model and resolve with actual returns.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

FEEDBACK_DIR = Path("data/models")
PENDING_SIGNALS_FILE = FEEDBACK_DIR / "agentic_pending_signals.json"
OUTCOMES_FILE = FEEDBACK_DIR / "agentic_outcomes.json"
MAX_PENDING_PER_TICKER = 5
MAX_OUTCOME_RECORDS = 5000


def _ensure_dir() -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def _load_pending() -> List[Dict[str, Any]]:
    _ensure_dir()
    if not PENDING_SIGNALS_FILE.exists():
        return []
    try:
        with open(PENDING_SIGNALS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not load pending signals: %s", e)
        return []


def _save_pending(pending: List[Dict[str, Any]]) -> None:
    _ensure_dir()
    try:
        with open(PENDING_SIGNALS_FILE, "w", encoding="utf-8") as f:
            json.dump(pending, f, indent=2, default=str)
    except Exception as e:
        logger.warning("Could not save pending signals: %s", e)


def _normalize_ticker(t: str) -> str:
    if not t:
        return ""
    return str(t).strip().upper().replace(".NS", "").replace(".BO", "")


def record_signal(
    ticker: str,
    entry_price: float,
    signal: str,
    ensemble_prob: float,
    model_predictions: Dict[str, Any],
    timestamp: Optional[datetime] = None,
) -> None:
    """
    Record a generated signal for later outcome resolution.
    Call this when ELITE produces a signal so we can learn from outcomes.
    """
    ts = timestamp or datetime.now()
    normalized = _normalize_ticker(ticker)
    # Flatten model_predictions to { model_id: probability }
    predictions = {}
    for k, v in (model_predictions or {}).items():
        if isinstance(v, dict) and "probability" in v:
            predictions[k] = float(v["probability"])
        elif isinstance(v, (int, float)):
            predictions[k] = float(v)
    record = {
        "ticker": normalized,
        "entry_price": float(entry_price),
        "signal": str(signal),
        "ensemble_prob": float(ensemble_prob),
        "model_predictions": predictions,
        "timestamp": ts.isoformat(),
    }
    pending = _load_pending()
    # Keep only recent pendings per this ticker
    pending = [p for p in pending if p.get("ticker") != normalized]
    pending.append(record)
    # Limit total pending per ticker by keeping last N
    by_ticker: Dict[str, List[Dict]] = {}
    for p in pending:
        t = p.get("ticker", "")
        by_ticker.setdefault(t, []).append(p)
    new_pending = []
    for t, recs in by_ticker.items():
        recs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        new_pending.extend(recs[:MAX_PENDING_PER_TICKER])
    new_pending.sort(key=lambda r: r.get("timestamp", ""))
    _save_pending(new_pending)
    logger.debug("Recorded signal for outcome tracking: %s %s @ %s", normalized, signal, entry_price)


def get_pending_for_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Return the oldest pending signal for this ticker (for resolution)."""
    normalized = _normalize_ticker(ticker)
    pending = _load_pending()
    for p in pending:
        if p.get("ticker") == normalized:
            return p
    return None


def resolve_signal(ticker: str, exit_price: float) -> Optional[Dict[str, Any]]:
    """
    Resolve the oldest pending signal for this ticker with the given exit price.
    Removes it from pending and returns the record with actual_return and correct flags.
    """
    normalized = _normalize_ticker(ticker)
    pending = _load_pending()
    for i, p in enumerate(pending):
        if p.get("ticker") != normalized:
            continue
        entry = float(p.get("entry_price", 0))
        if entry <= 0:
            pending.pop(i)
            _save_pending(pending)
            return None
        actual_return = (exit_price - entry) / entry
        p["exit_price"] = exit_price
        p["actual_return"] = actual_return
        p["resolved_at"] = datetime.now().isoformat()
        sig = p.get("signal", "HOLD")
        # Correct: BUY and return > 0, or SELL and return < 0
        if "BUY" in sig and actual_return > 0:
            p["correct"] = True
        elif "SELL" in sig and actual_return < 0:
            p["correct"] = True
        elif "BUY" in sig or "SELL" in sig:
            p["correct"] = False
        else:
            p["correct"] = None
        pending.pop(i)
        _save_pending(pending)
        return p
    return None
