"""
Options Trading Module
Phase 3.1: Options chain analysis, Greeks calculation, strategy builder, options signals
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from scipy.stats import norm
from math import log, sqrt, exp

logger = logging.getLogger(__name__)

# Check if scipy is available for Greeks calculation
SCIPY_AVAILABLE = False
try:
    from scipy.stats import norm
    SCIPY_AVAILABLE = True
except ImportError:
    logger.warning("scipy not available. Greeks calculation will use simplified formulas.")


class OptionsGreeks:
    """
    Calculate options Greeks: Delta, Gamma, Theta, Vega, Rho
    Uses Black-Scholes model for European options.
    """
    
    @staticmethod
    def black_scholes_call(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Black-Scholes call option price.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
        
        Returns:
            Call option price
        """
        if T <= 0:
            return max(S - K, 0)
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        if SCIPY_AVAILABLE:
            call_price = S * norm.cdf(d1) - K * exp(-r * T) * norm.cdf(d2)
        else:
            # Simplified approximation
            call_price = max(S - K, 0) + S * sigma * sqrt(T) * 0.4
        
        return call_price
    
    @staticmethod
    def black_scholes_put(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Black-Scholes put option price.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility (annualized)
        
        Returns:
            Put option price
        """
        if T <= 0:
            return max(K - S, 0)
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        if SCIPY_AVAILABLE:
            put_price = K * exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            # Simplified approximation
            put_price = max(K - S, 0) + S * sigma * sqrt(T) * 0.4
        
        return put_price
    
    @staticmethod
    def calculate_delta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'CE') -> float:
        """
        Calculate Delta (price sensitivity).
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            option_type: 'CE' for call, 'PE' for put
        
        Returns:
            Delta value
        """
        if T <= 0:
            if option_type == 'CE':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        
        if SCIPY_AVAILABLE:
            if option_type == 'CE':
                delta = norm.cdf(d1)
            else:  # PE
                delta = -norm.cdf(-d1)
        else:
            # Simplified approximation
            moneyness = S / K
            if option_type == 'CE':
                delta = max(0, min(1, (moneyness - 0.9) / 0.2))
            else:
                delta = max(-1, min(0, -(1.1 - moneyness) / 0.2))
        
        return round(delta, 4)
    
    @staticmethod
    def calculate_gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Gamma (Delta sensitivity).
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
        
        Returns:
            Gamma value
        """
        if T <= 0:
            return 0.0
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        
        if SCIPY_AVAILABLE:
            gamma = norm.pdf(d1) / (S * sigma * sqrt(T))
        else:
            # Simplified approximation (highest for ATM options)
            moneyness = abs(S / K - 1)
            gamma = max(0, 0.1 * (1 - moneyness * 10))
        
        return round(gamma, 6)
    
    @staticmethod
    def calculate_theta(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'CE') -> float:
        """
        Calculate Theta (time decay).
        Returns negative value (option loses value over time).
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
            option_type: 'CE' for call, 'PE' for put
        
        Returns:
            Theta value (per day, negative)
        """
        if T <= 0:
            return 0.0
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        d2 = d1 - sigma * sqrt(T)
        
        if SCIPY_AVAILABLE:
            if option_type == 'CE':
                theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt(T)) - 
                        r * K * exp(-r * T) * norm.cdf(d2)) / 365
            else:  # PE
                theta = (-S * norm.pdf(d1) * sigma / (2 * sqrt(T)) + 
                        r * K * exp(-r * T) * norm.cdf(-d2)) / 365
        else:
            # Simplified approximation
            time_factor = 1 / max(T * 365, 1)
            theta = -S * sigma * time_factor * 0.01
        
        return round(theta, 4)
    
    @staticmethod
    def calculate_vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vega (volatility sensitivity).
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate
            sigma: Volatility
        
        Returns:
            Vega value (per 1% change in volatility)
        """
        if T <= 0:
            return 0.0
        
        d1 = (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))
        
        if SCIPY_AVAILABLE:
            vega = S * norm.pdf(d1) * sqrt(T) * 0.01  # Per 1% change
        else:
            # Simplified approximation
            vega = S * sqrt(T) * 0.01 * 0.4
        
        return round(vega, 4)
    
    @staticmethod
    def calculate_all_greeks(S: float, K: float, T: float, r: float, sigma: float, 
                            option_type: str = 'CE') -> Dict[str, float]:
        """
        Calculate all Greeks for an option.
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (in years)
            r: Risk-free rate (default 0.06 for 6%)
            sigma: Volatility (annualized)
            option_type: 'CE' for call, 'PE' for put
        
        Returns:
            Dictionary with all Greeks
        """
        if r <= 0:
            r = 0.06  # Default 6% risk-free rate
        
        return {
            'delta': OptionsGreeks.calculate_delta(S, K, T, r, sigma, option_type),
            'gamma': OptionsGreeks.calculate_gamma(S, K, T, r, sigma),
            'theta': OptionsGreeks.calculate_theta(S, K, T, r, sigma, option_type),
            'vega': OptionsGreeks.calculate_vega(S, K, T, r, sigma),
            'option_type': option_type,
            'strike': K,
            'current_price': S,
            'time_to_expiry_days': round(T * 365, 1),
        }


class OptionsChainAnalyzer:
    """
    Analyzes options chain data.
    """
    
    def __init__(self):
        self.chain_cache: Dict[str, Dict] = {}
    
    def analyze_chain(self, options_chain: Dict, current_price: float, 
                     volatility: float = 0.2, risk_free_rate: float = 0.06,
                     days_to_expiry: int = 7) -> Dict[str, any]:
        """
        Analyze options chain and calculate Greeks.
        
        Args:
            options_chain: Options chain data from Upstox
            current_price: Current underlying price
            volatility: Implied or historical volatility
            risk_free_rate: Risk-free interest rate
            days_to_expiry: Days to expiration
        
        Returns:
            Options chain analysis with Greeks
        """
        if not options_chain:
            return {}
        
        T = days_to_expiry / 365.0  # Convert to years
        
        calls = options_chain.get('call_options', [])
        puts = options_chain.get('put_options', [])
        
        # Analyze calls
        call_analysis = []
        for call in calls[:20]:  # Analyze top 20 strikes
            strike = call.get('strike', 0)
            if strike <= 0:
                continue
            
            greeks = OptionsGreeks.calculate_all_greeks(
                S=current_price,
                K=strike,
                T=T,
                r=risk_free_rate,
                sigma=volatility,
                option_type='CE'
            )
            
            # Add market data
            greeks['market_price'] = call.get('last_price', 0)
            greeks['volume'] = call.get('volume', 0)
            greeks['open_interest'] = call.get('open_interest', 0)
            greeks['iv'] = call.get('implied_volatility', volatility)
            
            call_analysis.append(greeks)
        
        # Analyze puts
        put_analysis = []
        for put in puts[:20]:  # Analyze top 20 strikes
            strike = put.get('strike', 0)
            if strike <= 0:
                continue
            
            greeks = OptionsGreeks.calculate_all_greeks(
                S=current_price,
                K=strike,
                T=T,
                r=risk_free_rate,
                sigma=volatility,
                option_type='PE'
            )
            
            # Add market data
            greeks['market_price'] = put.get('last_price', 0)
            greeks['volume'] = put.get('volume', 0)
            greeks['open_interest'] = put.get('open_interest', 0)
            greeks['iv'] = put.get('implied_volatility', volatility)
            
            put_analysis.append(greeks)
        
        # Find ATM options
        atm_strike = round(current_price / 50) * 50  # Round to nearest 50
        atm_call = next((c for c in call_analysis if abs(c['strike'] - atm_strike) < 25), None)
        atm_put = next((p for p in put_analysis if abs(p['strike'] - atm_strike) < 25), None)
        
        # Calculate Put-Call Ratio
        total_call_volume = sum(c.get('volume', 0) for c in call_analysis)
        total_put_volume = sum(p.get('volume', 0) for p in put_analysis)
        pcr = total_put_volume / total_call_volume if total_call_volume > 0 else 0
        
        return {
            'current_price': current_price,
            'atm_strike': atm_strike,
            'days_to_expiry': days_to_expiry,
            'volatility': volatility,
            'call_options': call_analysis[:10],  # Top 10
            'put_options': put_analysis[:10],    # Top 10
            'atm_call': atm_call,
            'atm_put': atm_put,
            'put_call_ratio': round(pcr, 4),
            'total_call_volume': total_call_volume,
            'total_put_volume': total_put_volume,
            'analysis_timestamp': datetime.now().isoformat(),
        }
    
    def find_best_strikes(self, chain_analysis: Dict, signal_type: str = 'BUY') -> Dict[str, any]:
        """
        Find best strike prices based on signal and Greeks.
        
        Args:
            chain_analysis: Options chain analysis result
            signal_type: 'BUY' or 'SELL'
        
        Returns:
            Recommended strikes with reasoning
        """
        if not chain_analysis:
            return {}
        
        calls = chain_analysis.get('call_options', [])
        puts = chain_analysis.get('put_options', [])
        
        recommendations = {}
        
        if signal_type in ('BUY', 'STRONG_BUY'):
            # For bullish signals, recommend call options
            # Prefer OTM calls with good Delta (0.3-0.5) and low Theta decay
            best_calls = sorted(
                [c for c in calls if 0.3 <= abs(c.get('delta', 0)) <= 0.5],
                key=lambda x: abs(x.get('theta', 0))  # Lower Theta (less decay) is better
            )[:3]
            
            recommendations['recommended_calls'] = best_calls
            recommendations['strategy'] = 'Buy OTM Call Options'
            recommendations['reasoning'] = 'Bullish signal - OTM calls offer good risk/reward with moderate Delta'
        
        elif signal_type in ('SELL', 'STRONG_SELL'):
            # For bearish signals, recommend put options
            # Prefer OTM puts with good Delta (-0.3 to -0.5) and low Theta decay
            best_puts = sorted(
                [p for p in puts if -0.5 <= p.get('delta', 0) <= -0.3],
                key=lambda x: abs(x.get('theta', 0))
            )[:3]
            
            recommendations['recommended_puts'] = best_puts
            recommendations['strategy'] = 'Buy OTM Put Options'
            recommendations['reasoning'] = 'Bearish signal - OTM puts offer good risk/reward with moderate Delta'
        
        return recommendations


class OptionsStrategyBuilder:
    """
    Builds options trading strategies.
    """
    
    @staticmethod
    def build_straddle(current_price: float, strike: float, call_price: float, 
                      put_price: float) -> Dict[str, any]:
        """
        Build a straddle strategy (long call + long put at same strike).
        
        Args:
            current_price: Current underlying price
            strike: Strike price
            call_price: Call option premium
            put_price: Put option premium
        
        Returns:
            Straddle strategy details
        """
        total_cost = call_price + put_price
        max_loss = total_cost
        max_profit = float('inf')  # Unlimited
        
        # Breakeven points
        breakeven_high = strike + total_cost
        breakeven_low = strike - total_cost
        
        return {
            'strategy': 'STRADDLE',
            'strike': strike,
            'call_premium': call_price,
            'put_premium': put_price,
            'total_cost': round(total_cost, 2),
            'max_loss': round(max_loss, 2),
            'max_profit': 'Unlimited',
            'breakeven_high': round(breakeven_high, 2),
            'breakeven_low': round(breakeven_low, 2),
            'profit_zone': f'Above ₹{breakeven_high:.2f} or below ₹{breakeven_low:.2f}',
            'suitable_for': 'High volatility expected',
        }
    
    @staticmethod
    def build_strangle(current_price: float, call_strike: float, put_strike: float,
                      call_price: float, put_price: float) -> Dict[str, any]:
        """
        Build a strangle strategy (long OTM call + long OTM put).
        
        Args:
            current_price: Current underlying price
            call_strike: Call strike price
            put_strike: Put strike price
            call_price: Call option premium
            put_price: Put option premium
        
        Returns:
            Strangle strategy details
        """
        total_cost = call_price + put_price
        max_loss = total_cost
        
        # Breakeven points
        breakeven_high = call_strike + total_cost
        breakeven_low = put_strike - total_cost
        
        return {
            'strategy': 'STRANGLE',
            'call_strike': call_strike,
            'put_strike': put_strike,
            'call_premium': call_price,
            'put_premium': put_price,
            'total_cost': round(total_cost, 2),
            'max_loss': round(max_loss, 2),
            'max_profit': 'Unlimited',
            'breakeven_high': round(breakeven_high, 2),
            'breakeven_low': round(breakeven_low, 2),
            'profit_zone': f'Above ₹{breakeven_high:.2f} or below ₹{breakeven_low:.2f}',
            'suitable_for': 'High volatility expected, cheaper than straddle',
        }
    
    @staticmethod
    def build_bull_call_spread(current_price: float, lower_strike: float, higher_strike: float,
                               lower_call_price: float, higher_call_price: float) -> Dict[str, any]:
        """
        Build a bull call spread (buy lower strike call, sell higher strike call).
        
        Args:
            current_price: Current underlying price
            lower_strike: Lower strike (buy)
            higher_strike: Higher strike (sell)
            lower_call_price: Lower strike call premium (paid)
            higher_call_price: Higher strike call premium (received)
        
        Returns:
            Bull call spread details
        """
        net_cost = lower_call_price - higher_call_price
        max_profit = (higher_strike - lower_strike) - net_cost
        max_loss = net_cost
        breakeven = lower_strike + net_cost
        
        return {
            'strategy': 'BULL_CALL_SPREAD',
            'lower_strike': lower_strike,
            'higher_strike': higher_strike,
            'net_cost': round(net_cost, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(max_loss, 2),
            'breakeven': round(breakeven, 2),
            'profit_zone': f'Above ₹{breakeven:.2f}',
            'suitable_for': 'Moderately bullish, limited risk',
        }
    
    @staticmethod
    def build_bear_put_spread(current_price: float, higher_strike: float, lower_strike: float,
                              higher_put_price: float, lower_put_price: float) -> Dict[str, any]:
        """
        Build a bear put spread (buy higher strike put, sell lower strike put).
        
        Args:
            current_price: Current underlying price
            higher_strike: Higher strike (buy)
            lower_strike: Lower strike (sell)
            higher_put_price: Higher strike put premium (paid)
            lower_put_price: Lower strike put premium (received)
        
        Returns:
            Bear put spread details
        """
        net_cost = higher_put_price - lower_put_price
        max_profit = (higher_strike - lower_strike) - net_cost
        max_loss = net_cost
        breakeven = higher_strike - net_cost
        
        return {
            'strategy': 'BEAR_PUT_SPREAD',
            'higher_strike': higher_strike,
            'lower_strike': lower_strike,
            'net_cost': round(net_cost, 2),
            'max_profit': round(max_profit, 2),
            'max_loss': round(max_loss, 2),
            'breakeven': round(breakeven, 2),
            'profit_zone': f'Below ₹{breakeven:.2f}',
            'suitable_for': 'Moderately bearish, limited risk',
        }


class OptionsSignalGenerator:
    """
    Generates options trading signals based on underlying analysis.
    """
    
    def __init__(self):
        self.chain_analyzer = OptionsChainAnalyzer()
        self.strategy_builder = OptionsStrategyBuilder()
    
    def generate_options_signal(self, ticker: str, underlying_signal: Dict,
                              options_chain: Optional[Dict] = None,
                              volatility: float = 0.2) -> Dict[str, any]:
        """
        Generate options trading signal based on underlying signal.
        
        Args:
            ticker: Stock/index ticker
            underlying_signal: Signal from ELITE signal generator
            options_chain: Optional options chain data from Upstox
            volatility: Implied or historical volatility
        
        Returns:
            Options trading signal with recommendations
        """
        current_price = underlying_signal.get('current_price', 0)
        signal_type = underlying_signal.get('signal', 'HOLD')
        confidence = underlying_signal.get('confidence', 0.5)
        
        if current_price <= 0:
            return {'error': 'Invalid current price'}
        
        options_signal = {
            'ticker': ticker,
            'underlying_signal': signal_type,
            'underlying_confidence': confidence,
            'current_price': current_price,
            'timestamp': datetime.now().isoformat(),
        }
        
        # If options chain available, analyze it
        if options_chain:
            days_to_expiry = 7  # Default weekly expiry
            chain_analysis = self.chain_analyzer.analyze_chain(
                options_chain,
                current_price,
                volatility,
                days_to_expiry=days_to_expiry
            )
            options_signal['chain_analysis'] = chain_analysis
            
            # Find best strikes
            strike_recommendations = self.chain_analyzer.find_best_strikes(
                chain_analysis,
                signal_type
            )
            options_signal['strike_recommendations'] = strike_recommendations
        
        # Generate strategy recommendations
        if signal_type in ('BUY', 'STRONG_BUY'):
            options_signal['recommended_strategy'] = 'Buy Call Options'
            options_signal['strategy_details'] = {
                'type': 'LONG_CALL',
                'reasoning': 'Bullish underlying signal - Buy OTM call options for leverage',
                'risk_level': 'HIGH',
                'max_loss': 'Premium paid',
                'max_profit': 'Unlimited',
            }
        elif signal_type in ('SELL', 'STRONG_SELL'):
            options_signal['recommended_strategy'] = 'Buy Put Options'
            options_signal['strategy_details'] = {
                'type': 'LONG_PUT',
                'reasoning': 'Bearish underlying signal - Buy OTM put options for leverage',
                'risk_level': 'HIGH',
                'max_loss': 'Premium paid',
                'max_profit': 'Unlimited',
            }
        else:
            options_signal['recommended_strategy'] = 'Neutral Strategies'
            options_signal['strategy_details'] = {
                'type': 'STRADDLE_STRANGLE',
                'reasoning': 'Neutral signal - Consider volatility strategies',
                'risk_level': 'MEDIUM',
            }
        
        return options_signal


# Global instance
_options_signal_generator: Optional[OptionsSignalGenerator] = None

def get_options_signal_generator() -> OptionsSignalGenerator:
    """Get global OptionsSignalGenerator instance"""
    global _options_signal_generator
    if _options_signal_generator is None:
        _options_signal_generator = OptionsSignalGenerator()
    return _options_signal_generator
