from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ZerodhaAdapter:
    """
    Zerodha adapter.

    Notes:
    - Real Zerodha usage requires an `access_token` (generated via login flow).
    - For local development / unit tests (no credentials), you can set `dry_run=True`
      and methods will return deterministic mock responses.
    """

    api_key: str
    api_secret: Optional[str] = None  # kept for compatibility with older configs/tests
    access_token: Optional[str] = None
    dry_run: bool = True

    def __post_init__(self) -> None:
        self._kite = None
        if not self.dry_run and self.access_token:
            from kiteconnect import KiteConnect

            kite = KiteConnect(api_key=self.api_key)
            kite.set_access_token(self.access_token)
            self._kite = kite

    def place_order(self, symbol: str, quantity: int, order_type: str = "MARKET", transaction_type: str = "BUY") -> Dict[str, Any]:
        if self.dry_run or self._kite is None:
            return {"status": "success", "order_id": "DRYRUN-ORDER-1", "symbol": symbol, "quantity": quantity, "type": transaction_type}

        order_id = self._kite.place_order(
            variety=self._kite.VARIETY_REGULAR,
            exchange=self._kite.EXCHANGE_NSE,
            tradingsymbol=symbol,
            quantity=quantity,
            transaction_type=transaction_type,
            order_type=order_type,
            product=self._kite.PRODUCT_MIS,
        )
        return {"status": "success", "order_id": order_id}

    def get_balance(self) -> float:
        if self.dry_run or self._kite is None:
            return 100000.0
        return float(self._kite.margins()["equity"]["available"]["cash"])

    def get_positions(self) -> List[Dict[str, Any]]:
        if self.dry_run or self._kite is None:
            return []
        return self._kite.positions()
