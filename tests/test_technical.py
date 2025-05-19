"""
Tests for technical indicators module.
"""
import pytest
import pandas as pd
import numpy as np
from src.technical.core import sma, rsi, atr


def test_sma_matches_pandas_rolling():
    """Test that our SMA function matches pandas rolling mean."""
    # Create test data
    data = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
    
    # Calculate SMA using our function
    sma_result = sma(data, window=5)
    
    # Calculate SMA using pandas rolling
    pandas_result = data.rolling(window=5).mean().dropna()
    
    # Check that results match
    pd.testing.assert_series_equal(sma_result, pandas_result)


def test_rsi_range_is_0_100():
    """Test that RSI values are always between 0 and 100."""
    # Create test data with both up and down movements
    data = pd.Series([10, 11, 10, 12, 11, 14, 15, 13, 14, 15, 16, 17, 18, 19, 20])
    
    # Calculate RSI
    rsi_result = rsi(data)
    
    # Check that all values are between 0 and 100
    assert rsi_result.min() >= 0
    assert rsi_result.max() <= 100


def test_atr_nonnegative():
    """Test that ATR values are always non-negative."""
    # Create test data
    high = pd.Series([11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
    low = pd.Series([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23])
    close = pd.Series([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24])
    
    # Calculate ATR
    atr_result = atr(high, low, close)
    
    # Check that all values are non-negative
    assert (atr_result >= 0).all()


def test_invalid_window_raises():
    """Test that invalid window sizes raise ValueError."""
    data = pd.Series([10, 11, 12, 13, 14])
    high = pd.Series([11, 12, 13, 14, 15])
    low = pd.Series([9, 10, 11, 12, 13])
    close = pd.Series([10, 11, 12, 13, 14])
    
    # Test SMA with invalid window
    with pytest.raises(ValueError):
        sma(data, window=0)
    
    # Test RSI with invalid window
    with pytest.raises(ValueError):
        rsi(data, window=0)
    
    # Test ATR with invalid window
    with pytest.raises(ValueError):
        atr(high, low, close, window=0) 