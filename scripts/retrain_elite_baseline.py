"""
Periodic retrain of ELITE baseline (logistic regression) model.
Run monthly or on schedule; saves model to data/models/ for use by ELITE signal generator.
Uses time-based train/test split and a rolling window of daily data.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_FEATURE_COLS = [
    "ret_1", "ret_5", "vol_10", "sma_10", "sma_50", "ema_20",
    "rsi_14", "macd", "macd_signal", "macd_hist", "vol_chg_1", "vol_sma_20",
]
MODEL_DIR = Path("data/models")
MODEL_PATH = MODEL_DIR / "elite_baseline.joblib"
FEATURES_PATH = MODEL_DIR / "elite_baseline_features.json"


def run_retrain(
    ticker: str = "RELIANCE.NS",
    days_back: int = 504,  # ~2 years
    test_size: float = 0.2,
    random_state: int = 42,
) -> bool:
    """
    Download daily data, build features, train baseline classifier, save model and feature list.
    Returns True if successful.
    """
    from src.research.data import download_yahoo_ohlcv
    from src.research.features import make_features, add_label_forward_return_up, clean_ml_frame
    from src.research.ml import train_baseline_classifier, save_model

    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    logger.info(f"Downloading {ticker} from {start_date} to {end_date}")
    ohlcv = download_yahoo_ohlcv(ticker=ticker, start=start_date, end=end_date, interval="1d")
    if not ohlcv or len(ohlcv.df) < 300:
        logger.error("Insufficient data for retrain")
        return False

    df = make_features(ohlcv.df)
    df = add_label_forward_return_up(df, days=1, threshold=0.0)
    feature_cols = [c for c in DEFAULT_FEATURE_COLS if c in df.columns]
    if len(feature_cols) < 5:
        logger.error("Not enough feature columns")
        return False

    ml_df = clean_ml_frame(df, feature_cols=feature_cols, label_col="label_up")
    if len(ml_df) < 252:
        logger.error("Not enough rows after cleaning")
        return False

    logger.info("Training baseline classifier (time-based split)")
    train_result, pred_df = train_baseline_classifier(
        df=ml_df,
        feature_cols=feature_cols,
        label_col="label_up",
        test_size=test_size,
        random_state=random_state,
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    save_model(train_result.model, str(MODEL_PATH))
    with open(FEATURES_PATH, "w") as f:
        json.dump(feature_cols, f, indent=2)
    logger.info(f"Saved model to {MODEL_PATH} and features to {FEATURES_PATH}")
    return True


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--ticker", default="RELIANCE.NS")
    p.add_argument("--days", type=int, default=504)
    p.add_argument("--test-size", type=float, default=0.2)
    args = p.parse_args()
    ok = run_retrain(ticker=args.ticker, days_back=args.days, test_size=args.test_size)
    sys.exit(0 if ok else 1)
