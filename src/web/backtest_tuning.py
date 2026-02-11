"""
Backtest-driven tuning: threshold sweep and strategy ranking.
Used to suggest confidence_threshold and strategy weights from historical backtests.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

THRESHOLD_CANDIDATES = [0.52, 0.55, 0.60, 0.65, 0.70]
BEST_THRESHOLD_CAP = 0.75  # Never suggest threshold above this without user approval


def run_threshold_sweep(
    ticker: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Run backtest for several prob thresholds; return results and best threshold (by Sharpe).
    Does not modify config; caller may apply best_threshold with cap.
    """
    try:
        from src.research.data import download_yahoo_ohlcv
        from src.research.features import make_features, add_label_forward_return_up, clean_ml_frame
        from src.research.ml import walk_forward_predict_proba
        from src.research.backtest import backtest_long_cash_from_prob
        import pandas as pd

        ohlcv = download_yahoo_ohlcv(ticker=ticker, start=start_date, end=end_date, interval="1d")
        if not ohlcv or not getattr(ohlcv, "df", None) or len(ohlcv.df) < 260:
            return {"error": "Insufficient data (need ~260+ days)"}

        df = ohlcv.df.copy()
        df = make_features(df)
        df = add_label_forward_return_up(df, days=1, threshold=0.0)
        feature_cols = [c for c in ["ret_1", "ret_5", "vol_10", "sma_10", "sma_50", "ema_20", "rsi_14", "macd", "macd_signal", "macd_hist"] if c in df.columns]
        if len(feature_cols) < 5:
            return {"error": "Not enough feature columns for backtest"}

        labeled = clean_ml_frame(df, feature_cols=feature_cols, label_col="label_up")
        if len(labeled) < 260:
            return {"error": "Insufficient rows after cleaning"}

        prob_up = walk_forward_predict_proba(labeled, feature_cols, label_col="label_up", min_train_size=252, retrain_every=20)
        results = []
        for th in THRESHOLD_CANDIDATES:
            try:
                bt = backtest_long_cash_from_prob(labeled, prob_up, prob_threshold=th, fee_bps=10.0)
                results.append({
                    "threshold": th,
                    "sharpe": round(bt.stats["sharpe"], 4),
                    "total_return": round(bt.stats["total_return"] * 100, 2),
                    "max_drawdown": round(bt.stats["max_drawdown"] * 100, 2),
                })
            except Exception as e:
                logger.debug(f"Backtest failed for threshold {th}: {e}")
                continue

        if not results:
            return {"error": "No backtest results", "ticker": ticker}

        best = max(results, key=lambda x: (x["sharpe"], x["total_return"]))
        best_threshold = min(best["threshold"], BEST_THRESHOLD_CAP)
        return {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "results": results,
            "best_threshold": round(best_threshold, 2),
            "best_sharpe": best["sharpe"],
        }
    except Exception as e:
        logger.exception("Threshold sweep failed")
        return {"error": str(e), "ticker": ticker}


