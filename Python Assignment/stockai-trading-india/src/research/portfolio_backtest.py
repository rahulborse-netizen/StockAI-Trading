from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from src.research.backtest import BacktestResult, backtest_long_cash_from_prob


class PositionSizing(Enum):
    EQUAL_WEIGHT = "equal_weight"
    MARKET_CAP_WEIGHT = "market_cap_weight"  # Not implemented yet - would need market cap data
    CUSTOM = "custom"


@dataclass(frozen=True)
class PortfolioBacktestResult:
    equity_curve: pd.Series
    benchmark_equity: pd.Series
    daily_returns: pd.Series
    position_weights: pd.DataFrame  # Date x Ticker weights
    individual_results: dict[str, BacktestResult]  # Per-ticker backtest results
    stats: dict


def backtest_portfolio(
    ticker_data: dict[str, pd.DataFrame],  # ticker -> OHLCV dataframe
    ticker_probabilities: dict[str, pd.Series],  # ticker -> prob_up series
    prob_threshold: float = 0.55,
    fee_bps: float = 10.0,
    position_sizing: PositionSizing = PositionSizing.EQUAL_WEIGHT,
    custom_weights: Optional[dict[str, float]] = None,
    rebalance_frequency: str = "daily",  # "daily", "weekly", "monthly"
) -> PortfolioBacktestResult:
    """
    Backtest a portfolio of multiple assets simultaneously.
    
    Args:
        ticker_data: Dictionary mapping ticker symbols to OHLCV dataframes
        ticker_probabilities: Dictionary mapping ticker symbols to probability series
        prob_threshold: Probability threshold to go long (default: 0.55)
        fee_bps: Transaction fee in basis points per position change (default: 10.0)
        position_sizing: Position sizing method (default: EQUAL_WEIGHT)
        custom_weights: Custom weights dict (ticker -> weight) if position_sizing=CUSTOM
        rebalance_frequency: How often to rebalance positions (default: "daily")
        
    Returns:
        PortfolioBacktestResult with aggregated portfolio metrics
        
    Raises:
        ValueError: If ticker_data and ticker_probabilities don't match, or invalid inputs
    """
    if not ticker_data:
        raise ValueError("ticker_data cannot be empty")
    
    if set(ticker_data.keys()) != set(ticker_probabilities.keys()):
        missing_in_probs = set(ticker_data.keys()) - set(ticker_probabilities.keys())
        missing_in_data = set(ticker_probabilities.keys()) - set(ticker_data.keys())
        raise ValueError(
            f"ticker_data and ticker_probabilities must have matching keys. "
            f"Missing in probabilities: {missing_in_probs}. "
            f"Missing in data: {missing_in_data}."
        )
    
    # Run individual backtests first
    individual_results = {}
    for ticker in ticker_data.keys():
        bt = backtest_long_cash_from_prob(
            df=ticker_data[ticker],
            prob_up=ticker_probabilities[ticker],
            prob_threshold=prob_threshold,
            fee_bps=fee_bps,
        )
        individual_results[ticker] = bt
    
    # Align all dates
    all_dates = set()
    for df in ticker_data.values():
        all_dates.update(df.index)
    all_dates = sorted(all_dates)
    
    if not all_dates:
        raise ValueError("No common dates found across tickers")
    
    # Get individual equity curves aligned to common dates
    equity_curves = {}
    for ticker, bt_result in individual_results.items():
        equity_curves[ticker] = bt_result.equity_curve.reindex(all_dates).ffill().fillna(1.0)
    
    # Calculate position weights
    position_weights_df = pd.DataFrame(index=all_dates, columns=list(ticker_data.keys()))
    
    for date in all_dates:
        # Determine which assets to hold based on probabilities
        weights = {}
        active_tickers = []
        
        for ticker in ticker_data.keys():
            prob_series = ticker_probabilities[ticker]
            if date in prob_series.index and not pd.isna(prob_series.loc[date]):
                prob = prob_series.loc[date]
                if prob >= prob_threshold:
                    active_tickers.append(ticker)
        
        # Calculate weights based on sizing method
        if position_sizing == PositionSizing.EQUAL_WEIGHT:
            if active_tickers:
                weight_per_ticker = 1.0 / len(active_tickers)
                for ticker in active_tickers:
                    weights[ticker] = weight_per_ticker
        elif position_sizing == PositionSizing.CUSTOM:
            if custom_weights is None:
                raise ValueError("custom_weights must be provided when position_sizing=CUSTOM")
            total_custom_weight = sum(custom_weights.get(t, 0.0) for t in active_tickers)
            if total_custom_weight > 0:
                for ticker in active_tickers:
                    weights[ticker] = custom_weights.get(ticker, 0.0) / total_custom_weight
        else:
            raise ValueError(f"Unsupported position_sizing: {position_sizing}")
        
        # Store weights
        for ticker in ticker_data.keys():
            position_weights_df.loc[date, ticker] = weights.get(ticker, 0.0)
    
    position_weights_df = position_weights_df.fillna(0.0).astype(float)
    
    # Calculate portfolio equity curve (weighted sum of individual equity curves)
    portfolio_equity = pd.Series(index=all_dates, dtype=float)
    for date in all_dates:
        equity_sum = 0.0
        for ticker in ticker_data.keys():
            weight = position_weights_df.loc[date, ticker]
            if weight > 0 and ticker in equity_curves:
                equity_sum += weight * equity_curves[ticker].loc[date]
        portfolio_equity.loc[date] = equity_sum if equity_sum > 0 else 1.0
    
    # Normalize to start at 1.0
    if not portfolio_equity.empty:
        portfolio_equity = portfolio_equity / portfolio_equity.iloc[0]
    
    # Calculate daily returns
    portfolio_returns = portfolio_equity.pct_change(1).fillna(0.0)
    
    # Benchmark: equal-weighted buy-and-hold of all assets
    benchmark_equity = pd.Series(index=all_dates, dtype=float)
    for date in all_dates:
        bench_sum = 0.0
        for ticker in ticker_data.keys():
            if ticker in equity_curves:
                bench_sum += equity_curves[ticker].loc[date]
        benchmark_equity.loc[date] = bench_sum / len(ticker_data) if ticker_data else 1.0
    
    if not benchmark_equity.empty:
        benchmark_equity = benchmark_equity / benchmark_equity.iloc[0]
    
    # Calculate portfolio-level stats
    from src.research.backtest import _max_drawdown, _sharpe, _cagr
    
    stats = {
        "days": int(portfolio_returns.dropna().shape[0]),
        "total_return": float(portfolio_equity.iloc[-1] - 1.0) if not portfolio_equity.empty else 0.0,
        "max_drawdown": _max_drawdown(portfolio_equity) if not portfolio_equity.empty else 0.0,
        "sharpe": _sharpe(portfolio_returns),
        "cagr": _cagr(portfolio_equity),
        "benchmark_total_return": float(benchmark_equity.iloc[-1] - 1.0) if not benchmark_equity.empty else 0.0,
        "benchmark_cagr": _cagr(benchmark_equity),
        "num_assets": len(ticker_data),
        "avg_position_count": float((position_weights_df > 0).sum(axis=1).mean()) if not position_weights_df.empty else 0.0,
        "fee_bps": float(fee_bps),
        "prob_threshold": float(prob_threshold),
        "position_sizing": position_sizing.value,
    }
    
    return PortfolioBacktestResult(
        equity_curve=portfolio_equity,
        benchmark_equity=benchmark_equity,
        daily_returns=portfolio_returns,
        position_weights=position_weights_df,
        individual_results=individual_results,
        stats=stats,
    )
