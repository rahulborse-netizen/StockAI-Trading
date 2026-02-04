"""
Position Sizing Calculator
Risk-based position sizing calculations
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_risk_based_size(
    entry: float,
    stop_loss: float,
    risk_amount: float,
    lot_size: int = 1
) -> int:
    """
    Calculate position size based on risk amount and stop loss distance
    
    Formula: quantity = risk_amount / abs(entry - stop_loss)
    
    Args:
        entry: Entry price
        stop_loss: Stop loss price
        risk_amount: Maximum amount to risk on this trade
        lot_size: Minimum lot size (default: 1)
    
    Returns:
        Position size (quantity) rounded to nearest lot size
    """
    if entry <= 0 or risk_amount <= 0:
        logger.warning("Invalid entry price or risk amount for position sizing")
        return 0
    
    # Calculate price risk per share
    price_risk = abs(entry - stop_loss)
    if price_risk <= 0:
        logger.warning("Stop loss is at or beyond entry price")
        return 0
    
    # Calculate raw quantity
    raw_quantity = risk_amount / price_risk
    
    # Round to nearest lot size
    if lot_size > 1:
        quantity = int((raw_quantity // lot_size) * lot_size)
    else:
        quantity = int(raw_quantity)
    
    # Ensure minimum of 1 share if quantity > 0
    if quantity == 0 and raw_quantity > 0:
        quantity = 1
    
    logger.info(f"Position sizing: entry={entry}, stop={stop_loss}, risk={risk_amount}, quantity={quantity}")
    
    return quantity


def calculate_kelly_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    account_balance: float,
    kelly_fraction: float = 0.25
) -> float:
    """
    Calculate position size using Kelly Criterion (conservative fraction)
    
    Kelly % = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    Args:
        win_rate: Historical win rate (0-1)
        avg_win: Average winning trade amount
        avg_loss: Average losing trade amount (positive number)
        account_balance: Current account balance
        kelly_fraction: Fraction of Kelly to use (default: 0.25 for conservative)
    
    Returns:
        Position size as fraction of account (0-1)
    """
    if avg_win <= 0 or avg_loss <= 0:
        logger.warning("Invalid avg_win or avg_loss for Kelly sizing")
        return 0.0
    
    # Calculate Kelly percentage
    kelly_pct = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
    
    # Apply conservative fraction
    conservative_kelly = kelly_pct * kelly_fraction
    
    # Cap at reasonable maximum (e.g., 10% of account)
    max_position_pct = 0.10
    position_pct = min(conservative_kelly, max_position_pct)
    
    # Ensure non-negative
    position_pct = max(0.0, position_pct)
    
    logger.info(f"Kelly sizing: win_rate={win_rate}, kelly={kelly_pct:.4f}, conservative={position_pct:.4f}")
    
    return position_pct


def calculate_volatility_based_size(
    entry: float,
    volatility: float,
    risk_pct: float,
    account_balance: float
) -> int:
    """
    Calculate position size based on historical volatility
    
    Args:
        entry: Entry price
        volatility: Historical volatility (annualized, as decimal)
        risk_pct: Risk percentage of account (e.g., 0.02 for 2%)
        account_balance: Account balance
    
    Returns:
        Position size (quantity)
    """
    if entry <= 0 or volatility <= 0 or risk_pct <= 0:
        logger.warning("Invalid parameters for volatility-based sizing")
        return 0
    
    # Calculate risk amount
    risk_amount = account_balance * risk_pct
    
    # Estimate stop loss distance based on volatility
    # Use 2 standard deviations for stop loss
    daily_volatility = volatility / (252 ** 0.5)  # Convert annual to daily
    stop_distance = entry * daily_volatility * 2
    
    # Calculate quantity
    quantity = int(risk_amount / stop_distance)
    
    logger.info(f"Volatility sizing: entry={entry}, vol={volatility}, risk_pct={risk_pct}, quantity={quantity}")
    
    return max(1, quantity)  # Minimum 1 share
