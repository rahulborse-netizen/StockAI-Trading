"""
Trade Journal
Logs executed trades and tracks performance against trade plans
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExecutedTrade:
    """Record of an executed trade"""
    # Trade identification (non-default fields first)
    trade_id: str
    plan_id: Optional[str]  # Link to original trade plan
    order_id: Optional[str]  # Upstox order ID
    
    # Trade details (non-default fields)
    symbol: str
    ticker: str
    transaction_type: str  # BUY or SELL
    quantity: int
    entry_price: float
    entry_timestamp: str  # Moved before default fields
    
    # Default fields (must come after non-default)
    exit_price: Optional[float] = None  # Set when position is closed
    exit_timestamp: Optional[str] = None
    
    # Performance
    planned_entry: Optional[float] = None
    planned_stop_loss: Optional[float] = None
    planned_target_1: Optional[float] = None
    planned_target_2: Optional[float] = None
    
    # Actual results
    actual_pnl: Optional[float] = None
    actual_pnl_pct: Optional[float] = None
    hit_stop_loss: bool = False
    hit_target_1: bool = False
    hit_target_2: bool = False
    
    # Status
    status: str = "open"  # open, closed, stopped_out
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ExecutedTrade':
        """Create from dictionary"""
        return cls(**data)


class TradeJournal:
    """Manages trade journal storage and retrieval"""
    
    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path('data/trade_journal.json')
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.trades: Dict[str, ExecutedTrade] = {}
        self.load_journal()
    
    def load_journal(self):
        """Load trade journal from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self.trades = {
                        trade_id: ExecutedTrade.from_dict(trade_data)
                        for trade_id, trade_data in data.items()
                    }
                logger.info(f"Loaded {len(self.trades)} trades from journal")
        except Exception as e:
            logger.error(f"Error loading trade journal: {e}")
            self.trades = {}
    
    def save_journal(self):
        """Save trade journal to storage"""
        try:
            data = {
                trade_id: trade.to_dict()
                for trade_id, trade in self.trades.items()
            }
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.trades)} trades to journal")
        except Exception as e:
            logger.error(f"Error saving trade journal: {e}")
    
    def log_trade(
        self,
        plan_id: Optional[str],
        order_id: Optional[str],
        symbol: str,
        ticker: str,
        transaction_type: str,
        quantity: int,
        entry_price: float,
        planned_entry: Optional[float] = None,
        planned_stop_loss: Optional[float] = None,
        planned_target_1: Optional[float] = None,
        planned_target_2: Optional[float] = None
    ) -> ExecutedTrade:
        """Log a new executed trade"""
        trade_id = f"{symbol}_{transaction_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        trade = ExecutedTrade(
            trade_id=trade_id,
            plan_id=plan_id,
            order_id=order_id,
            symbol=symbol,
            ticker=ticker,
            transaction_type=transaction_type,
            quantity=quantity,
            entry_price=entry_price,
            entry_timestamp=datetime.now().isoformat(),
            planned_entry=planned_entry,
            planned_stop_loss=planned_stop_loss,
            planned_target_1=planned_target_1,
            planned_target_2=planned_target_2
        )
        
        self.trades[trade_id] = trade
        self.save_journal()
        
        logger.info(f"Logged trade: {trade_id} - {symbol} {transaction_type} {quantity} @ {entry_price}")
        
        return trade
    
    def update_trade_exit(
        self,
        trade_id: str,
        exit_price: float,
        actual_pnl: Optional[float] = None
    ):
        """Update trade with exit information"""
        trade = self.trades.get(trade_id)
        if not trade:
            logger.warning(f"Trade {trade_id} not found in journal")
            return
        
        trade.exit_price = exit_price
        trade.exit_timestamp = datetime.now().isoformat()
        trade.status = "closed"
        
        if actual_pnl is not None:
            trade.actual_pnl = actual_pnl
            trade.actual_pnl_pct = (actual_pnl / (trade.entry_price * trade.quantity)) * 100
        
        # Check if targets were hit
        if trade.planned_target_1:
            if trade.transaction_type == "BUY" and exit_price >= trade.planned_target_1:
                trade.hit_target_1 = True
            elif trade.transaction_type == "SELL" and exit_price <= trade.planned_target_1:
                trade.hit_target_1 = True
        
        if trade.planned_target_2:
            if trade.transaction_type == "BUY" and exit_price >= trade.planned_target_2:
                trade.hit_target_2 = True
            elif trade.transaction_type == "SELL" and exit_price <= trade.planned_target_2:
                trade.hit_target_2 = True
        
        # Check if stop loss was hit
        if trade.planned_stop_loss:
            if trade.transaction_type == "BUY" and exit_price <= trade.planned_stop_loss:
                trade.hit_stop_loss = True
                trade.status = "stopped_out"
            elif trade.transaction_type == "SELL" and exit_price >= trade.planned_stop_loss:
                trade.hit_stop_loss = True
                trade.status = "stopped_out"
        
        self.save_journal()
        logger.info(f"Updated trade exit: {trade_id} @ {exit_price}")
    
    def get_trade(self, trade_id: str) -> Optional[ExecutedTrade]:
        """Get a trade by ID"""
        return self.trades.get(trade_id)
    
    def get_trades_by_plan(self, plan_id: str) -> List[ExecutedTrade]:
        """Get all trades for a specific plan"""
        return [trade for trade in self.trades.values() if trade.plan_id == plan_id]
    
    def get_all_trades(
        self,
        status: Optional[str] = None,
        symbol: Optional[str] = None
    ) -> List[ExecutedTrade]:
        """Get all trades with optional filters"""
        trades = list(self.trades.values())
        
        if status:
            trades = [t for t in trades if t.status == status]
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        # Sort by entry timestamp (newest first)
        trades.sort(key=lambda t: t.entry_timestamp, reverse=True)
        return trades
    
    def get_performance_stats(self, plan_id: Optional[str] = None) -> Dict:
        """Calculate performance statistics"""
        trades = self.get_trades_by_plan(plan_id) if plan_id else self.get_all_trades()
        
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        closed_trades = [t for t in trades if t.status == "closed" and t.actual_pnl is not None]
        
        if not closed_trades:
            return {
                'total_trades': len(trades),
                'open_trades': len([t for t in trades if t.status == "open"]),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0
            }
        
        winning_trades = [t for t in closed_trades if t.actual_pnl > 0]
        losing_trades = [t for t in closed_trades if t.actual_pnl < 0]
        
        total_pnl = sum(t.actual_pnl for t in closed_trades)
        avg_win = sum(t.actual_pnl for t in winning_trades) / len(winning_trades) if winning_trades else 0.0
        avg_loss = abs(sum(t.actual_pnl for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0
        
        profit_factor = (sum(t.actual_pnl for t in winning_trades) / abs(sum(t.actual_pnl for t in losing_trades))) if losing_trades else float('inf')
        
        return {
            'total_trades': len(closed_trades),
            'open_trades': len([t for t in trades if t.status == "open"]),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(closed_trades) if closed_trades else 0.0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'target_1_hit_rate': len([t for t in closed_trades if t.hit_target_1]) / len(closed_trades) if closed_trades else 0.0,
            'stop_loss_hit_rate': len([t for t in closed_trades if t.hit_stop_loss]) / len(closed_trades) if closed_trades else 0.0
        }


# Global instance
_journal = None


def get_trade_journal() -> TradeJournal:
    """Get global trade journal instance"""
    global _journal
    if _journal is None:
        _journal = TradeJournal()
    return _journal
