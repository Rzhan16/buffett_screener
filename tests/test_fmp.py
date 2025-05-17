"""
Tests for FMP API client functionality.
"""
import os
import pytest
import json
from unittest.mock import patch, Mock, call

from src.data.fmp import fetch_fundamentals


@pytest.fixture
def mock_env_api_key():
    """Set mock API key for testing."""
    with patch.dict(os.environ, {"FMP_KEY": "test_api_key"}):
        yield


def test_fetch_fundamentals_success(mock_env_api_key, monkeypatch):
    """Test successful API response for AAPL."""
    # Mock successful API response
    mock_data = [
        {
            "symbol": "AAPL",
            "date": "2023-09-30",
            "period": "FY",
            "currentRatio": 0.98,
            "quickRatio": 0.85,
            "cashRatio": 0.21,
            "grossProfitMargin": 0.45,
            "operatingProfitMargin": 0.33,
            "netProfitMargin": 0.25,
            "returnOnAssets": 0.28,
            "returnOnEquity": 1.56,
            "debtRatio": 0.70,
            "debtEquityRatio": 2.45,
            "priceEarningsRatio": 30.03
        }
    ]
    
    # Create mock response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    
    # Mock requests.get
    with patch('requests.get', return_value=mock_response):
        with patch('requests_cache.install_cache'):  # Mock the cache installation
            result = fetch_fundamentals("AAPL")
            
    assert result == mock_data
    assert result[0]["symbol"] == "AAPL"
    assert "grossProfitMargin" in result[0]


def test_fetch_fundamentals_invalid_ticker(mock_env_api_key):
    """Test error handling for invalid ticker."""
    # Mock empty response for invalid ticker
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = []
    
    with patch('requests.get', return_value=mock_response):
        with patch('requests_cache.install_cache'):
            with pytest.raises(RuntimeError, match="No data found for ticker: INVALID"):
                fetch_fundamentals("INVALID")


def test_fetch_fundamentals_rate_limit(mock_env_api_key):
    """Test rate limit handling with retries."""
    # Create mocks for rate limited and successful responses
    rate_limited_response = Mock()
    rate_limited_response.status_code = 429
    
    success_response = Mock()
    success_response.status_code = 200
    success_response.json.return_value = [{"symbol": "AAPL", "date": "2023-09-30"}]
    
    # Set up the requests.get mock to return rate limited responses first, then success
    mock_get = Mock(side_effect=[rate_limited_response, rate_limited_response, success_response])
    
    with patch('requests.get', mock_get):
        with patch('requests_cache.install_cache'):
            with patch('time.sleep') as mock_sleep:
                result = fetch_fundamentals("AAPL")
                
                # Verify sleep was called twice
                assert mock_sleep.call_count == 2
                
                # Verify the result
                assert result == [{"symbol": "AAPL", "date": "2023-09-30"}]


def test_fetch_fundamentals_rate_limit_exceeded(mock_env_api_key):
    """Test error when rate limit is exceeded after max retries."""
    # Create mocks for the rate limited responses
    rate_limited_response1 = Mock()
    rate_limited_response1.status_code = 429
    
    rate_limited_response2 = Mock()
    rate_limited_response2.status_code = 429
    
    # The last one will trigger the exception
    rate_limited_response3 = Mock()
    rate_limited_response3.status_code = 429
    
    # Set up the side effect sequence
    mock_get = Mock(side_effect=[
        rate_limited_response1,
        rate_limited_response2,
        rate_limited_response3
    ])
    
    with patch('requests.get', mock_get):
        with patch('requests_cache.install_cache'):
            with patch('time.sleep') as mock_sleep:
                # The error is raised on the 3rd retry (when retry_count == max_retries)
                with pytest.raises(RuntimeError, match="Rate limit exceeded after 3 retries"):
                    fetch_fundamentals("AAPL")
                
                # Only 2 sleeps happen because the 3rd attempt raises the exception
                # before sleeping again
                assert mock_sleep.call_count == 2


def test_missing_api_key():
    """Test error when API key is not set."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(RuntimeError, match="FMP_KEY environment variable not set"):
            fetch_fundamentals("AAPL") 