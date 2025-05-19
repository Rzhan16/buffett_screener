"""
Core technical indicators module.
"""
import pandas as pd
import numpy as np
from typing import Union

__all__ = ["sma", "rsi", "atr"]


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Parameters
    ----------
    series : pd.Series
        Price series to calculate SMA on
    window : int
        Window size for SMA calculation
        
    Returns
    -------
    pd.Series
        Simple Moving Average series with NaNs dropped
        
    Raises
    ------
    ValueError
        If window is less than 1
        
    Examples
    --------
    >>> import pandas as pd
    >>> prices = pd.Series([10, 11, 12, 13, 14, 15])
    >>> sma(prices, 3)
    2    11.0
    3    12.0
    4    13.0
    5    14.0
    dtype: float64
    """
    if window < 1:
        raise ValueError("Window must be at least 1")
        
    result = series.rolling(window=window).mean()
    return result.dropna()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Parameters
    ----------
    series : pd.Series
        Price series to calculate RSI on
    window : int, default 14
        Window size for RSI calculation
        
    Returns
    -------
    pd.Series
        RSI series with NaNs dropped
        
    Raises
    ------
    ValueError
        If window is less than 1
        
    Examples
    --------
    >>> import pandas as pd
    >>> prices = pd.Series([10, 11, 10, 12, 11, 14, 15, 13, 14, 15, 16, 17, 18, 19, 20])
    >>> rsi_values = rsi(prices)
    >>> 0 <= rsi_values.min() and rsi_values.max() <= 100
    True
    """
    if window < 1:
        raise ValueError("Window must be at least 1")
        
    # Calculate price changes
    delta = series.diff()
    
    # Separate gains and losses
    gains = delta.copy()
    losses = delta.copy()
    gains[gains < 0] = 0
    losses[losses > 0] = 0
    losses = losses.abs()
    
    # Calculate average gains and losses
    avg_gain = gains.rolling(window=window).mean()
    avg_loss = losses.rolling(window=window).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values.dropna()


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Parameters
    ----------
    high : pd.Series
        High price series
    low : pd.Series
        Low price series
    close : pd.Series
        Close price series
    window : int, default 14
        Window size for ATR calculation
        
    Returns
    -------
    pd.Series
        ATR series with NaNs dropped and aligned to close.index
        
    Raises
    ------
    ValueError
        If window is less than 1
        
    Examples
    --------
    >>> import pandas as pd
    >>> high = pd.Series([11, 12, 13, 14, 15, 16])
    >>> low = pd.Series([9, 10, 11, 12, 13, 14])
    >>> close = pd.Series([10, 11, 12, 13, 14, 15])
    >>> atr_values = atr(high, low, close, window=3)
    >>> (atr_values >= 0).all()
    True
    """
    if window < 1:
        raise ValueError("Window must be at least 1")
        
    # Calculate True Range
    previous_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - previous_close).abs()
    tr3 = (low - previous_close).abs()
    
    # True Range is the maximum of the three
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate Average True Range
    atr_values = tr.rolling(window=window).mean()
    
    return atr_values.dropna() 