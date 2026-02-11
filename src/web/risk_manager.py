"""
Portfolio Risk Management
Checks portfolio-level risk limits and constraints
"""
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RiskCheckResult:
    """Result of a risk check"""
    passed: bool
    message: str
    details: Dict


class PortfolioRiskManager:
    """Manages portfolio-level risk checks"""
    
    def __init__(self, risk_config: Optional[Dict] = None):
        from src.web.risk_config import get_risk_config
        self.risk_config = risk_config or get_risk_config()
    
    def check_portfolio_risk(
        self,
        new_plan_capital: float,
        current_portfolio_value: float,
        existing_positions: List[Dict],
        new_plan_risk: float
    ) -> RiskCheckResult:
        """
        Check if adding a new trade plan would exceed portfolio risk limits
        
        Args:
            new_plan_capital: Capital required for new trade plan
            current_portfolio_value: Current total portfolio value
            existing_positions: List of existing positions
            new_plan_risk: Risk amount for new plan
        
        Returns:
            RiskCheckResult with check status
        """
        errors = []
        warnings = []
        
        # Check maximum position size
        max_position_size = self.risk_config.get('max_position_size', 0.20)
        position_size_pct = new_plan_capital / current_portfolio_value if current_portfolio_value > 0 else 0
        
        if position_size_pct > max_position_size:
            errors.append(
                f"Position size ({position_size_pct*100:.2f}%) exceeds maximum ({max_position_size*100:.2f}%)"
            )
        
        # Check maximum open positions
        max_open_positions = self.risk_config.get('max_open_positions', 10)
        if len(existing_positions) >= max_open_positions:
            errors.append(
                f"Maximum open positions ({max_open_positions}) already reached"
            )
        
        # Check portfolio-wide risk
        total_portfolio_risk = sum(
            pos.get('risk_amount', 0) for pos in existing_positions
        ) + new_plan_risk
        
        max_portfolio_risk = self.risk_config.get('max_portfolio_risk', 0.30)
        portfolio_risk_pct = total_portfolio_risk / current_portfolio_value if current_portfolio_value > 0 else 0
        
        if portfolio_risk_pct > max_portfolio_risk:
            errors.append(
                f"Portfolio risk ({portfolio_risk_pct*100:.2f}%) exceeds maximum ({max_portfolio_risk*100:.2f}%)"
            )
        
        # Check daily risk limit
        max_daily_risk = self.risk_config.get('max_daily_risk', 0.05)
        daily_risk_pct = new_plan_risk / current_portfolio_value if current_portfolio_value > 0 else 0
        
        if daily_risk_pct > max_daily_risk:
            warnings.append(
                f"Daily risk ({daily_risk_pct*100:.2f}%) exceeds recommended limit ({max_daily_risk*100:.2f}%)"
            )
        
        # Check for over-concentration (same symbol)
        symbol_counts = {}
        for pos in existing_positions:
            symbol = pos.get('symbol', '')
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # Warn if too many positions in same symbol
        max_positions_per_symbol = 3
        for symbol, count in symbol_counts.items():
            if count >= max_positions_per_symbol:
                warnings.append(
                    f"Multiple positions in {symbol} ({count}). Consider diversification."
                )
        
        passed = len(errors) == 0
        message = "Risk check passed" if passed else "; ".join(errors)
        if warnings:
            message += " | Warnings: " + "; ".join(warnings)
        
        return RiskCheckResult(
            passed=passed,
            message=message,
            details={
                'position_size_pct': position_size_pct,
                'portfolio_risk_pct': portfolio_risk_pct,
                'daily_risk_pct': daily_risk_pct,
                'open_positions': len(existing_positions),
                'errors': errors,
                'warnings': warnings
            }
        )
    
    def check_correlation_risk(
        self,
        new_symbol: str,
        existing_positions: List[Dict]
    ) -> RiskCheckResult:
        """
        Check for correlation-based risk (simplified - would need sector data for full implementation)
        
        Args:
            new_symbol: Symbol of new trade
            existing_positions: List of existing positions
        
        Returns:
            RiskCheckResult
        """
        # Simplified check - just count positions
        # In a full implementation, would check sector exposure, correlation matrices, etc.
        
        symbol_counts = {}
        for pos in existing_positions:
            symbol = pos.get('symbol', '')
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
        
        # Check if we already have position in this symbol
        if new_symbol in symbol_counts:
            return RiskCheckResult(
                passed=True,
                message=f"Already have position in {new_symbol}. Consider consolidating.",
                details={'existing_count': symbol_counts[new_symbol]}
            )
        
        return RiskCheckResult(
            passed=True,
            message="No correlation risk detected",
            details={}
        )
    
    def check_sector_exposure(
        self,
        new_symbol: str,
        existing_positions: List[Dict],
        max_sector_exposure: float = 0.40
    ) -> RiskCheckResult:
        """
        Check sector exposure limits (simplified - would need sector classification)
        
        Args:
            new_symbol: Symbol of new trade
            existing_positions: List of existing positions
            max_sector_exposure: Maximum exposure per sector (default 40%)
        
        Returns:
            RiskCheckResult
        """
        # Simplified implementation - would need sector mapping
        # For now, just return passed
        
        return RiskCheckResult(
            passed=True,
            message="Sector exposure check passed (simplified)",
            details={'note': 'Full sector exposure check requires sector classification data'}
        )
    
    def validate_trade_plan_risk(
        self,
        plan: Dict,
        portfolio_state: Dict
    ) -> RiskCheckResult:
        """
        Comprehensive risk validation for a trade plan
        
        Args:
            plan: Trade plan dictionary
            portfolio_state: Current portfolio state
        
        Returns:
            RiskCheckResult
        """
        new_plan_capital = plan.get('capital_required', 0)
        new_plan_risk = plan.get('risk_amount', 0)
        new_symbol = plan.get('symbol', '')
        
        current_portfolio_value = portfolio_state.get('total_value', 100000.0)
        existing_positions = portfolio_state.get('positions', [])
        
        # Run all checks
        portfolio_check = self.check_portfolio_risk(
            new_plan_capital, current_portfolio_value, existing_positions, new_plan_risk
        )
        
        correlation_check = self.check_correlation_risk(new_symbol, existing_positions)
        
        sector_check = self.check_sector_exposure(new_symbol, existing_positions)
        
        # Combine results
        all_passed = portfolio_check.passed and correlation_check.passed and sector_check.passed
        
        combined_message = portfolio_check.message
        if not correlation_check.passed:
            combined_message += f" | {correlation_check.message}"
        if not sector_check.passed:
            combined_message += f" | {sector_check.message}"
        
        return RiskCheckResult(
            passed=all_passed,
            message=combined_message,
            details={
                'portfolio_check': portfolio_check.details,
                'correlation_check': correlation_check.details,
                'sector_check': sector_check.details
            }
        )
    
    def check_auto_trade_risk(
        self,
        signal: Dict,
        current_positions: List[Dict],
        portfolio_value: float
    ) -> RiskCheckResult:
        """
        Validate risk for automatic trade execution
        
        Args:
            signal: Signal dictionary with ticker, current_price, stop_loss, etc.
            current_positions: List of current open positions
            portfolio_value: Current portfolio value
        
        Returns:
            RiskCheckResult with pass/fail status
        """
        errors = []
        warnings = []
        
        ticker = signal.get('ticker', '')
        current_price = signal.get('current_price', 0)
        stop_loss = signal.get('stop_loss', 0)
        entry_level = signal.get('entry_level', current_price)
        
        # Validate signal data
        if current_price <= 0:
            errors.append(f"Invalid current price: {current_price}")
        
        if stop_loss <= 0:
            errors.append(f"Invalid stop-loss: {stop_loss}")
        
        if entry_level <= 0:
            errors.append(f"Invalid entry level: {entry_level}")
        
        # Calculate risk per share
        risk_per_share = abs(entry_level - stop_loss)
        if risk_per_share == 0:
            errors.append("Stop-loss equals entry price - no risk defined")
        
        # Calculate position size based on risk per trade
        max_risk_per_trade = self.risk_config.get('max_risk_per_trade', 0.02)
        max_risk_amount = portfolio_value * max_risk_per_trade
        
        # Calculate maximum quantity based on risk
        max_quantity = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
        
        # Check minimum lot size
        min_lot_size = self.risk_config.get('min_lot_size', 1)
        if max_quantity < min_lot_size:
            errors.append(
                f"Calculated quantity ({max_quantity}) below minimum lot size ({min_lot_size})"
            )
        
        # Check maximum position size
        max_position_size = self.risk_config.get('max_position_size', 0.20)
        estimated_capital = entry_level * max_quantity
        position_size_pct = estimated_capital / portfolio_value if portfolio_value > 0 else 0
        
        if position_size_pct > max_position_size:
            errors.append(
                f"Position size ({position_size_pct*100:.2f}%) exceeds maximum ({max_position_size*100:.2f}%)"
            )
        
        # Check maximum open positions
        max_open_positions = self.risk_config.get('max_open_positions', 10)
        if len(current_positions) >= max_open_positions:
            errors.append(
                f"Maximum open positions ({max_open_positions}) already reached"
            )
        
        # Check daily risk limit
        max_daily_risk = self.risk_config.get('max_daily_risk', 0.05)
        daily_risk_pct = max_risk_amount / portfolio_value if portfolio_value > 0 else 0
        
        if daily_risk_pct > max_daily_risk:
            warnings.append(
                f"Daily risk ({daily_risk_pct*100:.2f}%) exceeds recommended limit ({max_daily_risk*100:.2f}%)"
            )
        
        # Check stop-loss placement (should be reasonable distance from entry)
        stop_loss_pct = abs((entry_level - stop_loss) / entry_level) if entry_level > 0 else 0
        
        # Warn if stop-loss is too tight (< 0.5%) or too wide (> 10%)
        if stop_loss_pct < 0.005:
            warnings.append(f"Stop-loss is very tight ({stop_loss_pct*100:.2f}%)")
        elif stop_loss_pct > 0.10:
            warnings.append(f"Stop-loss is very wide ({stop_loss_pct*100:.2f}%)")
        
        # Check risk-reward ratio
        target_1 = signal.get('target_1', 0)
        if target_1 > 0:
            reward_per_share = abs(target_1 - entry_level)
            if risk_per_share > 0:
                risk_reward_ratio = reward_per_share / risk_per_share
                min_risk_reward = self.risk_config.get('min_risk_reward_ratio', 1.5)
                
                if risk_reward_ratio < min_risk_reward:
                    warnings.append(
                        f"Risk-reward ratio ({risk_reward_ratio:.2f}) below minimum ({min_risk_reward})"
                    )
        
        # Check for existing position in same symbol
        for pos in current_positions:
            pos_symbol = pos.get('symbol', '') or pos.get('instrument_key', '') or pos.get('ticker', '')
            if ticker in pos_symbol or pos_symbol in ticker:
                errors.append(f"Already have position in {ticker}")
                break
        
        passed = len(errors) == 0
        message = "Risk check passed" if passed else "; ".join(errors)
        if warnings:
            message += " | Warnings: " + "; ".join(warnings)
        
        return RiskCheckResult(
            passed=passed,
            message=message,
            details={
                'risk_per_share': risk_per_share,
                'max_risk_amount': max_risk_amount,
                'max_quantity': max_quantity,
                'position_size_pct': position_size_pct,
                'daily_risk_pct': daily_risk_pct,
                'stop_loss_pct': stop_loss_pct,
                'risk_amount': max_risk_amount,  # For use by auto_trader
                'errors': errors,
                'warnings': warnings
            }
        )


# Global instance
_risk_manager = None


def get_risk_manager() -> PortfolioRiskManager:
    """Get global risk manager instance"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = PortfolioRiskManager()
    return _risk_manager
