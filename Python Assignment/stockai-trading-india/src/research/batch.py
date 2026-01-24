from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.research.backtest import backtest_long_cash_from_prob
from src.research.data import download_yahoo_ohlcv
from src.research.features import add_label_forward_return_up, clean_ml_frame, make_features
from src.research.ml import train_baseline_classifier


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
            rows.append(row)
        except Exception as e:  # noqa: BLE001
            rows.append({"ticker": t, "error": str(e)})

    summary = pd.DataFrame(rows)
    summary_path = outdir / "summary.csv"
    summary.to_csv(summary_path, index=False)

    return BatchRunResult(summary=summary, outdir=outdir)

