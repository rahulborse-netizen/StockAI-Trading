#!/usr/bin/env python3
"""
NSE Option Chain - Fetch option chain and compute Greeks (Delta, Gamma, Theta, Vega).
Recommends strike for options based on signal (BUY -> CE, SELL -> PE) and target delta.
"""

import math
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pytz

IST = pytz.timezone('Asia/Kolkata')

# NSE option chain is available for indices (NIFTY, BANKNIFTY) and F&O stocks
INDEX_OPTION_SYMBOLS = {'NIFTY', 'NIFTY 50', 'BANKNIFTY', 'NIFTY BANK', 'FINNIFTY', 'MIDCPNIFTY'}
# Equity F&O symbols - same as NSE (e.g. RELIANCE, TCS, INFY have options)


def _norm_cdf(x: float) -> float:
    """Standard normal CDF using math.erf (no scipy needed)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def black_scholes_greeks(
    S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'CE'
) -> Dict[str, float]:
    """
    Black-Scholes Greeks for European option.
    S=spot, K=strike, T=time to expiry (years), r=risk-free rate, sigma=annual volatility.
    option_type: 'CE' (call) or 'PE' (put).
    """
    if T <= 0:
        T = 1.0 / 365.0  # minimum 1 day
    sqrt_T = math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt_T) if sigma > 0 else 0.0
    d2 = d1 - sigma * sqrt_T if sigma > 0 else 0.0

    nd1 = _norm_cdf(d1)
    nd2 = _norm_cdf(d2)
    n_d1 = _norm_pdf(d1)

    if option_type.upper() in ('CE', 'C', 'CALL'):
        delta = nd1
        theta_per_day = (
            (-S * n_d1 * sigma / (2 * sqrt_T) - r * K * math.exp(-r * T) * nd2) / 365.0
            if sqrt_T > 0 else 0.0
        )
    else:
        delta = nd1 - 1.0
        theta_per_day = (
            (-S * n_d1 * sigma / (2 * sqrt_T) + r * K * math.exp(-r * T) * _norm_cdf(-d2)) / 365.0
            if sqrt_T > 0 else 0.0
        )

    # Gamma same for CE and PE
    gamma = (n_d1 / (S * sigma * sqrt_T)) if (S * sigma * sqrt_T) > 0 else 0.0
    # Vega per 1% move in volatility
    vega = S * n_d1 * sqrt_T * 0.01  # per 1% = 0.01

    return {
        'delta': round(delta, 4),
        'gamma': round(gamma, 6),
        'theta_per_day': round(theta_per_day, 4),
        'vega_per_1pct': round(vega, 4),
        'd1': d1,
        'd2': d2,
    }


def estimate_volatility(annual_atr_pct: float) -> float:
    """Convert ATR-based volatility to annual sigma. annual_atr_pct = (ATR/price)*sqrt(252)*100."""
    return (annual_atr_pct / 100.0) if annual_atr_pct and annual_atr_pct > 0 else 0.20


def get_option_chain_nse(session: requests.Session, symbol: str, is_index: bool = True) -> Optional[Dict]:
    """
    Fetch option chain from NSE.
    symbol: NIFTY, BANKNIFTY for indices; RELIANCE, TCS etc for equity F&O.
    """
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': 'https://www.nseindia.com/option-chain',
    })
    try:
        # Set cookies
        session.get('https://www.nseindia.com', timeout=10)
        session.get('https://www.nseindia.com/option-chain', timeout=10)

        if is_index or symbol.upper() in ('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'):
            url = 'https://www.nseindia.com/api/option-chain-indices'
            params = {'symbol': symbol if symbol.upper() in ('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY') else 'NIFTY'}
        else:
            url = 'https://www.nseindia.com/api/option-chain-equities'
            params = {'symbol': symbol.upper()}

        r = session.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def parse_option_chain(data: Dict, underlying: float) -> List[Dict]:
    """
    Parse NSE option chain response into list of strikes with CE/PE info.
    Returns list of { strike, expiry, ce_price, pe_price, ce_oi, pe_oi }.
    """
    out = []
    try:
        records = data.get('records', {}) or data
        if isinstance(records, dict):
            rec_list = records.get('data', []) or records.get('expiryDates', [])
            if not isinstance(rec_list, list) or not rec_list:
                # Some APIs return records.data as list of strike records
                for exp in (records.get('expiryDates') or [])[:1]:
                    pass
                rec_list = records.get('data', [])
        else:
            rec_list = records

        if not isinstance(rec_list, list):
            return out

        for r in rec_list:
            if isinstance(r, dict):
                strike = r.get('strikePrice') or r.get('strike')
                if strike is None:
                    continue
                strike = float(strike)
                expiry = r.get('expiryDate') or r.get('expiry')
                ce = r.get('CE') or r.get('call') or {}
                pe = r.get('PE') or r.get('put') or {}
                ce_price = ce.get('lastPrice') or ce.get('last') or ce.get('close') or 0
                pe_price = pe.get('lastPrice') or pe.get('last') or pe.get('close') or 0
                if isinstance(ce_price, (list, dict)):
                    ce_price = ce_price.get('lastPrice', 0) if isinstance(ce_price, dict) else 0
                if isinstance(pe_price, (list, dict)):
                    pe_price = pe_price.get('lastPrice', 0) if isinstance(pe_price, dict) else 0
                ce_price = float(ce_price) if ce_price else 0.0
                pe_price = float(pe_price) if pe_price else 0.0
                out.append({
                    'strike': strike,
                    'expiry': expiry,
                    'ce_price': ce_price,
                    'pe_price': pe_price,
                    'ce_oi': ce.get('openInterest') or ce.get('oi') or 0,
                    'pe_oi': pe.get('openInterest') or pe.get('oi') or 0,
                })
    except Exception:
        pass
    return out


def days_to_expiry(expiry_str: str) -> float:
    """Return time to expiry in years."""
    try:
        if isinstance(expiry_str, str) and expiry_str:
            # NSE format often "25-Feb-2026" or "2026-02-25"
            for fmt in ('%d-%b-%Y', '%Y-%m-%d', '%d-%m-%Y'):
                try:
                    exp_dt = datetime.strptime(expiry_str.strip()[:10], fmt)
                    now = datetime.now(IST)
                    if exp_dt.tzinfo is None:
                        exp_dt = IST.localize(exp_dt)
                    delta = (exp_dt - now).total_seconds() / (365.25 * 24 * 3600)
                    return max(delta, 1.0 / 365.0)
                except ValueError:
                    continue
    except Exception:
        pass
    return 7.0 / 365.0  # default 7 days


def recommend_strike(
    spot: float,
    signal: str,
    atr_pct: float,
    expiry_days: float = 7.0,
    target_delta_ce: float = 0.35,
    target_delta_pe: float = -0.35,
    risk_free_rate: float = 0.07,
) -> Dict:
    """
    Recommend option strike and Greeks when option chain is not available.
    signal: 'BUY' -> recommend CE, 'SELL' -> recommend PE.
    atr_pct: (ATR/price)*100 for volatility proxy.
    """
    T = expiry_days / 365.0
    sigma = estimate_volatility(atr_pct * (252 ** 0.5)) if atr_pct else 0.20

    # For BUY: suggest OTM CE with delta ~0.35 (strike above spot)
    # For SELL: suggest OTM PE with delta ~-0.35 (strike below spot)
    # Approximate strike from delta using inverse: K such that BS_delta = target
    # Simple rule: CE strike = spot * (1 + 0.02 * (1 - target_delta)) for OTM
    if signal.upper() == 'BUY':
        # OTM Call: strike slightly above spot
        step = spot * 0.01  # 1% steps
        best_k = spot
        best_delta = 0.0
        for k in [spot + i * step for i in range(1, 30)]:
            g = black_scholes_greeks(spot, k, T, risk_free_rate, sigma, 'CE')
            if g['delta'] <= target_delta_ce + 0.15 and g['delta'] >= target_delta_ce - 0.15:
                best_k = k
                best_delta = g['delta']
                break
            if g['delta'] < target_delta_ce:
                best_k = k
                best_delta = g['delta']
                break
        greeks = black_scholes_greeks(spot, best_k, T, risk_free_rate, sigma, 'CE')
        return {
            'option_type': 'CE',
            'strike': round(best_k, 2),
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta_per_day': greeks['theta_per_day'],
            'vega_per_1pct': greeks['vega_per_1pct'],
            'expiry_days': expiry_days,
            'implied_vol_approx': round(sigma * 100, 2),
            'reason': f'BUY signal -> OTM Call (target delta ~{target_delta_ce})',
        }
    else:
        # SELL -> OTM Put
        step = spot * 0.01
        best_k = spot
        for k in [spot - i * step for i in range(1, 30)]:
            if k <= 0:
                break
            g = black_scholes_greeks(spot, k, T, risk_free_rate, sigma, 'PE')
            if g['delta'] >= target_delta_pe - 0.15 and g['delta'] <= target_delta_pe + 0.15:
                best_k = k
                break
            if g['delta'] > target_delta_pe:
                best_k = k
                break
        greeks = black_scholes_greeks(spot, best_k, T, risk_free_rate, sigma, 'PE')
        return {
            'option_type': 'PE',
            'strike': round(best_k, 2),
            'delta': greeks['delta'],
            'gamma': greeks['gamma'],
            'theta_per_day': greeks['theta_per_day'],
            'vega_per_1pct': greeks['vega_per_1pct'],
            'expiry_days': expiry_days,
            'implied_vol_approx': round(sigma * 100, 2),
            'reason': f'SELL signal -> OTM Put (target delta ~{target_delta_pe})',
        }


def get_recommended_option(
    session: requests.Session,
    symbol: str,
    spot: float,
    signal: str,
    atr_pct: float,
    is_index: bool = False,
) -> Optional[Dict]:
    """
    Get recommended option strike from NSE chain if available, else use Black-Scholes.
    Returns dict with option_type, strike, delta, gamma, theta_per_day, vega_per_1pct, premium_approx, expiry.
    """
    # Try NSE option chain for indices and F&O stocks
    chain = get_option_chain_nse(session, symbol, is_index=is_index)
    T = 7.0 / 365.0
    # atr_pct = (ATR/price)*100 (daily); annualize for sigma
    sigma = estimate_volatility((atr_pct or 2.0) * (252 ** 0.5)) if atr_pct else 0.20
    r = 0.07

    if chain and spot > 0:
        rows = parse_option_chain(chain, spot)
        if rows:
            # Prefer weekly expiry (nearest)
            expiries = sorted(set(r.get('expiry') for r in rows if r.get('expiry')))
            expiry_str = expiries[0] if expiries else None
            T = days_to_expiry(expiry_str) if expiry_str else T

            best = None
            if signal.upper() == 'BUY':
                # CE: choose strike with delta 0.30-0.40 (OTM call)
                for row in rows:
                    k = row['strike']
                    if k <= spot:
                        continue
                    g = black_scholes_greeks(spot, k, T, r, sigma, 'CE')
                    if 0.25 <= g['delta'] <= 0.45:
                        row['greeks'] = g
                        row['option_type'] = 'CE'
                        row['premium_approx'] = row.get('ce_price') or 0
                        best = row
                        break
                if not best and rows:
                    # Pick first OTM CE above spot
                    otm = [r for r in rows if r['strike'] > spot]
                    if otm:
                        r0 = min(otm, key=lambda x: x['strike'])
                        g = black_scholes_greeks(spot, r0['strike'], T, r, sigma, 'CE')
                        r0['greeks'] = g
                        r0['option_type'] = 'CE'
                        r0['premium_approx'] = r0.get('ce_price') or 0
                        best = r0
            else:
                # PE: delta -0.30 to -0.40
                for row in rows:
                    k = row['strike']
                    if k >= spot:
                        continue
                    g = black_scholes_greeks(spot, k, T, r, sigma, 'PE')
                    if -0.45 <= g['delta'] <= -0.25:
                        row['greeks'] = g
                        row['option_type'] = 'PE'
                        row['premium_approx'] = row.get('pe_price') or 0
                        best = row
                        break
                if not best and rows:
                    otm = [r for r in rows if r['strike'] < spot]
                    if otm:
                        r0 = max(otm, key=lambda x: x['strike'])
                        g = black_scholes_greeks(spot, r0['strike'], T, r, sigma, 'PE')
                        r0['greeks'] = g
                        r0['option_type'] = 'PE'
                        r0['premium_approx'] = r0.get('pe_price') or 0
                        best = r0

            if best:
                g = best['greeks']
                return {
                    'option_type': best['option_type'],
                    'strike': best['strike'],
                    'delta': g['delta'],
                    'gamma': g['gamma'],
                    'theta_per_day': g['theta_per_day'],
                    'vega_per_1pct': g['vega_per_1pct'],
                    'premium_approx': best.get('premium_approx') or 0,
                    'expiry': best.get('expiry'),
                    'expiry_days': round(T * 365, 0),
                    'reason': 'From NSE option chain',
                }

    # Fallback: Black-Scholes recommendation (atr_pct = daily ATR as % of spot)
    rec = recommend_strike(
        spot, signal,
        atr_pct=atr_pct if atr_pct else 2.0,
        expiry_days=7.0,
        risk_free_rate=r,
    )
    rec['premium_approx'] = 0
    rec['expiry'] = None
    return rec
