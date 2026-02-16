"""
Accuracy Reports - Backtest ELITE signals and produce win rate, Sharpe, max drawdown report.
Used for validation and trust-building metrics (Phase A of roadmap).
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

REPORT_PATH = Path("data/accuracy_report.json")
DEFAULT_YEARS = 5
NIFTY50_TICKER = "^NSEI"


def run_nifty50_backtest_report(years: int = DEFAULT_YEARS) -> Dict[str, Any]:
    """
    Run backtest on NIFTY 50 for the given number of years.
    Returns win rate, Sharpe, max drawdown, total return and related metrics.
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=years * 365)
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()

    try:
        from src.web.strategies.backtest_adaptive import backtest_adaptive_strategy

        result = backtest_adaptive_strategy(
            ticker=NIFTY50_TICKER,
            start_date=start_str,
            end_date=end_str,
            initial_capital=100000.0,
        )
    except Exception as e:
        logger.exception("Backtest failed")
        return {
            "status": "error",
            "error": str(e),
            "ticker": NIFTY50_TICKER,
            "start_date": start_str,
            "end_date": end_str,
            "win_rate": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "generated_at": datetime.now().isoformat(),
        }

    if "error" in result:
        return {
            "status": "error",
            "error": result["error"],
            "ticker": NIFTY50_TICKER,
            "start_date": start_str,
            "end_date": end_str,
            "win_rate": None,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "total_return": None,
            "generated_at": datetime.now().isoformat(),
        }

    metrics = result.get("metrics") or {}
    report = {
        "status": "success",
        "ticker": result.get("ticker", NIFTY50_TICKER),
        "start_date": result.get("start_date", start_str),
        "end_date": result.get("end_date", end_str),
        "initial_capital": result.get("initial_capital"),
        "final_equity": result.get("final_equity"),
        "win_rate": metrics.get("win_rate"),
        "sharpe_ratio": metrics.get("sharpe_ratio"),
        "max_drawdown": metrics.get("max_drawdown"),
        "total_return": result.get("total_return") or metrics.get("total_return"),
        "num_trades": result.get("num_trades") or metrics.get("num_trades"),
        "avg_return_per_trade": metrics.get("avg_return_per_trade"),
        "buy_hold_return": metrics.get("buy_hold_return"),
        "metrics": metrics,
        "generated_at": datetime.now().isoformat(),
    }
    return report


def save_report(report: Dict[str, Any], path: Optional[Path] = None) -> None:
    """Save report to JSON file for API to serve."""
    path = path or REPORT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Saved accuracy report to {path}")


def load_report(path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Load report from JSON file if it exists."""
    path = path or REPORT_PATH
    if not path.exists():
        return None
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load report from {path}: {e}")
        return None


def generate_and_save_report(years: int = DEFAULT_YEARS) -> Dict[str, Any]:
    """Run backtest, save to file, and return the report."""
    report = run_nifty50_backtest_report(years=years)
    if report.get("status") == "success":
        save_report(report)
    return report
