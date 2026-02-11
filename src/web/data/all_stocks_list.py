"""
Comprehensive list of BSE and NSE stocks for signal generation
Now uses dynamic stock universe loader from stock_universe.py
Maintains backward compatibility with hardcoded lists as fallback
"""
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Fallback hardcoded lists (used if stock_universe fails to load)
NIFTY_50 = [
    'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
    'ICICIBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'BAJFINANCE.NS', 'LICI.NS',
    'ITC.NS', 'LT.NS', 'HCLTECH.NS', 'AXISBANK.NS', 'MARUTI.NS',
    'KOTAKBANK.NS', 'ASIANPAINT.NS', 'TITAN.NS', 'ULTRACEMCO.NS', 'NTPC.NS',
    'SUNPHARMA.NS', 'ONGC.NS', 'NESTLEIND.NS', 'POWERGRID.NS', 'M&M.NS',
    'WIPRO.NS', 'COALINDIA.NS', 'TECHM.NS', 'TATAMOTORS.NS', 'JSWSTEEL.NS',
    'ADANIENT.NS', 'ADANIPORTS.NS', 'TATASTEEL.NS', 'DIVISLAB.NS', 'BAJAJFINSV.NS',
    'GRASIM.NS', 'CIPLA.NS', 'HDFCLIFE.NS', 'APOLLOHOSP.NS', 'SBILIFE.NS',
    'EICHERMOT.NS', 'BRITANNIA.NS', 'HEROMOTOCO.NS', 'BPCL.NS', 'INDUSINDBK.NS',
    'DRREDDY.NS', 'ADANIGREEN.NS', 'HINDALCO.NS', 'TATACONSUM.NS', 'VEDL.NS'
]

NIFTY_NEXT_50 = [
    'PIDILITIND.NS', 'MARICO.NS', 'GODREJCP.NS', 'DABUR.NS', 'COLPAL.NS',
    'HAVELLS.NS', 'BERGEPAINT.NS', 'VOLTAS.NS', 'WHIRLPOOL.NS', 'CROMPTON.NS',
    'AMBUJACEM.NS', 'ACC.NS', 'SHREECEM.NS', 'RAMCOCEM.NS', 'JKCEMENT.NS',
    'INDIGO.NS', 'INTERGLOBE.NS', 'SPICEJET.NS', 'JETAIRWAYS.NS', 'VISTARA.NS',
    'ZOMATO.NS', 'SWIGGY.NS', 'PAYTM.NS', 'POLICYBZR.NS', 'NAUKRI.NS',
    'INFOEDGE.NS', 'JUSTDIAL.NS', 'MAKEMYTRIP.NS', 'YATRA.NS', 'IXIGO.NS',
    'FINOLEX.NS', 'ASTERDM.NS', 'FORTIS.NS', 'MAXHEALTH.NS', 'NARAYANA.NS',
    'APOLLO.NS', 'LALPATHLAB.NS', 'METROHEALTH.NS', 'RAINBOW.NS', 'STARHEALTH.NS',
    'HDFCAMC.NS', 'NIPPON.NS', 'FRANKLIN.NS', 'ICICIPRULI.NS', 'BAJAJHOLD.NS',
    'GODREJ.NS', 'EMAMILTD.NS', 'DALBHARAT.NS', 'ULTRATECH.NS', 'SHREECEM.NS'
]

ALL_STOCKS_FALLBACK = NIFTY_50 + NIFTY_NEXT_50


def _get_stock_universe():
    """Get stock universe instance, handling import errors gracefully"""
    try:
        from src.web.stock_universe import get_stock_universe
        return get_stock_universe()
    except Exception as e:
        logger.warning(f"Failed to load stock_universe module: {e}. Using fallback lists.")
        return None


def get_all_stocks() -> List[str]:
    """
    Get comprehensive list of all BSE/NSE stocks
    Uses dynamic stock universe if available, otherwise falls back to hardcoded list
    
    Returns:
        List of Yahoo Finance tickers (e.g., ['RELIANCE.NS', 'TCS.NS', ...])
    """
    universe = _get_stock_universe()
    if universe:
        try:
            stocks = universe.get_all_stocks()
            if stocks:
                logger.debug(f"Loaded {len(stocks)} stocks from dynamic universe")
                return stocks
        except Exception as e:
            logger.warning(f"Error getting stocks from universe: {e}. Using fallback.")
    
    # Fallback to hardcoded list
    logger.debug("Using fallback stock list")
    return ALL_STOCKS_FALLBACK.copy()


