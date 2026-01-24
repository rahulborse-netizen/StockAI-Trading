from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class BacktestResult:
    equity_curve: pd.Series
    benchmark_equity: pd.Series
    daily_returns: pd.Series
    stats: dict


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def _sharpe(daily_returns: pd.Series, periods_per_year: int = 252) -> float:
    r = daily_returns.dropna()
    if r.empty:
        return float("nan")
    mu = r.mean()
    sd = r.std(ddof=0)
    if sd == 0:
        return float("nan")
    return float((mu / sd) * np.sqrt(periods_per_year))


def _cagr(equity: pd.Series, periods_per_year: int = 252) -> float:
    if equity.empty:
        return 0.0
    n = max(int(equity.shape[0]), 1)
    total = float(equity.iloc[-1])
    return float(total ** (periods_per_year / n) - 1.0)


def backtest_long_cash_from_prob(
    df: pd.DataFrame,
    prob_up: pd.Series,
    prob_threshold: float = 0.55,
    fee_bps: float = 10.0,
) -> BacktestResult:
    """
    Simple daily long/cash backtest:
    - If prob_up >= threshold => long next day (position=1), else cash (position=0)
    - Use close-to-close returns
    - Apply fee (in basis points) on position changes (round-trip modeled as 1 fee per change)
    """
    close = df["close"].copy()
    ret = close.pct_change(1)

    # Restrict to the period where we actually have model outputs
    p = prob_up.reindex(close.index)
    first_valid = p.first_valid_index()
    if first_valid is None:
        raise ValueError("prob_up has no valid values; cannot backtest.")
    close = close.loc[first_valid:]
    ret = ret.loc[first_valid:]
    p = p.loc[first_valid:].ffill()

    # Align and create positions; act on next bar to avoid look-ahead
    pos = (p >= prob_threshold).astype(int).shift(1).fillna(0).astype(int)

    # transaction cost when position changes
    turnover = pos.diff().abs().fillna(0)
    fee = (fee_bps / 10000.0) * turnover

    strat_ret = pos * ret - fee
    equity = (1.0 + strat_ret.fillna(0)).cumprod()

    # Benchmark: buy & hold (no fees)
    bench_ret = ret.fillna(0)
    bench_equity = (1.0 + bench_ret).cumprod()

    stats = {
        "days": int(strat_ret.dropna().shape[0]),
        "total_return": float(equity.iloc[-1] - 1.0) if not equity.empty else 0.0,
        "max_drawdown": _max_drawdown(equity) if not equity.empty else 0.0,
        "sharpe": _sharpe(strat_ret),
        "cagr": _cagr(equity),
        "benchmark_total_return": float(bench_equity.iloc[-1] - 1.0) if not bench_equity.empty else 0.0,
        "benchmark_cagr": _cagr(bench_equity),
        "avg_position": float(pos.mean()) if not pos.empty else 0.0,
        "fee_bps": float(fee_bps),
        "prob_threshold": float(prob_threshold),
    }
    return BacktestResult(equity_curve=equity, benchmark_equity=bench_equity, daily_returns=strat_ret, stats=stats)

