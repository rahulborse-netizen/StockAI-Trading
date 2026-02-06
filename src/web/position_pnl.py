"""
Real-time Position P&L Calculator
Phase 2.3: Calculate and update position P&L in real-time
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PositionPnLCalculator:
    """Calculate position-level and portfolio-level P&L"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_position_pnl(self, position: Dict, current_price: float) -> Dict:
        """
        Calculate P&L for a single position
        
        Args:
            position: Position dict with quantity, avg_price, etc.
            current_price: Current market price
        
        Returns:
            Dict with P&L details
        """
        try:
            quantity = float(position.get('quantity', 0))
            avg_price = float(position.get('average_price', 0) or position.get('avg_price', 0))
            
            if quantity == 0 or avg_price == 0:
                return {
                    'unrealized_pnl': 0,
                    'unrealized_pnl_pct': 0,
                    'current_value': 0,
                    'invested_value': 0
                }
            
            invested_value = quantity * avg_price
            current_value = quantity * current_price
            unrealized_pnl = current_value - invested_value
            unrealized_pnl_pct = (unrealized_pnl / invested_value * 100) if invested_value > 0 else 0
            
            return {
                'unrealized_pnl': round(unrealized_pnl, 2),
                'unrealized_pnl_pct': round(unrealized_pnl_pct, 2),
                'current_value': round(current_value, 2),
                'invested_value': round(invested_value, 2),
                'current_price': current_price,
                'quantity': quantity,
                'avg_price': avg_price
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position P&L: {e}")
            return {
                'error': str(e),
                'unrealized_pnl': 0,
                'unrealized_pnl_pct': 0
            }
    
    def calculate_portfolio_pnl(self, positions: List[Dict], price_data: Dict[str, float]) -> Dict:
        """
        Calculate aggregate P&L across all positions
        
        Args:
            positions: List of position dicts
            price_data: Dict of instrument_key/ticker -> current_price
        
        Returns:
            Dict with portfolio-level P&L
        """
        try:
            total_invested = 0
            total_current_value = 0
            total_unrealized_pnl = 0
            position_count = len(positions)
            winning_positions = 0
            losing_positions = 0
            
            for position in positions:
                # Get current price
                ticker = position.get('ticker') or position.get('symbol')
                instrument_key = position.get('instrument_key')
                
                current_price = None
                if instrument_key and instrument_key in price_data:
                    current_price = price_data[instrument_key]
                elif ticker and ticker in price_data:
                    current_price = price_data[ticker]
                
                if not current_price:
                    # Use last price from position if available
                    current_price = float(position.get('last_price', 0) or position.get('current_price', 0))
                
                if current_price > 0:
                    pnl = self.calculate_position_pnl(position, current_price)
                    
                    total_invested += pnl.get('invested_value', 0)
                    total_current_value += pnl.get('current_value', 0)
                    total_unrealized_pnl += pnl.get('unrealized_pnl', 0)
                    
                    if pnl.get('unrealized_pnl', 0) > 0:
                        winning_positions += 1
                    elif pnl.get('unrealized_pnl', 0) < 0:
                        losing_positions += 1
            
            total_unrealized_pnl_pct = (total_unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
            win_rate = (winning_positions / position_count * 100) if position_count > 0 else 0
            
            return {
                'total_invested': round(total_invested, 2),
                'total_current_value': round(total_current_value, 2),
                'total_unrealized_pnl': round(total_unrealized_pnl, 2),
                'total_unrealized_pnl_pct': round(total_unrealized_pnl_pct, 2),
                'position_count': position_count,
                'winning_positions': winning_positions,
                'losing_positions': losing_positions,
                'win_rate': round(win_rate, 2),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio P&L: {e}")
            return {
                'error': str(e),
                'total_unrealized_pnl': 0,
                'position_count': 0
            }
    
    def get_risk_metrics(self, positions: List[Dict], price_data: Dict[str, float]) -> Dict:
        """
        Calculate portfolio risk metrics
        
        Args:
            positions: List of position dicts
            price_data: Dict of ticker/instrument_key -> current_price
        
        Returns:
            Dict with risk metrics
        """
        try:
            if not positions:
                return {
                    'concentration_risk': 0,
                    'largest_position_pct': 0,
                    'position_diversity': 0
                }
            
            # Calculate position values
            position_values = []
            total_value = 0
            
            for position in positions:
                ticker = position.get('ticker') or position.get('symbol')
                instrument_key = position.get('instrument_key')
                
                current_price = None
                if instrument_key and instrument_key in price_data:
                    current_price = price_data[instrument_key]
                elif ticker and ticker in price_data:
                    current_price = price_data[ticker]
                
                if not current_price:
                    current_price = float(position.get('last_price', 0) or position.get('current_price', 0))
                
                if current_price > 0:
                    quantity = float(position.get('quantity', 0))
                    value = quantity * current_price
                    position_values.append(value)
                    total_value += value
            
            if total_value == 0:
                return {
                    'concentration_risk': 0,
                    'largest_position_pct': 0,
                    'position_diversity': 0
                }
            
            # Calculate metrics
            largest_position = max(position_values) if position_values else 0
            largest_position_pct = (largest_position / total_value * 100) if total_value > 0 else 0
            
            # Concentration risk: HHI (Herfindahl-Hirschman Index)
            hhi = sum((value / total_value) ** 2 for value in position_values) if total_value > 0 else 0
            concentration_risk = hhi * 100  # Convert to percentage
            
            # Position diversity (inverse of concentration)
            position_diversity = (1 - hhi) * 100 if hhi < 1 else 0
            
            return {
                'concentration_risk': round(concentration_risk, 2),
                'largest_position_pct': round(largest_position_pct, 2),
                'position_diversity': round(position_diversity, 2),
                'total_portfolio_value': round(total_value, 2),
                'position_count': len(positions)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating risk metrics: {e}")
            return {
                'error': str(e),
                'concentration_risk': 0
            }


# Global singleton
_pnl_calculator = None


def get_pnl_calculator() -> PositionPnLCalculator:
    """Get global P&L calculator instance"""
    global _pnl_calculator
    if _pnl_calculator is None:
        _pnl_calculator = PositionPnLCalculator()
    return _pnl_calculator
