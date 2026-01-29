from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class IndexComparison:
    index_returns: pd.Series
    constituent_returns: dict[str, pd.Series]
    relative_strength: dict[str, pd.Series]
    correlation_matrix: pd.DataFrame
    sector_breakdown: dict[str, list[str]] | None = None


def calculate_relative_strength(
    stock_returns: pd.Series,
    index_returns: pd.Series,
    window: int = 20,
) -> pd.Series:
    """
    Calculate relative strength of a stock vs index.
    
    Args:
        stock_returns: Stock daily returns
        index_returns: Index daily returns (aligned to stock dates)
        window: Rolling window for calculation (default: 20 days)
        
    Returns:
        Relative strength series (positive = outperforming, negative = underperforming)
    """
    # Align dates
    common_dates = stock_returns.index.intersection(index_returns.index)
    stock_aligned = stock_returns.reindex(common_dates)
    index_aligned = index_returns.reindex(common_dates)
    
    # Calculate cumulative returns over rolling window
    stock_cumret = (1 + stock_aligned).rolling(window=window).apply(lambda x: x.prod() - 1.0, raw=False)
    index_cumret = (1 + index_aligned).rolling(window=window).apply(lambda x: x.prod() - 1.0, raw=False)
    
    # Relative strength = stock return - index return
    relative_strength = stock_cumret - index_cumret
    
    return relative_strength


def compare_index_vs_constituents(
    index_data: pd.DataFrame,  # OHLCV for index
    constituent_data: dict[str, pd.DataFrame],  # ticker -> OHLCV
) -> IndexComparison:
    """
    Compare index performance vs its constituent stocks.
    
    Args:
        index_data: Index OHLCV dataframe
        constituent_data: Dictionary mapping ticker symbols to OHLCV dataframes
        
    Returns:
        IndexComparison with relative strength, correlations, etc.
    """
    # Calculate returns
    index_returns = index_data["close"].pct_change(1).dropna()
    
    constituent_returns = {}
    for ticker, df in constituent_data.items():
        ret = df["close"].pct_change(1).dropna()
        constituent_returns[ticker] = ret
    
    # Calculate relative strength for each constituent
    relative_strength = {}
    for ticker, stock_ret in constituent_returns.items():
        rs = calculate_relative_strength(stock_ret, index_returns)
        relative_strength[ticker] = rs
    
    # Calculate correlation matrix
    # Align all returns to common dates
    all_dates = set(index_returns.index)
    for ret in constituent_returns.values():
        all_dates.update(ret.index)
    all_dates = sorted(all_dates)
    
    returns_df = pd.DataFrame(index=all_dates)
    returns_df["INDEX"] = index_returns.reindex(all_dates)
    for ticker, ret in constituent_returns.items():
        returns_df[ticker] = ret.reindex(all_dates)
    
    returns_df = returns_df.dropna()
    correlation_matrix = returns_df.corr()
    
    return IndexComparison(
        index_returns=index_returns,
        constituent_returns=constituent_returns,
        relative_strength=relative_strength,
        correlation_matrix=correlation_matrix,
        sector_breakdown=None,  # Could be enhanced with sector data
    )


def analyze_index_correlation(
    index_returns: pd.Series,
    stock_returns: pd.Series,
) -> dict:
    """
    Analyze correlation between index and a stock.
    
    Args:
        index_returns: Index daily returns
        stock_returns: Stock daily returns
        
    Returns:
        Dictionary with correlation metrics
    """
    # Align dates
    common_dates = index_returns.index.intersection(stock_returns.index)
    index_aligned = index_returns.reindex(common_dates)
    stock_aligned = stock_returns.reindex(common_dates)
    
    # Remove NaN
    valid_mask = ~(index_aligned.isna() | stock_aligned.isna())
    index_clean = index_aligned[valid_mask]
    stock_clean = stock_aligned[valid_mask]
    
    if len(index_clean) < 10:
        return {
            "correlation": np.nan,
            "beta": np.nan,
            "alpha": np.nan,
            "r_squared": np.nan,
        }
    
    # Calculate correlation
    correlation = index_clean.corr(stock_clean)
    
    # Calculate beta (slope of regression)
    # Beta = Cov(stock, index) / Var(index)
    covariance = np.cov(stock_clean, index_clean)[0, 1]
    index_variance = np.var(index_clean)
    beta = covariance / index_variance if index_variance > 0 else np.nan
    
    # Calculate alpha (intercept)
    # Alpha = mean(stock) - beta * mean(index)
    alpha = stock_clean.mean() - beta * index_clean.mean() if not np.isnan(beta) else np.nan
    
    # Calculate R-squared
    if not np.isnan(beta) and not np.isnan(alpha):
        predicted = alpha + beta * index_clean
        ss_res = ((stock_clean - predicted) ** 2).sum()
        ss_tot = ((stock_clean - stock_clean.mean()) ** 2).sum()
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else np.nan
    else:
        r_squared = np.nan
    
    return {
        "correlation": float(correlation),
        "beta": float(beta),
        "alpha": float(alpha),
        "r_squared": float(r_squared),
    }


def get_top_outperformers(
    relative_strength: dict[str, pd.Series],
    top_n: int = 10,
) -> list[tuple[str, float]]:
    """
    Get top N outperforming stocks based on relative strength.
    
    Args:
        relative_strength: Dictionary mapping tickers to relative strength series
        top_n: Number of top performers to return
        
    Returns:
        List of (ticker, avg_relative_strength) tuples, sorted descending
    """
    avg_rs = {}
    for ticker, rs_series in relative_strength.items():
        rs_clean = rs_series.dropna()
        if not rs_clean.empty:
            avg_rs[ticker] = rs_clean.mean()
    
    sorted_rs = sorted(avg_rs.items(), key=lambda x: x[1], reverse=True)
    return sorted_rs[:top_n]


def get_top_underperformers(
    relative_strength: dict[str, pd.Series],
    top_n: int = 10,
) -> list[tuple[str, float]]:
    """
    Get top N underperforming stocks based on relative strength.
    
    Args:
        relative_strength: Dictionary mapping tickers to relative strength series
        top_n: Number of worst performers to return
        
    Returns:
        List of (ticker, avg_relative_strength) tuples, sorted ascending
    """
    avg_rs = {}
    for ticker, rs_series in relative_strength.items():
        rs_clean = rs_series.dropna()
        if not rs_clean.empty:
            avg_rs[ticker] = rs_clean.mean()
    
    sorted_rs = sorted(avg_rs.items(), key=lambda x: x[1], reverse=False)
    return sorted_rs[:top_n]
