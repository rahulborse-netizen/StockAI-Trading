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


# Global instance
_risk_manager = None


def get_risk_manager() -> PortfolioRiskManager:
    """Get global risk manager instance"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = PortfolioRiskManager()
    return _risk_manager