def get_nifty_50() -> List[str]:
    """
    Get NIFTY 50 stocks
    Uses dynamic stock universe if available, otherwise falls back to hardcoded list
    """
    universe = _get_stock_universe()
    if universe:
        try:
            # Try to get NSE stocks and filter for NIFTY50 if possible
            # For now, return fallback since we don't have NIFTY50 membership data
            pass
        except Exception:
            pass
    
    return NIFTY_50.copy()


def get_nifty_next_50() -> List[str]:
    """
    Get NIFTY Next 50 stocks
    Uses dynamic stock universe if available, otherwise falls back to hardcoded list
    """
    return NIFTY_NEXT_50.copy()


def get_major_stocks(limit: int = 100) -> List[str]:
    """
    Get major stocks (NIFTY 50 + Next 50)
    
    Args:
        limit: Maximum number of stocks to return
    
    Returns:
        List of tickers
    """
    major = get_nifty_50() + get_nifty_next_50()
    return major[:limit]


def refresh_stock_list():
    """
    Refresh stock list from Upstox/NSE APIs
    Forces a refresh of the stock universe cache
    """
    universe = _get_stock_universe()
    if universe:
        try:
            universe.refresh_universe()
            logger.info("Stock list refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Error refreshing stock list: {e}")
            return False
    else:
        logger.warning("Cannot refresh: stock_universe module not available")
        return False


def get_stocks_by_exchange(exchange: str) -> List[str]:
    """
    Get stocks filtered by exchange
    
    Args:
        exchange: 'NSE' or 'BSE'
    
    Returns:
        List of tickers
    """
    universe = _get_stock_universe()
    if universe:
        try:
            return universe.get_stocks_by_exchange(exchange)
        except Exception as e:
            logger.warning(f"Error getting stocks by exchange: {e}")
    
    # Fallback: filter from all stocks
    all_stocks = get_all_stocks()
    if exchange.upper() == 'NSE':
        return [s for s in all_stocks if s.endswith('.NS')]
    elif exchange.upper() == 'BSE':
        return [s for s in all_stocks if s.endswith('.BO')]
    return []


def get_stocks_by_market_cap(min_mcap: Optional[float] = None, 
                              max_mcap: Optional[float] = None) -> List[str]:
    """
    Get stocks filtered by market cap
    
    Args:
        min_mcap: Minimum market cap (in crores)
        max_mcap: Maximum market cap (in crores)
    
    Returns:
        List of tickers matching market cap criteria
    """
    universe = _get_stock_universe()
    if universe:
        try:
            return universe.get_stocks_by_market_cap(min_mcap, max_mcap)
        except Exception as e:
            logger.warning(f"Error getting stocks by market cap: {e}")
    
    # Fallback: return all stocks
    return get_all_stocks()


def get_stocks_by_sector(sector: str) -> List[str]:
    """
    Get stocks filtered by sector
    
    Args:
        sector: Sector name (e.g., 'BANKING', 'IT', 'PHARMA')
    
    Returns:
        List of tickers in the specified sector
    """
    universe = _get_stock_universe()
    if universe:
        try:
            return universe.get_stocks_by_sector(sector)
        except Exception as e:
            logger.warning(f"Error getting stocks by sector: {e}")
    
    # Fallback: return all stocks
    return get_all_stocks()


def get_stocks_by_liquidity(min_volume: Optional[float] = None) -> List[str]:
    """
    Get stocks filtered by liquidity (average daily volume)
    
    Args:
        min_volume: Minimum average daily volume
    
    Returns:
        List of tickers matching liquidity criteria
    """
    universe = _get_stock_universe()
    if universe:
        try:
            return universe.get_stocks_by_liquidity(min_volume)
        except Exception as e:
            logger.warning(f"Error getting stocks by liquidity: {e}")
    
    # Fallback: return all stocks
    return get_all_stocks()
