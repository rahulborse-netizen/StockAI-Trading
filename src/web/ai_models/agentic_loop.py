"""
Agentic Loop: Self-correcting AI that learns from its own errors.
- Records every signal for outcome tracking
- Resolves outcomes when exit price is known (e.g. position closed)
- Updates ensemble weights based on recent model performance (corrects itself)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.web.ai_models.feedback_store import (
    record_signal as store_record_signal,
    resolve_signal as store_resolve_signal,
)
from src.web.ai_models.performance_tracker import get_performance_tracker
from src.web.ai_models.ensemble_manager import get_ensemble_manager

logger = logging.getLogger(__name__)


def record_signal(ticker: str, signal_response: Dict[str, Any]) -> None:
    """
    Record a generated signal for later outcome resolution (learn from errors).
    Call this after ELITE generates a signal.
    """
    if not signal_response or signal_response.get("error"):
        return
    try:
        entry_price = float(signal_response.get("current_price") or signal_response.get("entry_level", 0))
        if entry_price <= 0:
            return
        signal = signal_response.get("signal", "HOLD")
        ensemble_prob = float(signal_response.get("probability", 0.5))
        model_predictions = signal_response.get("model_predictions") or {}
        ts = signal_response.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None
        store_record_signal(
            ticker=ticker,
            entry_price=entry_price,
            signal=signal,
            ensemble_prob=ensemble_prob,
            model_predictions=model_predictions,
            timestamp=ts,
        )
    except Exception as e:
        logger.debug("Agentic record_signal skipped: %s", e)


def resolve_and_learn(ticker: str, exit_price: float) -> Dict[str, Any]:
    """
    Resolve the oldest pending signal for this ticker with exit_price,
    record per-model outcomes in the performance tracker, then update
    ensemble weights from recent performance (self-correction).
    Returns summary of what was learned.
    """
    result = {"resolved": False, "actual_return": None, "weights_updated": False}
    try:
        resolved = store_resolve_signal(ticker, exit_price)
        if not resolved:
            return result
        result["resolved"] = True
        result["actual_return"] = resolved.get("actual_return")
        result["correct"] = resolved.get("correct")

        # Record each model's prediction and outcome for accuracy tracking
        perf = get_performance_tracker()
        actual_return = resolved.get("actual_return")
        ts = resolved.get("timestamp")
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        for model_id, prob in (resolved.get("model_predictions") or {}).items():
            try:
                perf.record_prediction(
                    model_id=model_id,
                    ticker=ticker,
                    prediction=float(prob),
                    actual_return=actual_return,
                    timestamp=ts,
                )
            except Exception as e:
                logger.debug("Record prediction for %s: %s", model_id, e)
        # Also record ensemble as a "model" for overall tracking
        perf.record_prediction(
            model_id="ensemble",
            ticker=ticker,
            prediction=float(resolved.get("ensemble_prob", 0.5)),
            actual_return=actual_return,
            timestamp=ts,
        )

        # Learn from feedback: update ensemble weights from recent performance
        learn_result = learn_from_feedback(days=30)
        result["weights_updated"] = learn_result.get("weights_updated", False)
        result["weights"] = learn_result.get("weights")
    except Exception as e:
        logger.warning("Agentic resolve_and_learn failed: %s", e)
    return result


def learn_from_feedback(days: int = 30) -> Dict[str, Any]:
    """
    Recompute model performance from recent outcomes and update ensemble weights
    so the system corrects itself (down-weights models that were wrong often).
    """
    result = {"weights_updated": False, "weights": None}
    try:
        perf = get_performance_tracker()
        ensemble = get_ensemble_manager()
        # Get model IDs that participate in the ensemble (exclude "ensemble" - it's for tracking only)
        model_ids = ["logistic_regression", "xgboost", "lstm"]
        performance_data = {}
        for model_id in model_ids:
            metrics = perf.calculate_metrics(model_id, days=days)
            if "error" in metrics or "accuracy" not in metrics:
                continue
            performance_data[model_id] = {
                "accuracy": metrics.get("accuracy", 0.5),
                "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
                "win_rate": metrics.get("win_rate", 0.5),
            }
        if performance_data:
            ensemble.update_weights(performance_data)
            result["weights_updated"] = True
            result["weights"] = ensemble.model_weights
            logger.info("Agentic: updated ensemble weights from feedback (last %d days): %s", days, result["weights"])
    except Exception as e:
        logger.warning("Agentic learn_from_feedback failed: %s", e)
    return result


def get_agentic_status() -> Dict[str, Any]:
    """Return status of the agentic layer (pending count, last learn, etc.)."""
    try:
        from src.web.ai_models.feedback_store import _load_pending
        pending = _load_pending()
        ensemble = get_ensemble_manager()
        return {
            "pending_signals": len(pending),
            "ensemble_weights": ensemble.model_weights,
            "message": "Agentic self-correction is active. Signals are recorded; resolve outcomes to learn.",
        }
    except Exception as e:
        return {"error": str(e), "pending_signals": 0, "ensemble_weights": {}}
