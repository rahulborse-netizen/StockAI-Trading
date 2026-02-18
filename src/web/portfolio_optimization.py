"""
Phase 3.3: Portfolio Optimization
- Modern Portfolio Theory (MPT)
- Risk Parity Allocation
- Black-Litterman Model
- Factor-Based Allocation
- Rebalancing Strategies
- Risk Analytics (VaR, CVaR, Stress Testing, Correlation Analysis)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

try:
    from scipy.optimize import minimize
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("scipy not available - some optimization features will be limited")


@dataclass
class PortfolioAsset:
    """Represents an asset in the portfolio"""
    ticker: str
    weight: float  # Current weight (0-1)
    expected_return: float  # Expected annual return
    volatility: float  # Annual volatility (std dev)
    current_price: float
    quantity: int
    value: float  # Current market value


@dataclass
class OptimizationResult:
    """Result of portfolio optimization"""
    optimal_weights: Dict[str, float]  # ticker -> weight
    expected_return: float
    volatility: float
    sharpe_ratio: float
    method: str
    constraints_satisfied: bool
    optimization_details: Dict[str, Any]


class ModernPortfolioTheory:
    """Modern Portfolio Theory (MPT) - Mean-Variance Optimization"""
    
    def __init__(self, risk_free_rate: float = 0.06):
        """
        Initialize MPT optimizer
        Args:
            risk_free_rate: Risk-free rate (default 6% for India)
        """
        self.risk_free_rate = risk_free_rate
    
    def calculate_portfolio_metrics(
        self,
        weights: np.ndarray,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray
    ) -> Tuple[float, float, float]:
        """
        Calculate portfolio return, volatility, and Sharpe ratio
        """
        portfolio_return = np.dot(weights, expected_returns)
        portfolio_variance = np.dot(weights.T, np.dot(covariance_matrix, weights))
        portfolio_volatility = np.sqrt(portfolio_variance)
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        return portfolio_return, portfolio_volatility, sharpe_ratio
    
    def optimize_portfolio(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        target_return: Optional[float] = None,
        max_weight: float = 1.0,
        min_weight: float = 0.0
    ) -> OptimizationResult:
        """
        Optimize portfolio using mean-variance optimization
        
        Args:
            expected_returns: Array of expected returns for each asset
            covariance_matrix: Covariance matrix of returns
            target_return: Optional target return (if None, maximizes Sharpe ratio)
            max_weight: Maximum weight per asset
            min_weight: Minimum weight per asset
        """
        n_assets = len(expected_returns)
        
        if not SCIPY_AVAILABLE:
            # Fallback: Equal weight portfolio
            equal_weights = np.ones(n_assets) / n_assets
            ret, vol, sharpe = self.calculate_portfolio_metrics(equal_weights, expected_returns, covariance_matrix)
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(equal_weights)},
                expected_return=float(ret),
                volatility=float(vol),
                sharpe_ratio=float(sharpe),
                method="MPT (Equal Weight Fallback)",
                constraints_satisfied=True,
                optimization_details={"note": "scipy not available"}
            )
        
        # Objective function: minimize negative Sharpe ratio
        def objective(weights):
            ret, vol, sharpe = self.calculate_portfolio_metrics(weights, expected_returns, covariance_matrix)
            return -sharpe  # Minimize negative Sharpe = maximize Sharpe
        
        # Constraints
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
        ]
        
        if target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda w: np.dot(w, expected_returns) - target_return
            })
        
        # Bounds
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        
        # Initial guess: equal weights
        initial_weights = np.ones(n_assets) / n_assets
        
        try:
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            optimal_weights = result.x
            ret, vol, sharpe = self.calculate_portfolio_metrics(optimal_weights, expected_returns, covariance_matrix)
            
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(optimal_weights)},
                expected_return=float(ret),
                volatility=float(vol),
                sharpe_ratio=float(sharpe),
                method="MPT (Mean-Variance Optimization)",
                constraints_satisfied=result.success,
                optimization_details={
                    "iterations": result.nit,
                    "message": result.message
                }
            )
        except Exception as e:
            logger.error(f"MPT optimization failed: {e}")
            # Fallback to equal weights
            equal_weights = np.ones(n_assets) / n_assets
            ret, vol, sharpe = self.calculate_portfolio_metrics(equal_weights, expected_returns, covariance_matrix)
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(equal_weights)},
                expected_return=float(ret),
                volatility=float(vol),
                sharpe_ratio=float(sharpe),
                method="MPT (Fallback)",
                constraints_satisfied=False,
                optimization_details={"error": str(e)}
            )
    
    def efficient_frontier(
        self,
        expected_returns: np.ndarray,
        covariance_matrix: np.ndarray,
        num_portfolios: int = 50
    ) -> List[Dict[str, float]]:
        """
        Generate efficient frontier
        """
        min_return = np.min(expected_returns)
        max_return = np.max(expected_returns)
        target_returns = np.linspace(min_return, max_return, num_portfolios)
        
        frontier = []
        for target_ret in target_returns:
            result = self.optimize_portfolio(
                expected_returns=expected_returns,
                covariance_matrix=covariance_matrix,
                target_return=target_ret
            )
            frontier.append({
                'return': result.expected_return,
                'volatility': result.volatility,
                'sharpe_ratio': result.sharpe_ratio
            })
        
        return frontier


class RiskParityOptimizer:
    """Risk Parity Portfolio Optimization"""
    
    def optimize_portfolio(
        self,
        covariance_matrix: np.ndarray,
        max_weight: float = 1.0,
        min_weight: float = 0.0
    ) -> OptimizationResult:
        """
        Optimize portfolio using risk parity (equal risk contribution)
        """
        n_assets = covariance_matrix.shape[0]
        
        if not SCIPY_AVAILABLE:
            # Fallback: Equal weights
            equal_weights = np.ones(n_assets) / n_assets
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(equal_weights)},
                expected_return=0.0,
                volatility=float(np.sqrt(np.dot(equal_weights.T, np.dot(covariance_matrix, equal_weights)))),
                sharpe_ratio=0.0,
                method="Risk Parity (Equal Weight Fallback)",
                constraints_satisfied=True,
                optimization_details={"note": "scipy not available"}
            )
        
        def risk_contribution(weights):
            """Calculate risk contribution of each asset"""
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(covariance_matrix, weights)))
            marginal_contrib = np.dot(covariance_matrix, weights) / portfolio_vol
            risk_contrib = weights * marginal_contrib
            return risk_contrib
        
        def objective(weights):
            """Minimize sum of squared differences from equal risk contribution"""
            risk_contrib = risk_contribution(weights)
            target_risk = np.sum(risk_contrib) / n_assets  # Equal risk per asset
            return np.sum((risk_contrib - target_risk) ** 2)
        
        constraints = [
            {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}
        ]
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        initial_weights = np.ones(n_assets) / n_assets
        
        try:
            result = minimize(
                objective,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            optimal_weights = result.x
            portfolio_vol = np.sqrt(np.dot(optimal_weights.T, np.dot(covariance_matrix, optimal_weights)))
            
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(optimal_weights)},
                expected_return=0.0,  # Risk parity doesn't optimize for return
                volatility=float(portfolio_vol),
                sharpe_ratio=0.0,
                method="Risk Parity",
                constraints_satisfied=result.success,
                optimization_details={
                    "iterations": result.nit,
                    "risk_contributions": risk_contribution(optimal_weights).tolist()
                }
            )
        except Exception as e:
            logger.error(f"Risk parity optimization failed: {e}")
            equal_weights = np.ones(n_assets) / n_assets
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(equal_weights)},
                expected_return=0.0,
                volatility=float(np.sqrt(np.dot(equal_weights.T, np.dot(covariance_matrix, equal_weights)))),
                sharpe_ratio=0.0,
                method="Risk Parity (Fallback)",
                constraints_satisfied=False,
                optimization_details={"error": str(e)}
            )


class BlackLittermanOptimizer:
    """Black-Litterman Model for Portfolio Optimization"""
    
    def __init__(self, risk_free_rate: float = 0.06, tau: float = 0.05):
        """
        Initialize Black-Litterman optimizer
        Args:
            risk_free_rate: Risk-free rate
            tau: Scaling factor (typically 0.05)
        """
        self.risk_free_rate = risk_free_rate
        self.tau = tau
    
    def optimize_portfolio(
        self,
        market_caps: np.ndarray,
        covariance_matrix: np.ndarray,
        views: Optional[Dict[int, float]] = None,  # asset_index -> expected_return_view
        view_confidences: Optional[Dict[int, float]] = None,
        risk_aversion: float = 3.0
    ) -> OptimizationResult:
        """
        Optimize portfolio using Black-Litterman model
        
        Args:
            market_caps: Market capitalization weights (equilibrium portfolio)
            covariance_matrix: Covariance matrix
            views: Dictionary of views (asset_index -> expected return)
            view_confidences: Confidence in views (asset_index -> confidence)
            risk_aversion: Risk aversion coefficient
        """
        n_assets = len(market_caps)
        
        # Equilibrium expected returns (reverse optimization)
        equilibrium_returns = risk_aversion * np.dot(covariance_matrix, market_caps)
        
        # If no views, return equilibrium portfolio
        if not views:
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(market_caps)},
                expected_return=float(np.dot(market_caps, equilibrium_returns)),
                volatility=float(np.sqrt(np.dot(market_caps.T, np.dot(covariance_matrix, market_caps)))),
                sharpe_ratio=0.0,
                method="Black-Litterman (Equilibrium)",
                constraints_satisfied=True,
                optimization_details={"note": "No views provided"}
            )
        
        # Build views matrix P and views vector Q
        P = np.zeros((len(views), n_assets))
        Q = np.zeros(len(views))
        Omega = np.eye(len(views))  # Uncertainty matrix
        
        for idx, (asset_idx, view_return) in enumerate(views.items()):
            P[idx, asset_idx] = 1.0
            Q[idx] = view_return
            if view_confidences and asset_idx in view_confidences:
                Omega[idx, idx] = 1.0 / view_confidences[asset_idx]
        
        # Black-Litterman formula
        tau_sigma = self.tau * covariance_matrix
        M1 = np.linalg.inv(tau_sigma)
        M2 = np.dot(P.T, np.dot(np.linalg.inv(Omega), P))
        M3 = np.dot(M1, equilibrium_returns)
        M4 = np.dot(P.T, np.dot(np.linalg.inv(Omega), Q))
        
        try:
            posterior_cov = np.linalg.inv(M1 + M2)
            posterior_returns = np.dot(posterior_cov, M3 + M4)
            
            # Optimize using posterior returns
            mpt = ModernPortfolioTheory(risk_free_rate=self.risk_free_rate)
            result = mpt.optimize_portfolio(
                expected_returns=posterior_returns,
                covariance_matrix=covariance_matrix
            )
            
            result.method = "Black-Litterman"
            result.optimization_details.update({
                "equilibrium_returns": equilibrium_returns.tolist(),
                "posterior_returns": posterior_returns.tolist(),
                "views": views,
                "tau": self.tau
            })
            
            return result
        except Exception as e:
            logger.error(f"Black-Litterman optimization failed: {e}")
            # Fallback to equilibrium
            return OptimizationResult(
                optimal_weights={f"Asset_{i}": float(w) for i, w in enumerate(market_caps)},
                expected_return=float(np.dot(market_caps, equilibrium_returns)),
                volatility=float(np.sqrt(np.dot(market_caps.T, np.dot(covariance_matrix, market_caps)))),
                sharpe_ratio=0.0,
                method="Black-Litterman (Fallback)",
                constraints_satisfied=False,
                optimization_details={"error": str(e)}
            )


class FactorBasedAllocator:
    """Factor-Based Portfolio Allocation"""
    
    def optimize_portfolio(
        self,
        factor_loadings: np.ndarray,  # n_assets x n_factors
        factor_returns: np.ndarray,  # n_factors
        factor_covariance: np.ndarray,  # n_factors x n_factors
        specific_risk: np.ndarray,  # n_assets (idiosyncratic risk)
        target_factor_exposure: Optional[Dict[int, float]] = None  # factor_index -> target_exposure
    ) -> OptimizationResult:
        """
        Optimize portfolio based on factor exposures
        """
        n_assets = factor_loadings.shape[0]
        n_factors = factor_loadings.shape[1]
        
        # Calculate asset covariance from factors
        factor_contribution = np.dot(factor_loadings, np.dot(factor_covariance, factor_loadings.T))
        specific_contribution = np.diag(specific_risk ** 2)
        covariance_matrix = factor_contribution + specific_contribution
        
        # Calculate expected returns from factor returns
        expected_returns = np.dot(factor_loadings, factor_returns)
        
        # If target factor exposures specified, optimize to match
        if target_factor_exposure:
            # This is a simplified version - full implementation would use constraints
            pass
        
        # Use MPT with factor-based covariance
        mpt = ModernPortfolioTheory()
        result = mpt.optimize_portfolio(
            expected_returns=expected_returns,
            covariance_matrix=covariance_matrix
        )
        
        result.method = "Factor-Based Allocation"
        result.optimization_details.update({
            "factor_loadings": factor_loadings.tolist(),
            "factor_returns": factor_returns.tolist(),
            "specific_risk": specific_risk.tolist()
        })
        
        return result


class RiskAnalytics:
    """Risk Analytics: VaR, CVaR, Stress Testing, Correlation Analysis"""
    
    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize risk analytics
        Args:
            confidence_level: Confidence level for VaR/CVaR (default 95%)
        """
        self.confidence_level = confidence_level
    
    def calculate_var(
        self,
        portfolio_returns: np.ndarray,
        portfolio_value: float,
        method: str = 'historical'
    ) -> Dict[str, float]:
        """
        Calculate Value at Risk (VaR)
        
        Args:
            portfolio_returns: Historical portfolio returns
            portfolio_value: Current portfolio value
            method: 'historical', 'parametric', or 'monte_carlo'
        """
        if method == 'historical':
            var_percentile = (1 - self.confidence_level) * 100
            var_return = np.percentile(portfolio_returns, var_percentile)
            var_value = abs(var_return * portfolio_value)
            
            return {
                'var_percentile': var_percentile,
                'var_return': float(var_return),
                'var_value': float(var_value),
                'confidence_level': self.confidence_level,
                'method': 'historical'
            }
        
        elif method == 'parametric':
            mean_return = np.mean(portfolio_returns)
            std_return = np.std(portfolio_returns)
            z_score = norm.ppf(1 - self.confidence_level) if SCIPY_AVAILABLE else 1.65
            
            var_return = mean_return - z_score * std_return
            var_value = abs(var_return * portfolio_value)
            
            return {
                'var_return': float(var_return),
                'var_value': float(var_value),
                'confidence_level': self.confidence_level,
                'method': 'parametric',
                'z_score': float(z_score)
            }
        
        else:
            # Monte Carlo (simplified)
            mean_return = np.mean(portfolio_returns)
            std_return = np.std(portfolio_returns)
            simulated_returns = np.random.normal(mean_return, std_return, 10000)
            var_percentile = (1 - self.confidence_level) * 100
            var_return = np.percentile(simulated_returns, var_percentile)
            var_value = abs(var_return * portfolio_value)
            
            return {
                'var_return': float(var_return),
                'var_value': float(var_value),
                'confidence_level': self.confidence_level,
                'method': 'monte_carlo'
            }
    
    def calculate_cvar(
        self,
        portfolio_returns: np.ndarray,
        portfolio_value: float
    ) -> Dict[str, float]:
        """
        Calculate Conditional Value at Risk (CVaR) / Expected Shortfall
        """
        var_result = self.calculate_var(portfolio_returns, portfolio_value, method='historical')
        var_threshold = var_result['var_return']
        
        # CVaR is the mean of returns below VaR threshold
        tail_returns = portfolio_returns[portfolio_returns <= var_threshold]
        cvar_return = np.mean(tail_returns) if len(tail_returns) > 0 else var_threshold
        cvar_value = abs(cvar_return * portfolio_value)
        
        return {
            'cvar_return': float(cvar_return),
            'cvar_value': float(cvar_value),
            'var_threshold': float(var_threshold),
            'confidence_level': self.confidence_level
        }
    
    def stress_test(
        self,
        portfolio_weights: np.ndarray,
        covariance_matrix: np.ndarray,
        stress_scenarios: List[Dict[str, float]]
    ) -> List[Dict[str, Any]]:
        """
        Stress test portfolio under various scenarios
        
        Args:
            portfolio_weights: Current portfolio weights
            covariance_matrix: Covariance matrix
            stress_scenarios: List of stress scenarios (e.g., market crash, sector shock)
        """
        results = []
        
        for scenario in stress_scenarios:
            # Apply stress shocks to covariance matrix or returns
            stressed_cov = covariance_matrix * scenario.get('volatility_multiplier', 1.0)
            portfolio_vol = np.sqrt(np.dot(portfolio_weights.T, np.dot(stressed_cov, portfolio_weights)))
            
            results.append({
                'scenario_name': scenario.get('name', 'Unknown'),
                'portfolio_volatility': float(portfolio_vol),
                'stress_multiplier': scenario.get('volatility_multiplier', 1.0),
                'expected_loss': float(portfolio_vol * scenario.get('shock_size', 0.1))
            })
        
        return results
    
    def correlation_analysis(
        self,
        returns_matrix: np.ndarray,  # n_assets x n_periods
        asset_names: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze correlation between assets
        """
        correlation_matrix = np.corrcoef(returns_matrix)
        
        # Find highest and lowest correlations
        n = len(asset_names)
        max_corr = -1
        min_corr = 1
        max_pair = None
        min_pair = None
        
        for i in range(n):
            for j in range(i + 1, n):
                corr = correlation_matrix[i, j]
                if corr > max_corr:
                    max_corr = corr
                    max_pair = (asset_names[i], asset_names[j])
                if corr < min_corr:
                    min_corr = corr
                    min_pair = (asset_names[i], asset_names[j])
        
        return {
            'correlation_matrix': correlation_matrix.tolist(),
            'asset_names': asset_names,
            'max_correlation': {
                'value': float(max_corr),
                'pair': max_pair
            },
            'min_correlation': {
                'value': float(min_corr),
                'pair': min_pair
            },
            'average_correlation': float(np.mean(correlation_matrix[np.triu_indices(n, k=1)]))
        }
    
    def sector_exposure(
        self,
        portfolio_weights: Dict[str, float],
        asset_sectors: Dict[str, str]
    ) -> Dict[str, float]:
        """
        Calculate sector exposure of portfolio
        """
        sector_exposure = {}
        
        for ticker, weight in portfolio_weights.items():
            sector = asset_sectors.get(ticker, 'Unknown')
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + weight
        
        return sector_exposure


class RebalancingStrategy:
    """Portfolio Rebalancing Strategies"""
    
    def __init__(self, threshold: float = 0.05, rebalancing_cost: float = 0.001):
        """
        Initialize rebalancing strategy
        Args:
            threshold: Threshold for triggering rebalancing (5% deviation)
            rebalancing_cost: Transaction cost per trade (0.1%)
        """
        self.threshold = threshold
        self.rebalancing_cost = rebalancing_cost
    
    def check_rebalancing_needed(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Check if rebalancing is needed
        """
        deviations = {}
        max_deviation = 0.0
        needs_rebalancing = False
        
        for ticker in set(list(current_weights.keys()) + list(target_weights.keys())):
            current = current_weights.get(ticker, 0.0)
            target = target_weights.get(ticker, 0.0)
            deviation = abs(current - target)
            deviations[ticker] = {
                'current': current,
                'target': target,
                'deviation': deviation,
                'deviation_pct': deviation / target * 100 if target > 0 else 0.0
            }
            
            if deviation > max_deviation:
                max_deviation = deviation
            
            if deviation > self.threshold:
                needs_rebalancing = True
        
        return {
            'needs_rebalancing': needs_rebalancing,
            'max_deviation': max_deviation,
            'threshold': self.threshold,
            'deviations': deviations,
            'rebalancing_cost': self.rebalancing_cost
        }
    
    def calculate_rebalancing_trades(
        self,
        current_weights: Dict[str, float],
        target_weights: Dict[str, float],
        portfolio_value: float,
        current_prices: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """
        Calculate trades needed for rebalancing
        """
        trades = []
        
        for ticker in set(list(current_weights.keys()) + list(target_weights.keys())):
            current_weight = current_weights.get(ticker, 0.0)
            target_weight = target_weights.get(ticker, 0.0)
            
            if abs(current_weight - target_weight) > self.threshold:
                current_value = current_weight * portfolio_value
                target_value = target_weight * portfolio_value
                trade_value = target_value - current_value
                
                price = current_prices.get(ticker, 0.0)
                if price > 0:
                    quantity = int(trade_value / price)
                    if quantity != 0:
                        trades.append({
                            'ticker': ticker,
                            'action': 'BUY' if quantity > 0 else 'SELL',
                            'quantity': abs(quantity),
                            'value': abs(trade_value),
                            'current_weight': current_weight,
                            'target_weight': target_weight,
                            'price': price
                        })
        
        return trades
    
    def time_based_rebalancing(
        self,
        last_rebalance_date: datetime,
        rebalance_frequency: str = 'monthly'  # 'daily', 'weekly', 'monthly', 'quarterly'
    ) -> bool:
        """
        Check if time-based rebalancing is due
        """
        now = datetime.now()
        days_since = (now - last_rebalance_date).days
        
        frequency_days = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90
        }
        
        return days_since >= frequency_days.get(rebalance_frequency, 30)


# Singleton instances
_mpt_optimizer: Optional[ModernPortfolioTheory] = None
_risk_parity_optimizer: Optional[RiskParityOptimizer] = None
_black_litterman_optimizer: Optional[BlackLittermanOptimizer] = None
_factor_allocator: Optional[FactorBasedAllocator] = None
_risk_analytics: Optional[RiskAnalytics] = None
_rebalancing_strategy: Optional[RebalancingStrategy] = None


def get_mpt_optimizer(risk_free_rate: float = 0.06) -> ModernPortfolioTheory:
    """Get singleton MPT optimizer"""
    global _mpt_optimizer
    if _mpt_optimizer is None:
        _mpt_optimizer = ModernPortfolioTheory(risk_free_rate=risk_free_rate)
    return _mpt_optimizer


def get_risk_parity_optimizer() -> RiskParityOptimizer:
    """Get singleton Risk Parity optimizer"""
    global _risk_parity_optimizer
    if _risk_parity_optimizer is None:
        _risk_parity_optimizer = RiskParityOptimizer()
    return _risk_parity_optimizer


def get_black_litterman_optimizer(risk_free_rate: float = 0.06, tau: float = 0.05) -> BlackLittermanOptimizer:
    """Get singleton Black-Litterman optimizer"""
    global _black_litterman_optimizer
    if _black_litterman_optimizer is None:
        _black_litterman_optimizer = BlackLittermanOptimizer(risk_free_rate=risk_free_rate, tau=tau)
    return _black_litterman_optimizer


def get_factor_allocator() -> FactorBasedAllocator:
    """Get singleton Factor-Based Allocator"""
    global _factor_allocator
    if _factor_allocator is None:
        _factor_allocator = FactorBasedAllocator()
    return _factor_allocator


def get_risk_analytics(confidence_level: float = 0.95) -> RiskAnalytics:
    """Get singleton Risk Analytics"""
    global _risk_analytics
    if _risk_analytics is None or _risk_analytics.confidence_level != confidence_level:
        _risk_analytics = RiskAnalytics(confidence_level=confidence_level)
    return _risk_analytics


def get_rebalancing_strategy(threshold: float = 0.05, rebalancing_cost: float = 0.001) -> RebalancingStrategy:
    """Get singleton Rebalancing Strategy"""
    global _rebalancing_strategy
    if _rebalancing_strategy is None:
        _rebalancing_strategy = RebalancingStrategy(threshold=threshold, rebalancing_cost=rebalancing_cost)
    return _rebalancing_strategy
