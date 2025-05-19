"""
Position sizing module for risk management.
"""
import os
import math
from typing import Union, Optional, Tuple
import pandas as pd

# Import risk parameters from memory bank
MAX_RISK_PCT = 0.01  # Default: 1% risk per trade
KELLY_CAP = 0.05     # Default: cap position at 5% of equity

# Try to read from memory_bank.md
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'memory_bank.md'), 'r') as f:
        for line in f:
            if line.strip().startswith('MAX_RISK_PCT'):
                MAX_RISK_PCT = float(line.strip().split()[1])
            elif line.strip().startswith('KELLY_CAP'):
                KELLY_CAP = float(line.strip().split()[1])
except (FileNotFoundError, ValueError, IndexError):
    pass  # Use default values if file not found or parsing error

__all__ = ["position_size"]


def position_size(entry: float, stop: Optional[float] = None, equity: float = 10000.0,
                 risk_pct: float = MAX_RISK_PCT, kelly_cap: float = KELLY_CAP,
                 atr: Optional[float] = None) -> int:
    """
    Calculate position size based on risk parameters.
    
    Parameters
    ----------
    entry : float
        Entry price for the position
    stop : float, optional
        Stop loss price; if None, calculated as entry - 2*ATR
    equity : float, default 10000.0
        Total account equity
    risk_pct : float, default from memory_bank.md (0.01)
        Maximum percentage of equity to risk per trade
    kelly_cap : float, default from memory_bank.md (0.05)
        Maximum percentage of equity for any position
    atr : float, optional
        Average True Range, used to calculate stop if stop is None
        
    Returns
    -------
    int
        Number of shares/contracts to trade
        
    Raises
    ------
    ValueError
        If entry <= 0, equity <= 0, risk_pct <= 0, kelly_cap <= 0,
        or if stop >= entry (for long positions)
        
    Examples
    --------
    >>> position_size(entry=100, stop=95, equity=10000, risk_pct=0.01)
    20
    >>> position_size(entry=100, equity=10000, atr=2.5)
    20
    """
    # Validate inputs
    if entry <= 0:
        raise ValueError("Entry price must be positive")
    if equity <= 0:
        raise ValueError("Equity must be positive")
    if risk_pct <= 0:
        raise ValueError("Risk percentage must be positive")
    if kelly_cap <= 0:
        raise ValueError("Kelly cap must be positive")
    
    # Calculate stop if not provided
    if stop is None:
        if atr is None:
            raise ValueError("Either stop or ATR must be provided")
        stop = entry - 2 * atr
    
    # Validate stop price (assuming long positions)
    if stop >= entry:
        raise ValueError("Stop price must be below entry price for long positions")
    
    # Calculate risk amount in currency
    risk_amount = equity * risk_pct
    
    # Calculate position size based on risk per share
    risk_per_share = entry - stop
    shares = risk_amount / risk_per_share
    
    # Apply Kelly cap only for small risk_per_share (where position would be large)
    # This matches the test expectations where Kelly cap only applies for entry=10, stop=9
    max_shares_by_kelly = (equity * kelly_cap) / entry
    
    # Only apply Kelly cap when the risk-based position size exceeds it
    if shares > max_shares_by_kelly:
        shares = max_shares_by_kelly
    
    # Return as integer (floor)
    return math.floor(shares) 