from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.research.backtest import backtest_long_cash_from_prob
from src.research.batch import run_batch_research, run_portfolio_backtest
from src.research.data import download_yahoo_ohlcv
from src.research.features import add_label_forward_return_up, clean_ml_frame, make_features
from src.research.ml import save_model, train_baseline_classifier, walk_forward_predict_proba
from src.research.universe import load_universe_file
from src.research.visualize import generate_backtest_report
from src.paper.paper_trader import paper_trade_long_cash


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


def cmd_research(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cache = Path(args.cache) if args.cache else (outdir / f"{args.ticker.replace(':', '_').replace('/', '_')}.csv")
    ohlcv = download_yahoo_ohlcv(
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        interval=args.interval,
        cache_path=cache,
        refresh=args.refresh,
    )

    feat = make_features(ohlcv.df)
    labeled = add_label_forward_return_up(feat, days=args.label_days, threshold=args.label_threshold)
    ml_df = clean_ml_frame(labeled, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")

    if args.train_mode == "walkforward":
        # Auto-adjust if the user picked a short date range
        min_train = args.min_train_size
        if len(ml_df) <= min_train:
            min_train = max(50, int(len(ml_df) * 0.6))

        prob = walk_forward_predict_proba(
            df=ml_df,
            feature_cols=DEFAULT_FEATURE_COLS,
            label_col="label_up",
            min_train_size=min_train,
            retrain_every=args.retrain_every,
            random_state=args.random_state,
        )
        pred = pd.DataFrame(index=ml_df.index, data={"prob_up": prob, "y_true": ml_df["label_up"].values})
        trained = None
        model_path = None
    else:
        (trained, pred) = train_baseline_classifier(
            df=ml_df,
            feature_cols=DEFAULT_FEATURE_COLS,
            label_col="label_up",
            test_size=args.test_size,
            random_state=args.random_state,
        )
        model_path = outdir / "model.joblib"
        save_model(trained.model, str(model_path))

    pred_path = outdir / "predictions.csv"
    pred.to_csv(pred_path, index=True)

    bt = backtest_long_cash_from_prob(
        df=ml_df,
        prob_up=pred["prob_up"],
        prob_threshold=args.prob_threshold,
        fee_bps=args.fee_bps,
    )

    equity_path = outdir / "equity_curve.csv"
    pd.DataFrame({"equity": bt.equity_curve}).to_csv(equity_path, index=True)
    bench_path = outdir / "benchmark_equity_curve.csv"
    pd.DataFrame({"equity": bt.benchmark_equity}).to_csv(bench_path, index=True)

    stats_path = outdir / "stats.json"
    stats_path.write_text(json.dumps(bt.stats, indent=2))

    # Auto-generate visualization report
    try:
        report_path = generate_backtest_report(
            result=bt,
            outdir=outdir,
            ticker=args.ticker,
            include_plots=True,
        )
        print(f"- HTML Report: {report_path}")
    except Exception as e:
        print(f"Warning: Failed to generate visualization report: {e}")

    print("Research run complete")
    print(f"- Data cache: {cache}")
    if model_path:
        print(f"- Model: {model_path}")
    print(f"- Predictions: {pred_path}")
    print(f"- Equity curve: {equity_path}")
    print(f"- Benchmark equity curve: {bench_path}")
    print(f"- Stats: {stats_path}")
    print(json.dumps(bt.stats, indent=2))

    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    uni = load_universe_file(args.universe)
    
    if args.portfolio_mode:
        # Portfolio backtest mode
        res = run_portfolio_backtest(
            tickers=uni.tickers,
            start=args.start,
            end=args.end,
            interval=args.interval,
            outdir=args.outdir,
            refresh=args.refresh,
            random_state=args.random_state,
            label_days=args.label_days,
            label_threshold=args.label_threshold,
            prob_threshold=args.prob_threshold,
            fee_bps=args.fee_bps,
            position_sizing=args.position_sizing,
            min_train_size=getattr(args, "min_train_size", 252),
            retrain_every=getattr(args, "retrain_every", 20),
        )
        
        print("Portfolio backtest complete")
        print(f"- Universe: {uni.name} ({len(uni.tickers)} tickers)")
        print(f"- Portfolio equity curve: {args.outdir}/portfolio_equity_curve.csv")
        print(f"- Position weights: {args.outdir}/portfolio_position_weights.csv")
        print(f"- Portfolio stats: {args.outdir}/portfolio_stats.json")
        print(json.dumps(res.stats, indent=2))
    else:
        # Individual backtest mode (original behavior)
        res = run_batch_research(
            tickers=uni.tickers,
            start=args.start,
            end=args.end,
            interval=args.interval,
            outdir=args.outdir,
            refresh=args.refresh,
            test_size=args.test_size,
            random_state=args.random_state,
            label_days=args.label_days,
            label_threshold=args.label_threshold,
            prob_threshold=args.prob_threshold,
            fee_bps=args.fee_bps,
            compare_index=getattr(args, "compare_index", None),
        )

        print("Batch run complete")
        print(f"- Universe: {uni.name} ({len(uni.tickers)} tickers)")
        print(f"- Output dir: {res.outdir}")
        print(f"- Summary: {res.outdir / 'summary.csv'}")
        # Note: Individual reports are generated in each ticker's subdirectory
        print(f"- Individual reports: Check subdirectories in {res.outdir}")
    
    return 0


def cmd_paper(args: argparse.Namespace) -> int:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    cache = Path(args.cache) if args.cache else (outdir / f"{args.ticker.replace(':', '_').replace('/', '_')}.csv")
    ohlcv = download_yahoo_ohlcv(
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        interval=args.interval,
        cache_path=cache,
        refresh=args.refresh,
    )

    feat = make_features(ohlcv.df)
    labeled = add_label_forward_return_up(feat, days=args.label_days, threshold=args.label_threshold)
    ml_df = clean_ml_frame(labeled, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")

    prob = walk_forward_predict_proba(
        df=ml_df,
        feature_cols=DEFAULT_FEATURE_COLS,
        label_col="label_up",
        min_train_size=max(50, int(len(ml_df) * 0.6)) if len(ml_df) <= args.min_train_size else args.min_train_size,
        retrain_every=args.retrain_every,
        random_state=args.random_state,
    )

    equity_df, trades_df = paper_trade_long_cash(
        ohlcv=ml_df,
        prob_up=prob,
        prob_threshold=args.prob_threshold,
        fee_bps=args.fee_bps,
        initial_cash=args.initial_cash,
    )

    equity_path = outdir / "paper_equity.csv"
    trades_path = outdir / "paper_trades.csv"
    equity_df.to_csv(equity_path, index=True)
    trades_df.to_csv(trades_path, index=True)

    print("Paper trading simulation complete")
    print(f"- Equity: {equity_path}")
    print(f"- Trades: {trades_path}")
    return 0


def cmd_visualize(args: argparse.Namespace) -> int:
    """Generate visualization report from existing backtest results."""
    outdir = Path(args.outdir)
    
    if not outdir.exists():
        print(f"Error: Output directory does not exist: {outdir}")
        return 1
    
    # Try to load backtest results
    equity_path = outdir / "equity_curve.csv"
    benchmark_path = outdir / "benchmark_equity_curve.csv"
    stats_path = outdir / "stats.json"
    
    if not equity_path.exists():
        print(f"Error: equity_curve.csv not found in {outdir}")
        print("This command requires existing backtest results.")
        return 1
    
    try:
        # Load equity curves
        equity_df = pd.read_csv(equity_path, parse_dates=True, index_col=0)
        equity_curve = equity_df["equity"]
        
        benchmark_equity = None
        if benchmark_path.exists():
            bench_df = pd.read_csv(benchmark_path, parse_dates=True, index_col=0)
            benchmark_equity = bench_df["equity"]
        
        # Load stats
        stats = {}
        if stats_path.exists():
            stats = json.loads(stats_path.read_text())
        
        # Create BacktestResult-like object
        from src.research.backtest import BacktestResult
        daily_returns = equity_curve.pct_change(1)
        
        result = BacktestResult(
            equity_curve=equity_curve,
            benchmark_equity=benchmark_equity if benchmark_equity is not None else equity_curve,
            daily_returns=daily_returns,
            stats=stats,
        )
        
        # Generate report
        report_path = generate_backtest_report(
            result=result,
            outdir=outdir,
            ticker=args.ticker,
            include_plots=True,
        )
        
        print("Visualization report generated successfully")
        print(f"- Report: {report_path}")
        return 0
        
    except Exception as e:
        print(f"Error generating visualization report: {e}")
        import traceback
        traceback.print_exc()
        return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stockai",
        description=(
            "StockAI (India) - research/backtesting CLI. Educational use only; "
            "do not treat outputs as financial advice."
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("research", help="Download data, train a baseline ML model, and backtest long/cash strategy.")
    r.add_argument("--ticker", required=True, help="Yahoo ticker, e.g. RELIANCE.NS, TCS.NS")
    r.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    r.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    r.add_argument("--interval", default="1d", help="Data interval (default: 1d)")
    r.add_argument("--cache", default=None, help="Optional CSV cache path")
    r.add_argument("--refresh", action="store_true", help="Re-download data even if cache exists")

    r.add_argument("--outdir", default="outputs/research", help="Output directory")
    r.add_argument("--test-size", type=float, default=0.2, help="Fraction of data used as test (time-based)")
    r.add_argument("--random-state", type=int, default=42, help="Random seed")
    r.add_argument("--label-days", type=int, default=1, help="Label horizon in trading days (default: 1)")
    r.add_argument("--label-threshold", type=float, default=0.0, help="Label threshold for next-day return")
    r.add_argument("--prob-threshold", type=float, default=0.55, help="Prob threshold to go long")
    r.add_argument("--fee-bps", type=float, default=10.0, help="Transaction fee per position change (bps)")
    r.add_argument("--train-mode", choices=["split", "walkforward"], default="walkforward", help="Training mode")
    r.add_argument("--min-train-size", type=int, default=252, help="Min rows before walk-forward starts")
    r.add_argument("--retrain-every", type=int, default=20, help="Retrain frequency (rows) for walk-forward")
    r.set_defaults(func=cmd_research)

    b = sub.add_parser("batch", help="Run research/backtest across a universe of tickers and aggregate results.")
    b.add_argument("--universe", default="configs/universe_nifty50.txt", help="Path to universe file (one ticker per line)")
    b.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    b.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    b.add_argument("--interval", default="1d", help="Data interval (default: 1d)")
    b.add_argument("--refresh", action="store_true", help="Re-download data even if cache exists")
    b.add_argument("--outdir", default="outputs/batch", help="Output directory")
    b.add_argument("--portfolio-mode", action="store_true", help="Run portfolio backtest (multiple positions simultaneously) instead of individual backtests")
    b.add_argument("--position-sizing", choices=["equal_weight", "custom"], default="equal_weight", help="Position sizing method for portfolio mode")
    b.add_argument("--test-size", type=float, default=0.2, help="Fraction of data used as test (time-based, ignored in portfolio mode)")
    b.add_argument("--random-state", type=int, default=42, help="Random seed")
    b.add_argument("--label-days", type=int, default=1, help="Label horizon in trading days (default: 1)")
    b.add_argument("--label-threshold", type=float, default=0.0, help="Label threshold for next-day return")
    b.add_argument("--prob-threshold", type=float, default=0.55, help="Prob threshold to go long")
    b.add_argument("--fee-bps", type=float, default=10.0, help="Transaction fee per position change (bps)")
    b.add_argument("--min-train-size", type=int, default=252, help="Min rows before walk-forward starts (portfolio mode)")
    b.add_argument("--retrain-every", type=int, default=20, help="Retrain frequency (rows) for walk-forward (portfolio mode)")
    b.add_argument("--compare-index", default=None, help="Compare strategy returns vs index benchmark (e.g., ^NSEI, NIFTYBEES.NS)")
    b.set_defaults(func=cmd_batch)

    ppr = sub.add_parser("paper", help="Run a paper-trading simulation (no broker).")
    ppr.add_argument("--ticker", required=True, help="Yahoo ticker, e.g. RELIANCE.NS, TCS.NS")
    ppr.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    ppr.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    ppr.add_argument("--interval", default="1d", help="Data interval (default: 1d)")
    ppr.add_argument("--cache", default=None, help="Optional CSV cache path")
    ppr.add_argument("--refresh", action="store_true", help="Re-download data even if cache exists")
    ppr.add_argument("--outdir", default="outputs/paper", help="Output directory")

    ppr.add_argument("--label-days", type=int, default=1, help="Label horizon in trading days (default: 1)")
    ppr.add_argument("--label-threshold", type=float, default=0.0, help="Label threshold for forward return")
    ppr.add_argument("--prob-threshold", type=float, default=0.55, help="Prob threshold to go long")
    ppr.add_argument("--fee-bps", type=float, default=10.0, help="Transaction fee per position change (bps)")
    ppr.add_argument("--initial-cash", type=float, default=100000.0, help="Starting cash for simulation")

    ppr.add_argument("--random-state", type=int, default=42, help="Random seed")
    ppr.add_argument("--train-mode", choices=["walkforward"], default="walkforward", help="Training mode")
    ppr.add_argument("--min-train-size", type=int, default=252, help="Min rows before walk-forward starts")
    ppr.add_argument("--retrain-every", type=int, default=20, help="Retrain frequency (rows) for walk-forward")
    ppr.set_defaults(func=cmd_paper)

    viz = sub.add_parser("visualize", help="Generate visualization report from existing backtest results.")
    viz.add_argument("--outdir", required=True, help="Output directory containing backtest results")
    viz.add_argument("--ticker", default="Strategy", help="Ticker/strategy name for report title")
    viz.set_defaults(func=cmd_visualize)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