def run_strategy_ranking(
    ticker: str,
    start_date: str,
    end_date: str,
) -> Dict[str, Any]:
    """
    Run backtest for each QUANT strategy; return ranking by Sharpe.
    Does not modify config; caller may use ranking to set active strategy or weights.
    """
    try:
        from src.research.data import download_yahoo_ohlcv
        from src.web.strategies.strategy_manager import get_strategy_manager
        from src.web.strategies.adaptive_features import make_adaptive_features
        import pandas as pd
        import numpy as np

        ohlcv = download_yahoo_ohlcv(ticker=ticker, start=start_date, end=end_date, interval="1d")
        if not ohlcv or not getattr(ohlcv, "df", None) or len(ohlcv.df) < 100:
            return {"error": "Insufficient data"}

        df = ohlcv.df.copy()
        sm = get_strategy_manager()
        strategy_names = sm.get_available_strategies()
        rankings = []

        for name in strategy_names:
            if name not in sm.strategies:
                continue
            strategy = sm.strategies[name]
            try:
                cash = 100000.0
                position = 0
                entry_price = 0.0
                daily_returns = []
                prev_equity = 100000.0
                trade_count = 0

                for i in range(60, len(df)):
                    historical_df = df.iloc[: i + 1].copy()
                    try:
                        enhanced_df, regime_info = make_adaptive_features(historical_df)
                        latest = enhanced_df.iloc[-1]
                        current_price = float(latest.get("close", 0))
                        if current_price <= 0:
                            continue
                        price_std = float(historical_df["close"].tail(20).std()) if len(historical_df) >= 20 else current_price * 0.02
                        data = {
                            "ticker": ticker,
                            "current_price": current_price,
                            "ohlcv_df": enhanced_df,
                            "sma_10": float(latest.get("sma_10", current_price)),
                            "sma_20": float(latest.get("sma_20", current_price)),
                            "sma_50": float(latest.get("sma_50", current_price)),
                            "rsi_14": float(latest.get("rsi_14", 50)),
                            "macd": float(latest.get("macd", 0)),
                            "macd_signal": float(latest.get("macd_signal", 0)),
                            "macd_hist": float(latest.get("macd_hist", 0)),
                            "ret_5": float(latest.get("ret_5", 0)),
                            "ret_20": float(latest.get("ret_20", 0)),
                            "adx": float(latest.get("adx_14", 25)),
                            "price_std": price_std,
                            "bollinger_upper": float(latest.get("bb_upper", current_price * 1.05)),
                            "bollinger_lower": float(latest.get("bb_lower", current_price * 0.95)),
                            "volume": float(latest.get("volume", 0)),
                            "market_data": regime_info,
                            "probability": max(0.0, min(1.0, 0.5 + float(latest.get("ret_1", 0)) * 2)),
                        }
                        result = strategy.execute(data)
                    except Exception as e:
                        logger.debug(f"Strategy {name} execute failed at i={i}: {e}")
                        current_price = float(df["close"].iloc[i])
                        equity = cash + position * current_price
                        if prev_equity > 0:
                            daily_returns.append((equity / prev_equity) - 1.0)
                        prev_equity = equity
                        continue

                    signal = result.signal
                    conf = getattr(result, "confidence", 0.5)

                    if signal in ("BUY", "STRONG_BUY") and position == 0 and conf >= 0.70:
                        position = int((cash * 0.95) / current_price)
                        if position > 0:
                            entry_price = current_price
                            cash -= position * current_price
                    elif signal in ("SELL", "STRONG_SELL") and position > 0 and conf >= 0.70:
                        cash += position * current_price
                        trade_count += 1
                        position = 0
                        entry_price = 0.0

                    equity = cash + position * current_price
                    if prev_equity > 0:
                        daily_returns.append((equity / prev_equity) - 1.0)
                    prev_equity = equity

                if position > 0:
                    cash += position * float(df["close"].iloc[-1])
                    position = 0
                final_equity = cash

                if len(daily_returns) > 1 and np.std(daily_returns) > 0:
                    sharpe = (np.mean(daily_returns) / np.std(daily_returns)) * np.sqrt(252)
                else:
                    sharpe = 0.0
                total_return = (final_equity / 100000.0 - 1.0) * 100
                rankings.append({"strategy": name, "sharpe_ratio": round(sharpe, 4), "total_return_pct": round(total_return, 2), "trades": trade_count})
            except Exception as e:
                logger.warning(f"Backtest failed for strategy {name}: {e}")

        rankings.sort(key=lambda x: (x["sharpe_ratio"], x["total_return_pct"]), reverse=True)
        return {
            "ticker": ticker,
            "start_date": start_date,
            "end_date": end_date,
            "rankings": rankings,
            "best_strategy": rankings[0]["strategy"] if rankings else None,
        }
    except Exception as e:
        logger.exception("Strategy ranking failed")
        return {"error": str(e), "ticker": ticker}


def apply_backtest_results(
    sweep_result: Optional[Dict[str, Any]] = None,
    ranking_result: Optional[Dict[str, Any]] = None,
    apply_threshold: bool = True,
    apply_strategy: bool = False,
) -> Dict[str, Any]:
    """
    Apply backtest results to config (with safety caps).
    - sweep_result: from run_threshold_sweep; if apply_threshold, set confidence_threshold (capped at BEST_THRESHOLD_CAP).
    - ranking_result: from run_strategy_ranking; if apply_strategy, set active quant strategy to best_strategy.
    """
    applied = []
    if sweep_result and apply_threshold and "error" not in sweep_result and "best_threshold" in sweep_result:
        th = min(float(sweep_result["best_threshold"]), BEST_THRESHOLD_CAP)
        from src.web.risk_config import update_risk_config
        update_risk_config({"confidence_threshold": round(th, 2)})
        applied.append(f"confidence_threshold={round(th, 2)}")
    if ranking_result and apply_strategy and "error" not in ranking_result and ranking_result.get("best_strategy"):
        name = ranking_result["best_strategy"]
        from src.web.strategies.strategy_manager import get_strategy_manager
        sm = get_strategy_manager()
        if name in sm.strategies:
            sm.set_active_strategy(name)
            applied.append(f"active_strategy={name}")
    return {"applied": applied, "message": "Applied: " + ", ".join(applied) if applied else "Nothing applied"}
