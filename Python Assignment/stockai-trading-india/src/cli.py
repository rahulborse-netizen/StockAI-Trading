from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src.research.backtest import backtest_long_cash_from_prob
from src.research.data import download_yahoo_ohlcv
from src.research.features import add_label_next_day_up, clean_ml_frame, make_features
from src.research.ml import save_model, train_baseline_classifier


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
    labeled = add_label_next_day_up(feat, threshold=args.label_threshold)
    ml_df = clean_ml_frame(labeled, feature_cols=DEFAULT_FEATURE_COLS, label_col="label_up")

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

    stats_path = outdir / "stats.json"
    stats_path.write_text(json.dumps(bt.stats, indent=2))

    print("Research run complete")
    print(f"- Data cache: {cache}")
    print(f"- Model: {model_path}")
    print(f"- Predictions: {pred_path}")
    print(f"- Equity curve: {equity_path}")
    print(f"- Stats: {stats_path}")
    print(json.dumps(bt.stats, indent=2))

    return 0


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
    r.add_argument("--label-threshold", type=float, default=0.0, help="Label threshold for next-day return")
    r.add_argument("--prob-threshold", type=float, default=0.55, help="Prob threshold to go long")
    r.add_argument("--fee-bps", type=float, default=10.0, help="Transaction fee per position change (bps)")
    r.set_defaults(func=cmd_research)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

