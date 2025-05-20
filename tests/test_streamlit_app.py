"""
Test file for Streamlit application functionality.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock

# Import from app/main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.main import (
    get_stocks_data,
    calculate_position_sizes,
    parse_custom_tickers,
    format_large_number,
    get_stock_chart
)

def test_parse_custom_tickers():
    """Test parsing custom ticker inputs"""
    # Test comma separated
    tickers = parse_custom_tickers("AAPL, MSFT, GOOG")
    assert tickers == ["AAPL", "MSFT", "GOOG"]
    
    # Test space separated
    tickers = parse_custom_tickers("AAPL MSFT GOOG")
    assert tickers == ["AAPL", "MSFT", "GOOG"]
    
    # Test mixed separators
    tickers = parse_custom_tickers("AAPL, MSFT GOOG,AMD")
    assert tickers == ["AAPL", "MSFT", "GOOG", "AMD"]
    
    # Test empty input
    tickers = parse_custom_tickers("")
    assert tickers == []
    
    # Test with whitespace
    tickers = parse_custom_tickers("  AAPL  ,  MSFT  ")
    assert tickers == ["AAPL", "MSFT"]

def test_format_large_number():
    """Test formatting large numbers with suffixes"""
    # Test billions
    assert format_large_number(1_000_000_000) == "$1.00B"
    assert format_large_number(2_500_000_000) == "$2.50B"
    
    # Test millions
    assert format_large_number(1_000_000) == "$1.00M"
    assert format_large_number(2_500_000) == "$2.50M"
    
    # Test thousands
    assert format_large_number(1_000) == "$1.00K"
    assert format_large_number(2_500) == "$2.50K"
    
    # Test small numbers
    assert format_large_number(100) == "$100.00"
    assert format_large_number(25.5) == "$25.50"
    
    # Test None and NaN
    assert format_large_number(None) == "N/A"
    assert format_large_number(np.nan) == "N/A"

@patch('app.main.get_f_score')
def test_calculate_position_sizes(mock_get_f_score):
    """Test calculation of position sizes"""
    # Create mock dataframe
    stocks_df = pd.DataFrame({
        'close': [100, 50, 200],
        'atr': [2, 1, 4]
    }, index=['AAPL', 'MSFT', 'AMZN'])
    
    # Calculate positions with 10,000 buying power and 1% risk
    positions = calculate_position_sizes(stocks_df, 10000, 0.01)
    
    # Check results
    assert 'AAPL' in positions
    assert 'MSFT' in positions
    assert 'AMZN' in positions
    
    # AAPL: $100 price, $2 ATR, $10,000 * 0.01 = $100 risk
    # Risk per share = $2 ATR * 2 = $4
    # Position size = $100 / $4 * $100 = $2,500
    # Shares = $2,500 / $100 = 25
    assert positions['AAPL']['shares'] == 25
    assert positions['AAPL']['dollars'] == 2500.0
    assert positions['AAPL']['percentage'] == 25.0
    
    # Test with zero price (should handle division by zero)
    stocks_df.loc['ZERO', 'close'] = 0
    stocks_df.loc['ZERO', 'atr'] = 1
    positions = calculate_position_sizes(stocks_df, 10000, 0.01)
    assert positions['ZERO']['shares'] == 0

@patch('app.main.yf.Ticker')
@patch('app.main.plt')
def test_get_stock_chart(mock_plt, mock_ticker):
    """Test stock chart generation"""
    # Mock the ticker and history data
    mock_ticker_instance = MagicMock()
    mock_hist = pd.DataFrame({
        'Open': [100, 101, 102],
        'High': [105, 106, 107],
        'Low': [98, 99, 100],
        'Close': [103, 104, 105]
    }, index=pd.date_range('2023-01-01', periods=3))
    mock_ticker_instance.history.return_value = mock_hist
    mock_ticker.return_value = mock_ticker_instance
    
    # Mock the plot and figure
    mock_fig = MagicMock()
    mock_plt.subplots.return_value = (mock_fig, MagicMock())
    
    # Test the function
    result = get_stock_chart('AAPL')
    
    # Verify ticker was called correctly
    mock_ticker.assert_called_once_with('AAPL')
    mock_ticker_instance.history.assert_called_once_with(period='6mo')
    
    # Verify result is a string (base64 encoded image)
    assert isinstance(result, str)
    
    # Test empty history
    mock_ticker_instance.history.return_value = pd.DataFrame()
    result = get_stock_chart('EMPTY')
    assert result is None 