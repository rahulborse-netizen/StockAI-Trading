from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Trade:
    date: pd.Timestamp
    side: str  # BUY / SELL
    price: float
    qty: int
    cash_after: float
    position_after: int
    equity_after: float


def paper_trade_long_cash(
    ohlcv: pd.DataFrame,
    prob_up: pd.Series,
    prob_threshold: float = 0.55,
    fee_bps: float = 10.0,
    initial_cash: float = 100000.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Paper-trade a simple long/cash strategy with an explicit trade blotter.

    Rules (daily):
    - Desired position for day t is based on prob(t-1) (avoid look-ahead)
    - Execute at close of day t (simplified)
    - Position is either 0 or 1 share (qty=1) for demo purposes
    """
    close = ohlcv["close"].astype(float).copy()
    p = prob_up.reindex(close.index)
    first_valid = p.first_valid_index()
    if first_valid is None:
        raise ValueError("prob_up has no valid values; cannot paper trade.")

    close = close.loc[first_valid:]
    p = p.loc[first_valid:].ffill()
    desired = (p >= prob_threshold).astype(int).shift(1).fillna(0).astype(int)

    cash = float(initial_cash)
    pos = 0
    trades: list[Trade] = []

    equity_series = []
    for dt, price in close.items():
        want = int(desired.loc[dt])
        fee = (fee_bps / 10000.0) * 1.0  # bps on notional ~ price; simplified below

        if want != pos:
            if want == 1 and pos == 0:
                # buy 1 share
                cost = price * (1.0 + fee)
                if cash >= cost:
                    cash -= cost
                    pos = 1
                    trades.append(Trade(dt, "BUY", float(price), 1, cash, pos, cash + pos * price))
            elif want == 0 and pos == 1:
                # sell 1 share
                proceeds = price * (1.0 - fee)
                cash += proceeds
                pos = 0
                trades.append(Trade(dt, "SELL", float(price), 1, cash, pos, cash + pos * price))

        equity_series.append({"date": dt, "cash": cash, "position": pos, "price": float(price), "equity": cash + pos * price})

    equity_df = pd.DataFrame(equity_series).set_index("date")
    trades_df = pd.DataFrame([t.__dict__ for t in trades])
    if not trades_df.empty:
        trades_df["date"] = pd.to_datetime(trades_df["date"])
        trades_df = trades_df.set_index("date").sort_index()
    return equity_df, trades_df

