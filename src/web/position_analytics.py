"""
Position Analytics Module
Phase 2.3: Advanced position analytics and performance metrics
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class PositionAnalytics:
    """Advanced analytics for positions and trading performance"""
    
    def __init__(self):
        self.position_history: Dict[str, List[Dict]] = {}
    
    def get_position_history(self, symbol: str, days: int = 30) -> List[Dict]:
        """
        Get historical data for a position
        
        Args:
            symbol: Stock symbol
            days: Number of days of history
        
        Returns:
            List of historical position snapshots
        """
        try:
            history = self.position_history.get(symbol, [])
            
            # Filter by days
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered = [
                entry for entry in history
                if datetime.fromisoformat(entry.get('timestamp', '')) >= cutoff_date
            ]
            
            return filtered
        except Exception as e:
            logger.error(f"Error getting position history for {symbol}: {e}")
            return []
    
    def calculate_holding_period_return(self, position: Dict) -> Dict:
        """
        Calculate holding period return for a position
        
        Args:
            position: Position dictionary with entry and current data
        
        Returns:
            Dictionary with holding period return metrics
        """
        try:
            entry_timestamp = position.get('entry_timestamp') or position.get('timestamp')
            if not entry_timestamp:
                return {
                    'holding_days': 0,
                    'holding_period_return': 0,
                    'annualized_return': 0,
                    'error': 'No entry timestamp'
                }
            
            entry_date = datetime.fromisoformat(entry_timestamp) if isinstance(entry_timestamp, str) else entry_timestamp
            holding_days = (datetime.now() - entry_date).days
            
            average_price = float(position.get('average_price', 0) or position.get('avg_price', 0))
            current_price = float(position.get('current_price', 0) or position.get('ltp', 0) or position.get('last_price', 0))
            
            if average_price == 0:
                return {
                    'holding_days': holding_days,
                    'holding_period_return': 0,
                    'annualized_return': 0,
                    'error': 'No average price'
                }
            
            holding_period_return = ((current_price - average_price) / average_price) * 100
            
            # Annualized return
            if holding_days > 0:
                annualized_return = ((current_price / average_price) ** (365 / holding_days) - 1) * 100
            else:
                annualized_return = 0
            
            return {
                'holding_days': holding_days,
                'holding_period_return': holding_period_return,
                'annualized_return': annualized_return,
                'entry_price': average_price,
                'current_price': current_price,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating holding period return: {e}")
            return {
                'holding_days': 0,
                'holding_period_return': 0,
                'annualized_return': 0,
                'error': str(e)
            }
    
    def get_win_loss_ratio(self, positions: List[Dict]) -> Dict:
        """
        Calculate win/loss ratio from positions
        
        Args:
            positions: List of position dictionaries
        
        Returns:
            Dictionary with win/loss metrics
        """
        try:
            if not positions:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'loss_rate': 0,
                    'win_loss_ratio': 0
                }
            
            winning_trades = 0
            losing_trades = 0
            total_pnl = 0
            
            for position in positions:
                pnl = float(position.get('pnl', 0) or position.get('total_pnl', 0) or 0)
                total_pnl += pnl
                
                if pnl > 0:
                    winning_trades += 1
                elif pnl < 0:
                    losing_trades += 1
            
            total_trades = len(positions)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            loss_rate = (losing_trades / total_trades * 100) if total_trades > 0 else 0
            win_loss_ratio = (winning_trades / losing_trades) if losing_trades > 0 else (winning_trades if winning_trades > 0 else 0)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'loss_rate': loss_rate,
                'win_loss_ratio': win_loss_ratio,
                'total_pnl': total_pnl,
                'average_pnl': total_pnl / total_trades if total_trades > 0 else 0,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error calculating win/loss ratio: {e}")
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'loss_rate': 0,
                'win_loss_ratio': 0,
                'error': str(e)
            }
    
    def analyze_exit_quality(self, positions: List[Dict]) -> Dict:
        """
        Analyze exit quality - how well positions were exited
        
        Args:
            positions: List of closed position dictionaries
        
        Returns:
            Dictionary with exit quality metrics
        """
        try:
            if not positions:
                return {
                    'total_exits': 0,
                    'target_hit_rate': 0,
                    'stop_loss_hit_rate': 0,
                    'average_exit_price_vs_target': 0,
                    'exit_quality_score': 0
                }
            
            closed_positions = [p for p in positions if p.get('status') == 'CLOSED' or p.get('quantity', 0) == 0]
            
            if not closed_positions:
                return {
                    'total_exits': 0,
                    'target_hit_rate': 0,
                    'stop_loss_hit_rate': 0,
                    'average_exit_price_vs_target': 0,
                    'exit_quality_score': 0
                }
            
            target_hits = 0
            stop_loss_hits = 0
            exit_price_diffs = []
            
            for position in closed_positions:
                entry_price = float(position.get('average_price', 0) or position.get('avg_price', 0))
                exit_price = float(position.get('exit_price', 0) or position.get('current_price', 0))
                target_price = float(position.get('target_1', 0) or position.get('target', 0))
                stop_loss_price = float(position.get('stop_loss', 0) or 0)
                
                if entry_price == 0 or exit_price == 0:
                    continue
                
                # Check if target was hit
                if target_price > 0:
                    if (position.get('transaction_type') == 'BUY' and exit_price >= target_price) or \
                       (position.get('transaction_type') == 'SELL' and exit_price <= target_price):
                        target_hits += 1
                
                # Check if stop loss was hit
                if stop_loss_price > 0:
                    if (position.get('transaction_type') == 'BUY' and exit_price <= stop_loss_price) or \
                       (position.get('transaction_type') == 'SELL' and exit_price >= stop_loss_price):
                        stop_loss_hits += 1
                
                # Calculate exit price vs target
                if target_price > 0:
                    diff_pct = ((exit_price - target_price) / target_price) * 100
                    exit_price_diffs.append(diff_pct)
            
            total_exits = len(closed_positions)
            target_hit_rate = (target_hits / total_exits * 100) if total_exits > 0 else 0
            stop_loss_hit_rate = (stop_loss_hits / total_exits * 100) if total_exits > 0 else 0
            average_exit_price_vs_target = sum(exit_price_diffs) / len(exit_price_diffs) if exit_price_diffs else 0
            
            # Exit quality score (0-100)
            exit_quality_score = (target_hit_rate * 0.7) - (stop_loss_hit_rate * 0.3) + 50
            
            return {
                'total_exits': total_exits,
                'target_hit_rate': target_hit_rate,
                'stop_loss_hit_rate': stop_loss_hit_rate,
                'average_exit_price_vs_target': average_exit_price_vs_target,
                'exit_quality_score': max(0, min(100, exit_quality_score)),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error analyzing exit quality: {e}")
            return {
                'total_exits': 0,
                'target_hit_rate': 0,
                'stop_loss_hit_rate': 0,
                'average_exit_price_vs_target': 0,
                'exit_quality_score': 0,
                'error': str(e)
            }
    
    def record_position_snapshot(self, symbol: str, position_data: Dict) -> None:
        """
        Record a snapshot of position data for historical analysis
        
        Args:
            symbol: Stock symbol
            position_data: Position data dictionary
        """
        try:
            if symbol not in self.position_history:
                self.position_history[symbol] = []
            
            snapshot = {
                **position_data,
                'timestamp': datetime.now().isoformat()
            }
            
            self.position_history[symbol].append(snapshot)
            
            # Keep only last 1000 snapshots per symbol
            if len(self.position_history[symbol]) > 1000:
                self.position_history[symbol] = self.position_history[symbol][-1000:]
                
        except Exception as e:
            logger.error(f"Error recording position snapshot: {e}")


# Global instance
_position_analytics: Optional[PositionAnalytics] = None


def get_position_analytics() -> PositionAnalytics:
    """Get global position analytics instance"""
    global _position_analytics
    if _position_analytics is None:
        _position_analytics = PositionAnalytics()
    return _position_analytics
