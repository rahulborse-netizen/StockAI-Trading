"""
Holdings History Database
Phase 2.4: SQLite database for portfolio history tracking
"""
import sqlite3
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import threading

logger = logging.getLogger(__name__)


class HoldingsDatabase:
    """SQLite database for tracking portfolio history"""
    
    def __init__(self, db_path: str = 'data/holdings_history.db'):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_lock = threading.Lock()
        self._initialize_db()
        logger.info(f"✅ Holdings database initialized: {self.db_path}")
    
    def _initialize_db(self):
        """Create database tables if they don't exist"""
        with self.db_lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Portfolio snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_value REAL NOT NULL,
                    cash_balance REAL,
                    position_value REAL,
                    daily_pnl REAL,
                    cumulative_pnl REAL,
                    metadata TEXT
                )
            ''')
            
            # Holding snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS holding_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL,
                    symbol TEXT NOT NULL,
                    instrument_key TEXT,
                    quantity INTEGER NOT NULL,
                    average_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    pnl REAL,
                    pnl_pct REAL,
                    FOREIGN KEY (snapshot_id) REFERENCES portfolio_snapshots (id)
                )
            ''')
            
            # Create indices for better query performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp 
                ON portfolio_snapshots(timestamp)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_holdings_snapshot 
                ON holding_snapshots(snapshot_id)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_holdings_symbol 
                ON holding_snapshots(symbol)
            ''')
            
            conn.commit()
            conn.close()
    
    def record_portfolio_snapshot(self, holdings: List[Dict], cash_balance: float = 0, 
                                  metadata: Optional[Dict] = None) -> int:
        """
        Record a portfolio snapshot
        
        Args:
            holdings: List of holding dicts with symbol, quantity, avg_price, current_price
            cash_balance: Available cash balance
            metadata: Optional metadata dict
        
        Returns:
            Snapshot ID
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Calculate portfolio metrics
                position_value = sum(
                    h.get('quantity', 0) * h.get('current_price', 0) 
                    for h in holdings
                )
                total_value = position_value + cash_balance
                
                # Calculate P&L
                invested_value = sum(
                    h.get('quantity', 0) * h.get('average_price', 0) 
                    for h in holdings
                )
                cumulative_pnl = position_value - invested_value
                
                # Get previous snapshot for daily P&L
                cursor.execute('''
                    SELECT total_value FROM portfolio_snapshots 
                    ORDER BY id DESC LIMIT 1
                ''')
                previous = cursor.fetchone()
                daily_pnl = total_value - previous[0] if previous else 0
                
                # Insert portfolio snapshot
                timestamp = datetime.now().isoformat()
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute('''
                    INSERT INTO portfolio_snapshots 
                    (timestamp, total_value, cash_balance, position_value, 
                     daily_pnl, cumulative_pnl, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (timestamp, total_value, cash_balance, position_value,
                      daily_pnl, cumulative_pnl, metadata_json))
                
                snapshot_id = cursor.lastrowid
                
                # Insert holding snapshots
                for holding in holdings:
                    symbol = holding.get('symbol') or holding.get('ticker')
                    instrument_key = holding.get('instrument_key')
                    quantity = holding.get('quantity', 0)
                    avg_price = holding.get('average_price', 0) or holding.get('avg_price', 0)
                    current_price = holding.get('current_price', 0)
                    
                    if quantity > 0 and avg_price > 0:
                        pnl = (current_price - avg_price) * quantity
                        pnl_pct = ((current_price - avg_price) / avg_price * 100) if avg_price > 0 else 0
                        
                        cursor.execute('''
                            INSERT INTO holding_snapshots 
                            (snapshot_id, symbol, instrument_key, quantity, 
                             average_price, current_price, pnl, pnl_pct)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (snapshot_id, symbol, instrument_key, quantity,
                              avg_price, current_price, pnl, pnl_pct))
                
                conn.commit()
                conn.close()
                
                logger.info(f"📊 Recorded portfolio snapshot #{snapshot_id}: {len(holdings)} holdings, ₹{total_value:.2f}")
                return snapshot_id
                
        except Exception as e:
            logger.error(f"Error recording portfolio snapshot: {e}")
            return -1
    
    def get_portfolio_history(self, days: int = 30) -> List[Dict]:
        """
        Get portfolio history for the last N days
        
        Args:
            days: Number of days of history to retrieve
        
        Returns:
            List of portfolio snapshot dicts
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor.execute('''
                    SELECT id, timestamp, total_value, cash_balance, position_value,
                           daily_pnl, cumulative_pnl, metadata
                    FROM portfolio_snapshots
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC
                ''', (cutoff_date,))
                
                snapshots = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[7]) if row[7] else {}
                    snapshots.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'total_value': row[2],
                        'cash_balance': row[3],
                        'position_value': row[4],
                        'daily_pnl': row[5],
                        'cumulative_pnl': row[6],
                        'metadata': metadata
                    })
                
                conn.close()
                return snapshots
                
        except Exception as e:
            logger.error(f"Error getting portfolio history: {e}")
            return []
    
    def get_holding_history(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        Get history for a specific holding
        
        Args:
            symbol: Stock symbol/ticker
            days: Number of days of history
        
        Returns:
            List of holding snapshot dicts
        """
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor.execute('''
                    SELECT h.id, p.timestamp, h.symbol, h.quantity, 
                           h.average_price, h.current_price, h.pnl, h.pnl_pct
                    FROM holding_snapshots h
                    JOIN portfolio_snapshots p ON h.snapshot_id = p.id
                    WHERE h.symbol = ? AND p.timestamp >= ?
                    ORDER BY p.timestamp ASC
                ''', (symbol, cutoff_date))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'id': row[0],
                        'timestamp': row[1],
                        'symbol': row[2],
                        'quantity': row[3],
                        'average_price': row[4],
                        'current_price': row[5],
                        'pnl': row[6],
                        'pnl_pct': row[7]
                    })
                
                conn.close()
                return history
                
        except Exception as e:
            logger.error(f"Error getting holding history for {symbol}: {e}")
            return []
    
    def calculate_time_weighted_return(self, days: int = 30) -> float:
        """
        Calculate time-weighted return (TWR) for the portfolio
        
        Args:
            days: Number of days to calculate TWR for
        
        Returns:
            TWR as percentage
        """
        try:
            history = self.get_portfolio_history(days)
            
            if len(history) < 2:
                return 0.0
            
            # Simple TWR calculation: (final_value / initial_value - 1) * 100
            initial_value = history[0]['total_value']
            final_value = history[-1]['total_value']
            
            if initial_value == 0:
                return 0.0
            
            twr = ((final_value / initial_value) - 1) * 100
            return round(twr, 2)
            
        except Exception as e:
            logger.error(f"Error calculating TWR: {e}")
            return 0.0
    
    def get_latest_snapshot(self) -> Optional[Dict]:
        """Get the most recent portfolio snapshot"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, timestamp, total_value, cash_balance, position_value,
                           daily_pnl, cumulative_pnl, metadata
                    FROM portfolio_snapshots
                    ORDER BY id DESC LIMIT 1
                ''')
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    metadata = json.loads(row[7]) if row[7] else {}
                    return {
                        'id': row[0],
                        'timestamp': row[1],
                        'total_value': row[2],
                        'cash_balance': row[3],
                        'position_value': row[4],
                        'daily_pnl': row[5],
                        'cumulative_pnl': row[6],
                        'metadata': metadata
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error getting latest snapshot: {e}")
            return None
    
    def clear_old_snapshots(self, days: int = 90):
        """Delete snapshots older than specified days"""
        try:
            with self.db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # Delete old holding snapshots first (foreign key constraint)
                cursor.execute('''
                    DELETE FROM holding_snapshots
                    WHERE snapshot_id IN (
                        SELECT id FROM portfolio_snapshots
                        WHERE timestamp < ?
                    )
                ''', (cutoff_date,))
                
                # Delete old portfolio snapshots
                cursor.execute('''
                    DELETE FROM portfolio_snapshots
                    WHERE timestamp < ?
                ''', (cutoff_date,))
                
                deleted = cursor.rowcount
                conn.commit()
                conn.close()
                
                logger.info(f"🗑️ Deleted {deleted} old snapshots (older than {days} days)")
                return deleted
                
        except Exception as e:
            logger.error(f"Error clearing old snapshots: {e}")
            return 0


# Global singleton
_holdings_db = None
_db_lock = threading.Lock()


def get_holdings_db() -> HoldingsDatabase:
    """Get global holdings database instance"""
    global _holdings_db
    with _db_lock:
        if _holdings_db is None:
            _holdings_db = HoldingsDatabase()
        return _holdings_db
