from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class ExampleStrategy:
    """
    A simple example strategy used by unit tests and as a template.

    Behavior:
    - If no data is provided -> "hold"
    - If short SMA crosses above long SMA -> "buy"
    - If short SMA crosses below long SMA -> "sell"
    """

    short_window: int = 10
    long_window: int = 30
    _params: Dict[str, Any] = field(default_factory=dict)

    def set_parameters(self, params: Dict[str, Any]) -> None:
        self._params.update(params)
        if "short_window" in params:
            self.short_window = int(params["short_window"])
        if "long_window" in params:
            self.long_window = int(params["long_window"])

    def get_parameters(self) -> Dict[str, Any]:
        return {"short_window": self.short_window, "long_window": self.long_window, **self._params}

    def execute(self, data: Optional[pd.DataFrame] = None) -> str:
        if data is None or data.empty:
            return "hold"

        if "close" not in data.columns:
            return "hold"

        close = data["close"].astype(float)
        if close.shape[0] < max(self.short_window, self.long_window) + 2:
            return "hold"

        sma_s = close.rolling(self.short_window).mean()
        sma_l = close.rolling(self.long_window).mean()

        prev = sma_s.iloc[-2] - sma_l.iloc[-2]
        curr = sma_s.iloc[-1] - sma_l.iloc[-1]

        if pd.isna(prev) or pd.isna(curr):
            return "hold"
        if prev <= 0 and curr > 0:
            return "buy"
        if prev >= 0 and curr < 0:
            return "sell"
        return "hold"