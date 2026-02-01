from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


@dataclass(frozen=True)
class ConstituentList:
    index_name: str
    tickers: list[str]
    source: str  # "manual" or "api"
    last_updated: Optional[str] = None


# Manual constituent lists (as fallback when API is unavailable)
MANUAL_NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "HINDUNILVR.NS", "BHARTIARTL.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS",
    "BAJAJFINSV.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "POWERGRID.NS", "ONGC.NS", "NTPC.NS", "COALINDIA.NS", "TATAMOTORS.NS",
    "JSWSTEEL.NS", "TATASTEEL.NS", "DIVISLAB.NS", "ADANIENT.NS",
    "ADANIPORTS.NS", "APOLLOHOSP.NS", "CIPLA.NS", "DRREDDY.NS",
    "EICHERMOT.NS", "GRASIM.NS", "HDFCLIFE.NS", "HEROMOTOCO.NS",
    "HINDALCO.NS", "INDUSINDBK.NS", "M&M.NS", "MARICO.NS", "SBILIFE.NS",
    "TECHM.NS", "VEDL.NS", "BPCL.NS", "HDFCAMC.NS", "SIEMENS.NS"
]

MANUAL_BANKNIFTY = [
    "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "INDUSINDBK.NS", "FEDERALBNK.NS", "BANDHANBNK.NS", "PNB.NS",
    "IDFCFIRSTB.NS", "AUBANK.NS", "BANKBARODA.NS"
]

MANUAL_SENSEX = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "SBIN.NS", "ITC.NS", "LT.NS", "AXISBANK.NS", "KOTAKBANK.NS",
    "HINDUNILVR.NS", "BHARTIARTL.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "HCLTECH.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS",
    "BAJAJFINSV.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "WIPRO.NS",
    "POWERGRID.NS", "ONGC.NS", "NTPC.NS", "COALINDIA.NS", "TATAMOTORS.NS",
    "JSWSTEEL.NS", "TATASTEEL.NS", "DIVISLAB.NS"
]


def get_constituents(index_name: str, cache_dir: Optional[Path] = None) -> ConstituentList:
    """
    Get constituent list for a given index.
    
    Args:
        index_name: One of "NIFTY50", "BANKNIFTY", "SENSEX"
        cache_dir: Optional directory to cache constituent lists
        
    Returns:
        ConstituentList with tickers
        
    Raises:
        ValueError: If index_name is not recognized
    """
    index_name_upper = index_name.upper()
    
    # Check cache first
    if cache_dir:
        cache_file = cache_dir / f"constituents_{index_name_upper.lower()}.json"
        if cache_file.exists():
            try:
                data = json.loads(cache_file.read_text())
                return ConstituentList(
                    index_name=data["index_name"],
                    tickers=data["tickers"],
                    source=data.get("source", "cache"),
                    last_updated=data.get("last_updated")
                )
            except Exception:
                pass  # Fall back to manual list
    
    # Use manual lists (could be enhanced with NSE/BSE API calls in future)
    if index_name_upper == "NIFTY50":
        tickers = MANUAL_NIFTY50.copy()
    elif index_name_upper in ("BANKNIFTY", "BANKNIFTY50"):
        tickers = MANUAL_BANKNIFTY.copy()
    elif index_name_upper == "SENSEX":
        tickers = MANUAL_SENSEX.copy()
    else:
        raise ValueError(
            f"Unknown index: {index_name}. "
            f"Supported indices: NIFTY50, BANKNIFTY, SENSEX"
        )
    
    result = ConstituentList(
        index_name=index_name_upper,
        tickers=tickers,
        source="manual"
    )
    
    # Save to cache
    if cache_dir:
        cache_file = cache_dir / f"constituents_{index_name_upper.lower()}.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps({
            "index_name": result.index_name,
            "tickers": result.tickers,
            "source": result.source,
            "last_updated": result.last_updated
        }, indent=2))
    
    return result


def validate_tickers(tickers: list[str], strict: bool = False) -> tuple[list[str], list[str]]:
    """
    Validate ticker symbols format.
    
    Args:
        tickers: List of ticker symbols to validate
        strict: If True, only allow known formats (.NS, .BO, ^)
        
    Returns:
        Tuple of (valid_tickers, invalid_tickers)
    """
    valid = []
    invalid = []
    
    for ticker in tickers:
        ticker = ticker.strip()
        if not ticker:
            invalid.append(ticker)
            continue
        
        # Check format: should end with .NS, .BO, or start with ^
        is_valid = (
            ticker.endswith(".NS") or
            ticker.endswith(".BO") or
            ticker.startswith("^")
        )
        
        if strict and not is_valid:
            invalid.append(ticker)
        elif is_valid:
            valid.append(ticker)
        else:
            # Non-strict mode: allow any non-empty string (might be valid for other sources)
            valid.append(ticker)
    
    return valid, invalid


def load_constituents_from_file(file_path: Path) -> list[str]:
    """
    Load tickers from a universe file (one per line, comments with #).
    
    Args:
        file_path: Path to universe file
        
    Returns:
        List of ticker symbols
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Universe file not found: {file_path}")
    
    tickers = []
    for line in file_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tickers.append(line)
    
    return tickers
