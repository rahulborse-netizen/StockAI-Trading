"""
Phase 5.2: Backtesting Infrastructure
Walk-forward analysis, Monte Carlo simulation, parameter optimization, strategy comparison.
"""
import logging
import random
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


def walk_forward_analysis(
    returns: np.ndarray,
    train_ratio: float = 0.7,
    step_size: int = 1,
) -> Dict[str, Any]:
    """
    Walk-forward: split into train/test windows, step forward.
    returns: period returns array.
    """
    n = len(returns)
    if n < 20:
        return {'error': 'Insufficient data', 'n': n}
    train_size = max(10, int(n * train_ratio))
    test_size = n - train_size
    if test_size < 5:
        return {'error': 'Test set too small', 'n': n}
    train_ret = float(np.mean(returns[:train_size]))
    train_vol = float(np.std(returns[:train_size])) or 1e-8
    test_ret = float(np.mean(returns[train_size:]))
    test_vol = float(np.std(returns[train_size:])) or 1e-8
    return {
        'train_size': train_size,
        'test_size': test_size,
        'train_return': train_ret,
        'train_volatility': train_vol,
        'test_return': test_ret,
        'test_volatility': test_vol,
        'out_of_sample_sharpe': test_ret / test_vol if test_vol else 0.0,
    }


def monte_carlo_simulation(
    returns: np.ndarray,
    n_simulations: int = 1000,
    horizon_days: int = 252,
) -> Dict[str, Any]:
    """Monte Carlo: bootstrap returns to simulate future paths."""
    if len(returns) < 10:
        return {'error': 'Insufficient data'}
    returns = np.asarray(returns, dtype=float)
    paths = []
    for _ in range(n_simulations):
        idx = np.random.randint(0, len(returns), size=horizon_days)
        path = np.cumprod(1 + returns[idx]) - 1
        paths.append(path[-1])
    paths = np.array(paths)
    return {
        'mean_final_return': float(np.mean(paths)),
        'std_final_return': float(np.std(paths)),
        'percentile_5': float(np.percentile(paths, 5)),
        'percentile_95': float(np.percentile(paths, 95)),
        'n_simulations': n_simulations,
        'horizon_days': horizon_days,
    }


def parameter_optimization(
    param_grid: Dict[str, List[Any]],
    objective_fn: Callable[..., float],
    maximize: bool = True,
) -> Dict[str, Any]:
    """
    Grid search over param_grid; objective_fn(**params) -> score.
    """
    keys = list(param_grid.keys())
    if not keys:
        return {'best_params': {}, 'best_score': None}
    n = 1
    for v in param_grid.values():
        n *= len(v)
    best_score = None
    best_params = None
    for _ in range(min(n, 100)):  # cap iterations
        params = {k: random.choice(param_grid[k]) for k in keys}
        try:
            score = objective_fn(**params)
        except Exception:
            continue
        if best_score is None or (maximize and score > best_score) or (not maximize and score < best_score):
            best_score = score
            best_params = params
    return {
        'best_params': best_params or {},
        'best_score': best_score,
    }


def strategy_comparison(
    strategy_returns: Dict[str, np.ndarray],
    risk_free_rate: float = 0.0,
) -> List[Dict[str, Any]]:
    """Compare multiple strategies by Sharpe, total return, max drawdown."""
    results = []
    for name, rets in strategy_returns.items():
        rets = np.asarray(rets, dtype=float)
        if len(rets) < 2:
            results.append({'strategy': name, 'error': 'Insufficient data'})
            continue
        mean_ret = np.mean(rets)
        vol = np.std(rets) or 1e-8
        sharpe = (mean_ret - risk_free_rate / 252) / vol * np.sqrt(252)
        cum = np.cumprod(1 + rets) - 1
        peak = np.maximum.accumulate(cum)
        dd = (cum - peak) / (peak + 1e-12)
        max_dd = float(np.min(dd))
        total_ret = float(cum[-1])
        results.append({
            'strategy': name,
            'sharpe_ratio': float(sharpe),
            'total_return': total_ret,
            'max_drawdown': max_dd,
            'volatility': float(vol),
        })
    results.sort(key=lambda x: x.get('sharpe_ratio', 0), reverse=True)
    return results
