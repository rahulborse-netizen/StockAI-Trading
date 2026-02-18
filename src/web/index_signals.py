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


def enhance_index_signal(
    ticker: str,
    signal_response: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Enhance ELITE signal response with index-specific fields:
    strike_atm, strike_ce, strike_pe, option_suggestion, reasoning.
    """
    current = float(signal_response.get('current_price') or 0)
    signal = signal_response.get('signal') or 'HOLD'
    confidence = float(signal_response.get('confidence') or signal_response.get('probability') or 0.5)
    vol = float(signal_response.get('volatility') or 0)
    rh = float(signal_response.get('recent_high') or current)
    rl = float(signal_response.get('recent_low') or current)

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

    out['reasoning'] = build_reasoning(signal, confidence, vol, rh, rl, current, ticker)
    return out
