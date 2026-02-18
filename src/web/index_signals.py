"""
Index Trading Signals - Strike price, entry, stop-loss, and reasoning for Nifty, Bank Nifty, Sensex.
Used for index F&O (futures/options) trading with logical levels and win-oriented structure.
"""
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# NSE/BSE index option strike intervals (rounded to nearest)
INDEX_STRIKE_INTERVAL = {
    '^NSEI': 50,   # Nifty 50
    '^NSEBANK': 100,  # Bank Nifty
    '^BSESN': 100,    # Sensex
}

# Display names and keys
INDEX_CONFIG = {
    '^NSEI': {'name': 'Nifty 50', 'key': 'nifty50', 'interval': 50},
    '^NSEBANK': {'name': 'Bank Nifty', 'key': 'banknifty', 'interval': 100},
    '^BSESN': {'name': 'Sensex', 'key': 'sensex', 'interval': 100},
}


def round_to_strike(level: float, interval: int) -> int:
    """Round index level to nearest strike (e.g. 24567 with interval 50 -> 24550)."""
    if level <= 0 or interval <= 0:
        return int(level) if level else 0
    return int(round(level / interval) * interval)


def get_atm_strikes(current_price: float, ticker: str) -> Dict[str, Any]:
    """
    Get ATM (at-the-money) strike and suggested CE/PE strikes for index options.
    Returns strike_atm, strike_ce (for calls), strike_pe (for puts).
    For indices, ATM is same for both; we suggest CE for bullish and PE for bearish.
    """
    interval = INDEX_STRIKE_INTERVAL.get(ticker, 50)
    strike_atm = round_to_strike(current_price, interval)
    return {
        'strike_atm': strike_atm,
        'strike_ce': strike_atm,
        'strike_pe': strike_atm,
        'interval': interval,
    }


def build_reasoning(signal: str, confidence: float, volatility: float,
                    recent_high: float, recent_low: float,
                    current_price: float, ticker: str) -> str:
    """
    Build a short reasoning text for the index signal (logical, trade-oriented).
    """
    parts = []
    # Signal strength
    if signal == 'STRONG_BUY':
        parts.append('Strong bullish bias: ensemble probability supports upside.')
    elif signal == 'BUY':
        parts.append('Bullish bias: model suggests upside with acceptable risk.')
    elif signal == 'STRONG_SELL':
        parts.append('Strong bearish bias: ensemble supports downside.')
    elif signal == 'SELL':
        parts.append('Bearish bias: model suggests downside; consider hedges.')
    else:
        parts.append('Neutral: no clear edge; wait for confirmation.')

    # Confidence
    if confidence >= 0.70:
        parts.append(f'High confidence ({confidence * 100:.0f}%).')
    elif confidence >= 0.55:
        parts.append(f'Moderate confidence ({confidence * 100:.0f}%).')
    else:
        parts.append(f'Lower confidence ({confidence * 100:.0f}%); size position accordingly.')

    # Volatility context (annualized)
    if volatility > 0:
        if volatility < 0.15:
            parts.append('Volatility low; tighter stops may work.')
        elif volatility > 0.25:
            parts.append('Elevated volatility; use wider stop-loss.')

    # Price vs range
    if recent_high > recent_low and current_price > 0:
        range_pct = (recent_high - recent_low) / current_price * 100
        if current_price >= recent_high * 0.98:
            parts.append('Price near recent high; breakout or rejection zone.')
        elif current_price <= recent_low * 1.02:
            parts.append('Price near recent low; support or breakdown zone.')
        if range_pct < 2:
            parts.append('Narrow range; expect expansion.')

    return ' '.join(parts)


def get_option_suggestion(signal: str) -> Dict[str, str]:
    """
    Suggest option type for index trading: BUY -> CE (Call), SELL -> PE (Put).
    """
    if signal in ('STRONG_BUY', 'BUY'):
        return {
            'option_type': 'CE',
            'label': 'Call (CE)',
            'action': 'Consider buying Call option or futures long.',
        }
    if signal in ('STRONG_SELL', 'SELL'):
        return {
            'option_type': 'PE',
            'label': 'Put (PE)',
            'action': 'Consider buying Put option or futures short.',
        }
    return {
        'option_type': '',
        'label': '—',
        'action': 'No directional trade; consider straddle/strangle or wait.',
    }


