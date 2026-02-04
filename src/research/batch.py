from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.research.backtest import backtest_long_cash_from_prob
from src.research.data import download_yahoo_ohlcv
from src.research.features import add_label_forward_return_up, clean_ml_frame, make_features
from src.research.index_analysis import analyze_index_correlation
from src.research.ml import train_baseline_classifier, walk_forward_predict_proba
from src.research.portfolio_backtest import PortfolioBacktestResult, PositionSizing, backtest_portfolio


@dataclass(frozen=True)
class BatchRunResult:
    summary: pd.DataFrame
    outdir: Path


DEFAULT_FEATURE_COLS = [
    "ret_1",
    "ret_5",
    "vol_10",
    "sma_10",
    "sma_50",
    "ema_20",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "vol_chg_1",
    "vol_sma_20",
]


def run_batch_research(
    tickers: list[str],
    start: str,
    end: str,
    interval: str,
    outdir: str | Path,
    refresh: bool = False,
    test_size: float = 0.2,
    random_state: int = 42,
    label_days: int = 1,
    label_threshold: float = 0.0,
    prob_threshold: float = 0.55,
    fee_bps: float = 10.0,
    compare_index: str | None = None,
) -> BatchRunResult:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []

    for t in tickers:
        t_dir = outdir / t.replace(":", "_").replace("/", "_")
        t_dir.mkdir(parents=True, exist_ok=True)

        cache = t_dir / f"{t}.csv"
        try:
            ohlcv = download_yahoo_ohlcv(
                ticker=t,
                start=start,
                end=end,
                interval=interval,
                cache_path=cache,
                refresh=refresh,
            )
            feat = make_features(ohlcv.df)
            labeled = add_label_forward_return_up(feat, days=label_days, threshold=label_threshold)
            ml_df = clean_ml_frame(labeled, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")

            (_, pred) = train_baseline_classifier(
                df=ml_df,
                feature_cols=DEFAULT_FEATURE_COLS,
                label_col="label_up",
                test_size=test_size,
                random_state=random_state,
            )

            bt = backtest_long_cash_from_prob(
                df=ml_df,
                prob_up=pred["prob_up"],
                prob_threshold=prob_threshold,
                fee_bps=fee_bps,
            )

            (t_dir / "stats.json").write_text(json.dumps(bt.stats, indent=2))

            row = {"ticker": t, **bt.stats}
            
            # Add index-relative metrics if compare_index is provided
            if compare_index:
                try:
                    index_ohlcv = download_yahoo_ohlcv(
                        ticker=compare_index,
                        start=start,
                        end=end,
                        interval=interval,
                        cache_path=outdir / f"{compare_index.replace('^', '').replace('.NS', '').replace('.BO', '')}_index.csv",
                        refresh=refresh,
                    )
                    index_returns = index_ohlcv.df["close"].pct_change(1).dropna()
                    stock_returns = ohlcv.df["close"].pct_change(1).dropna()
                    
                    from src.research.index_analysis import analyze_index_correlation
                    corr_metrics = analyze_index_correlation(index_returns, stock_returns)
                    row.update({f"index_{k}": v for k, v in corr_metrics.items()})
                except Exception:  # noqa: BLE001
                    pass  # Skip index comparison if it fails
            
            rows.append(row)
        except Exception as e:  # noqa: BLE001
            rows.append({"ticker": t, "error": str(e)})

    summary = pd.DataFrame(rows)
    summary_path = outdir / "summary.csv"
    summary.to_csv(summary_path, index=False)

    return BatchRunResult(summary=summary, outdir=outdir)


def run_portfolio_backtest(
    tickers: list[str],
    start: str,
    end: str,
    interval: str,
    outdir: str | Path,
    refresh: bool = False,
    random_state: int = 42,
    label_days: int = 1,
    label_threshold: float = 0.0,
    prob_threshold: float = 0.55,
    fee_bps: float = 10.0,
    position_sizing: str = "equal_weight",
    min_train_size: int = 252,
    retrain_every: int = 20,
) -> PortfolioBacktestResult:
    """
    Run portfolio-level backtest (multiple assets simultaneously).
    
    Args:
        tickers: List of ticker symbols
        start: Start date YYYY-MM-DD
        end: End date YYYY-MM-DD
        interval: Data interval (default: "1d")
        outdir: Output directory
        refresh: Re-download data even if cache exists
        random_state: Random seed
        label_days: Label horizon in trading days
        label_threshold: Label threshold for forward return
        prob_threshold: Probability threshold to go long
        fee_bps: Transaction fee in basis points
        position_sizing: Position sizing method ("equal_weight" or "custom")
        min_train_size: Minimum training size for walk-forward
        retrain_every: Retrain frequency for walk-forward
        
    Returns:
        PortfolioBacktestResult with aggregated portfolio metrics
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Download data and prepare features for all tickers
    ticker_data = {}
    ticker_probabilities = {}
    
    for t in tickers:
        t_dir = outdir / t.replace(":", "_").replace("/", "_")
        t_dir.mkdir(parents=True, exist_ok=True)
        cache = t_dir / f"{t}.csv"
        
        try:
            ohlcv = download_yahoo_ohlcv(
                ticker=t,
                start=start,
                end=end,
                interval=interval,
                cache_path=cache,
                refresh=refresh,
            )
            feat = make_features(ohlcv.df)
            labeled = add_label_forward_return_up(feat, days=label_days, threshold=label_threshold)
            ml_df = clean_ml_frame(labeled, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")
            
            # Use walk-forward for portfolio backtest
            prob = walk_forward_predict_proba(
                df=ml_df,
                feature_cols=DEFAULT_FEATURE_COLS,
                label_col="label_up",
                min_train_size=min_train_size,
                retrain_every=retrain_every,
                random_state=random_state,
            )
            
            ticker_data[t] = ml_df
            ticker_probabilities[t] = prob
            
        except Exception as e:  # noqa: BLE001
            raise RuntimeError(f"Failed to prepare data for {t}: {e}") from e
    
    # Determine position sizing
    sizing_enum = PositionSizing.EQUAL_WEIGHT
    if position_sizing == "custom":
        sizing_enum = PositionSizing.CUSTOM
    elif position_sizing != "equal_weight":
        raise ValueError(f"Unsupported position_sizing: {position_sizing}")
    
    # Run portfolio backtest
    portfolio_result = backtest_portfolio(
        ticker_data=ticker_data,
        ticker_probabilities=ticker_probabilities,
        prob_threshold=prob_threshold,
        fee_bps=fee_bps,
        position_sizing=sizing_enum,
    )
    
    # Save portfolio results
    portfolio_result.equity_curve.to_csv(outdir / "portfolio_equity_curve.csv", header=["equity"])
    portfolio_result.benchmark_equity.to_csv(outdir / "portfolio_benchmark_equity_curve.csv", header=["equity"])
    portfolio_result.position_weights.to_csv(outdir / "portfolio_position_weights.csv")
    (outdir / "portfolio_stats.json").write_text(json.dumps(portfolio_result.stats, indent=2))
    
    # Save individual results summary
    individual_summary = []
    for ticker, bt_result in portfolio_result.individual_results.items():
        individual_summary.append({"ticker": ticker, **bt_result.stats})
    
    pd.DataFrame(individual_summary).to_csv(outdir / "individual_summary.csv", index=False)
    
    return portfolio_result

