"""
Phase 5.1: Advanced Analytics
Sortino/Calmar ratios, MAE/MFE, attribution analysis, performance metrics.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


def sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0.0, periods_per_year: int = 252) -> float:
    """Sortino ratio: excess return / downside deviation."""
    excess = np.asarray(returns, dtype=float) - risk_free_rate / periods_per_year
    downside = excess[excess < 0]
    if len(downside) == 0:
        return 0.0
    downside_std = np.sqrt(np.mean(downside ** 2))
    if downside_std == 0:
        return 0.0
    return float(np.mean(excess) / downside_std * np.sqrt(periods_per_year))


def calmar_ratio(returns: np.ndarray, periods_per_year: int = 252, rolling_months: int = 36) -> float:
    """Calmar ratio: annual return / max drawdown (over rolling period)."""
    if len(returns) < 2:
        return 0.0
    ann_return = float(np.mean(returns) * periods_per_year)
    cum = np.cumprod(1 + np.asarray(returns, dtype=float)) - 1
    peak = np.maximum.accumulate(cum)
    dd = (cum - peak) / (peak + 1e-12)
    max_dd = float(np.min(dd))
    if max_dd == 0:
        return 0.0
    return ann_return / abs(max_dd)


def max_adverse_excursion(prices: np.ndarray, entry_idx: int, exit_idx: int) -> float:
    """MAE: max unfavorable move from entry during the trade (as fraction)."""
    if entry_idx < 0 or exit_idx >= len(prices) or entry_idx >= exit_idx:
        return 0.0
    entry_price = float(prices[entry_idx])
    segment = prices[entry_idx : exit_idx + 1]
    low = float(np.min(segment))
    if entry_price <= 0:
        return 0.0
    return (low - entry_price) / entry_price


def max_favorable_excursion(prices: np.ndarray, entry_idx: int, exit_idx: int) -> float:
    """MFE: max favorable move from entry during the trade (as fraction)."""
    if entry_idx < 0 or exit_idx >= len(prices) or entry_idx >= exit_idx:
        return 0.0
    entry_price = float(prices[entry_idx])
    segment = prices[entry_idx : exit_idx + 1]
    high = float(np.max(segment))
    if entry_price <= 0:
        return 0.0
    return (high - entry_price) / entry_price


def compute_trade_analytics(trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    trades: list of dicts with keys e.g. entry_price, exit_price, entry_time, exit_time, pnl, side
    """
    if not trades:
        return {
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'total_pnl': 0.0,
            'mae_avg': 0.0,
            'mfe_avg': 0.0,
        }
    pnls = [float(t.get('pnl', 0)) for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    total_pnl = sum(pnls)
    win_rate = len(wins) / len(pnls) if pnls else 0.0
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss else 0.0

    mae_list = []
    mfe_list = []
    for t in trades:
        ep, ex = t.get('entry_price'), t.get('exit_price')
        if ep and ex and ep > 0:
            ret = (ex - ep) / ep
            mae_list.append(t.get('mae', ret))  # use provided MAE or simple ret
            mfe_list.append(t.get('mfe', ret))
    return {
        'win_rate': win_rate,
        'avg_win': float(avg_win),
        'avg_loss': float(avg_loss),
        'profit_factor': float(profit_factor),
        'total_pnl': total_pnl,
        'trade_count': len(trades),
        'mae_avg': float(np.mean(mae_list)) if mae_list else 0.0,
        'mfe_avg': float(np.mean(mfe_list)) if mfe_list else 0.0,
    }


def attribution_by_model(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """Attribution: performance by model_id."""
    by_model: Dict[str, List[float]] = {}
    for r in records:
        mid = r.get('model_id', 'unknown')
        if mid not in by_model:
            by_model[mid] = []
        ret = r.get('actual_return') or r.get('return')
        if ret is not None:
            by_model[mid].append(float(ret))
    return {
        mid: {
            'count': len(rets),
            'mean_return': float(np.mean(rets)),
            'total_return': float(np.sum(rets)),
        }
        for mid, rets in by_model.items()
    }


def attribution_by_period(
    records: List[Dict[str, Any]],
    period: str = 'day',
) -> Dict[str, float]:
    """Attribution by time period (day/week/month)."""
    from collections import defaultdict
    by_period = defaultdict(list)
    for r in records:
        ts = r.get('timestamp') or r.get('date')
        if not ts:
            continue
        if isinstance(ts, str):
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            except Exception:
                continue
        else:
            dt = ts
        ret = r.get('actual_return') or r.get('return')
        if ret is None:
            continue
        if period == 'day':
            key = dt.strftime('%Y-%m-%d')
        elif period == 'week':
            key = dt.strftime('%Y-W%W')
        else:
            key = dt.strftime('%Y-%m')
        by_period[key].append(float(ret))
    return {
        k: float(np.sum(v)) for k, v in by_period.items()
    }