def estimate_option_premium(strike: int, current_price: float, option_type: str, volatility: float, days_to_expiry: int = 7) -> float:
    """
    Estimate option premium using simplified Black-Scholes approximation.
    For indices, typical premium is 0.5-2% of strike for ATM options.
    """
    if not strike or not current_price or strike <= 0 or current_price <= 0:
        return 0.0
    
    # Moneyness (how far from ATM)
    moneyness = abs(current_price - strike) / current_price
    
    # Base premium estimate (0.5-1.5% of strike for ATM, adjusted for volatility)
    base_premium_pct = 0.008 + (volatility * 0.5)  # Base 0.8% + volatility adjustment
    base_premium = strike * base_premium_pct
    
    # Adjust for moneyness (OTM options cheaper)
    if option_type == 'CE':
        if strike > current_price:  # OTM call
            discount = min(moneyness * 2, 0.5)  # Up to 50% discount
            premium = base_premium * (1 - discount)
        else:  # ITM call
            intrinsic = current_price - strike
            premium = base_premium + intrinsic * 0.3
    else:  # PE
        if strike < current_price:  # OTM put
            discount = min(moneyness * 2, 0.5)
            premium = base_premium * (1 - discount)
        else:  # ITM put
            intrinsic = strike - current_price
            premium = base_premium + intrinsic * 0.3
    
    # Time decay adjustment (closer to expiry = lower premium)
    time_factor = max(0.7, min(1.0, days_to_expiry / 7.0))
    premium = premium * time_factor
    
    return round(premium, 2)


def calculate_strike_premiums(strike: int, current_price: float, option_type: str, volatility: float,
                              entry_level: float, target_1: float, target_2: float) -> Dict[str, float]:
    """
    Calculate premium prices for strike option:
    - Current premium (live market price)
    - Entry premium (premium at entry level)
    - Target 1 premium (premium at target 1)
    - Target 2 premium (premium at target 2)
    """
    # Current premium (at current market price)
    current_premium = estimate_option_premium(strike, current_price, option_type, volatility)
    
    # Entry premium (at entry level)
    entry_premium = estimate_option_premium(strike, entry_level, option_type, volatility)
    
    # Target premiums (at target levels - options will be ITM, higher premium)
    target_1_premium = estimate_option_premium(strike, target_1, option_type, volatility)
    target_2_premium = estimate_option_premium(strike, target_2, option_type, volatility)
    
    # For ITM options at targets, add intrinsic value
    if option_type == 'CE':
        if target_1 > strike:
            target_1_premium = max(target_1_premium, (target_1 - strike) * 0.8)
        if target_2 > strike:
            target_2_premium = max(target_2_premium, (target_2 - strike) * 0.8)
    else:  # PE
        if target_1 < strike:
            target_1_premium = max(target_1_premium, (strike - target_1) * 0.8)
        if target_2 < strike:
            target_2_premium = max(target_2_premium, (strike - target_2) * 0.8)
    
    return {
        'strike_premium_current': round(current_premium, 2),
        'strike_premium_entry': round(entry_premium, 2),
        'strike_premium_target_1': round(target_1_premium, 2),
        'strike_premium_target_2': round(target_2_premium, 2),
    }


def enhance_index_signal(
    ticker: str,
    signal_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enhance ELITE signal response with index-specific fields:
    strike_atm, strike_ce, strike_pe, option_suggestion, reasoning.
    Now includes live strike premium prices (current, entry, targets).
    """
    current = float(signal_response.get('current_price') or 0)
    signal = signal_response.get('signal') or 'HOLD'
    confidence = float(signal_response.get('confidence') or signal_response.get('probability') or 0.5)
    vol = float(signal_response.get('volatility') or 0)
    rh = float(signal_response.get('recent_high') or current)
    rl = float(signal_response.get('recent_low') or current)
    entry_level = float(signal_response.get('entry_level') or current)
    target_1 = float(signal_response.get('target_1') or current)
    target_2 = float(signal_response.get('target_2') or current)

    out = dict(signal_response)
    if ticker not in INDEX_STRIKE_INTERVAL:
        return out

    strikes = get_atm_strikes(current, ticker)
    out['strike_atm'] = strikes['strike_atm']
    out['strike_ce'] = strikes['strike_ce']
    out['strike_pe'] = strikes['strike_pe']
    out['strike_interval'] = strikes['interval']

    opt = get_option_suggestion(signal)
    out['option_type'] = opt['option_type']
    out['option_label'] = opt['label']
    out['option_action'] = opt['action']

    # Calculate strike premium prices for the recommended strike
    recommended_strike = strikes['strike_atm']  # Use ATM strike
    if opt['option_type']:
        premium_details = calculate_strike_premiums(
            strike=recommended_strike,
            current_price=current,
            option_type=opt['option_type'],
            volatility=vol,
            entry_level=entry_level,
            target_1=target_1,
            target_2=target_2
        )
        out.update(premium_details)
        
        # Add strike price details for display
        out['strike_details'] = {
            'strike_price': recommended_strike,
            'option_type': opt['option_type'],
            'current_premium': premium_details['strike_premium_current'],
            'entry_premium': premium_details['strike_premium_entry'],
            'target_1_premium': premium_details['strike_premium_target_1'],
            'target_2_premium': premium_details['strike_premium_target_2'],
            'buy_at_premium': premium_details['strike_premium_entry'],  # Where to buy
            'sell_at_target_1': premium_details['strike_premium_target_1'],  # Where to sell (target 1)
            'sell_at_target_2': premium_details['strike_premium_target_2'],  # Where to sell (target 2)
        }

    out['reasoning'] = build_reasoning(signal, confidence, vol, rh, rl, current, ticker)
    return out
