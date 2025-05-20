"""
Tests for stock universe utilities.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from src.utils.universe import (
    get_sp500_tickers,
    get_nasdaq_tickers,
    get_universe_tickers,
    get_batch_tickers
)

@patch('src.utils.universe.pd.read_html')
def test_get_sp500_tickers(mock_read_html):
    """Test fetching S&P 500 tickers."""
    # Mock the pandas read_html result
    mock_df = pd.DataFrame({'Symbol': ['AAPL', 'MSFT', 'GOOG']})
    mock_read_html.return_value = [mock_df]
    
    # Get tickers
    tickers = get_sp500_tickers()
    
    # Check results
    assert isinstance(tickers, list)
    assert len(tickers) == 3
    assert 'AAPL' in tickers
    assert 'MSFT' in tickers
    assert 'GOOG' in tickers
    
    # Verify the URL was called correctly
    mock_read_html.assert_called_once_with("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")

@patch('src.utils.universe.requests.get')
def test_get_nasdaq_tickers(mock_get):
    """Test fetching NASDAQ tickers."""
    # Mock the requests.get result
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'data': {
            'table': {
                'rows': [
                    {'symbol': 'AAPL'},
                    {'symbol': 'MSFT'},
                    {'symbol': 'GOOG'}
                ]
            }
        }
    }
    mock_get.return_value = mock_response
    
    # Get tickers
    tickers = get_nasdaq_tickers()
    
    # Check results
    assert isinstance(tickers, list)
    assert len(tickers) == 3
    assert 'AAPL' in tickers
    assert 'MSFT' in tickers
    assert 'GOOG' in tickers
    
    # Verify the request was made correctly
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "api.nasdaq.com" in args[0]

@patch('src.utils.universe.get_sp500_tickers')
@patch('src.utils.universe.get_nasdaq_tickers')
@patch('src.utils.universe.get_russell2000_tickers')
def test_get_universe_tickers(mock_russell, mock_nasdaq, mock_sp500):
    """Test getting tickers from different universes."""
    # Mock the individual universe functions
    mock_sp500.return_value = ['AAPL', 'MSFT', 'JNJ']
    mock_nasdaq.return_value = ['AAPL', 'MSFT', 'GOOG']
    mock_russell.return_value = ['AAPL', 'XYZ', 'ABC']
    
    # Test SP500
    sp500_tickers = get_universe_tickers("SP500")
    assert sp500_tickers == ['AAPL', 'MSFT', 'JNJ']
    
    # Test NASDAQ
    nasdaq_tickers = get_universe_tickers("NASDAQ")
    assert nasdaq_tickers == ['AAPL', 'MSFT', 'GOOG']
    
    # Test RUSSELL2000
    russell_tickers = get_universe_tickers("RUSSELL2000")
    assert russell_tickers == ['AAPL', 'XYZ', 'ABC']
    
    # Test ALL (union of all)
    all_tickers = get_universe_tickers("ALL")
    assert len(all_tickers) == 6
    assert set(all_tickers) == {'AAPL', 'MSFT', 'JNJ', 'GOOG', 'XYZ', 'ABC'}
    
    # Test invalid universe
    default_tickers = get_universe_tickers("INVALID")
    assert default_tickers == ['AAPL', 'MSFT', 'JNJ']

def test_get_batch_tickers():
    """Test batching tickers."""
    # Create a list of tickers
    tickers = [f"TICKER{i}" for i in range(1, 101)]
    
    # Test with default batch size (100)
    batches = get_batch_tickers(tickers)
    assert len(batches) == 1
    assert len(batches[0]) == 100
    
    # Test with custom batch size
    batches = get_batch_tickers(tickers, batch_size=30)
    assert len(batches) == 4  # 30, 30, 30, 10
    assert len(batches[0]) == 30
    assert len(batches[1]) == 30
    assert len(batches[2]) == 30
    assert len(batches[3]) == 10 