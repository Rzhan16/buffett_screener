"""
Tests for Buffett scoring module.
"""
import os
import pytest
import json
import sqlite3
from unittest.mock import patch, Mock
from datetime import date

from src.scoring.buffett import get_score, F_SCORE_THRESHOLD


def test_get_score_aapl():
    """Test that AAPL gets a score greater than 5."""
    # Mock Fundamental to return a high score for AAPL
    mock_fundamental = Mock()
    mock_fundamental.score.return_value = {
        'overall_score': 8.0,
        'profitability_score': 4,
        'leverage_score': 2,
        'operating_efficiency_score': 2,
        'positive_net_income': True,
        'positive_operating_cashflow': True,
        'higher_roa': True,
        'cashflow_greater_than_income': True,
        'lower_leverage_ratio': True,
        'higher_current_ratio': True,
        'no_dilution': False,
        'higher_gross_margin': True,
        'higher_asset_turnover': True
    }
    
    # Mock environment and cache
    with patch('os.environ.get', return_value='dummy_api_key'):
        with patch('src.scoring.buffett._get_from_cache', return_value=None):
            with patch('src.scoring.buffett._create_fundamental_analyzer', return_value=mock_fundamental) as mock_create:
                with patch('src.scoring.buffett._cache_result'):
                    score, details = get_score('AAPL')
    
    # Check that score is a float
    assert isinstance(score, float)
    
    # Check that AAPL score is greater than 5
    assert score > 5.0
    
    # Check that details contains component scores
    assert 'profitability' in details
    assert 'leverage' in details
    assert 'operating_efficiency' in details
    assert 'components' in details
    
    # Verify that _create_fundamental_analyzer was called with the right parameters
    mock_create.assert_called_once_with('AAPL', 'dummy_api_key')


def test_get_score_from_cache():
    """Test retrieving a score from cache."""
    # Mock the cache retrieval
    mock_cached_result = (8.0, {
        'profitability': 3,
        'leverage': 3,
        'operating_efficiency': 2,
        'components': {
            'positive_net_income': True,
            'positive_operating_cashflow': True,
            'higher_roa': True,
            'cashflow_greater_than_income': True,
            'lower_leverage_ratio': True,
            'higher_current_ratio': True,
            'no_dilution': True,
            'higher_gross_margin': True,
            'higher_asset_turnover': False
        }
    })
    
    with patch('src.scoring.buffett._get_from_cache', return_value=mock_cached_result):
        # The function should return the cached result without calling Fundamental
        with patch('src.scoring.buffett._create_fundamental_analyzer') as mock_create:
            score, details = get_score('AAPL')
            
            # Check that _create_fundamental_analyzer was not called
            mock_create.assert_not_called()
            
            # Check that we got the cached result
            assert score == 8.0
            assert details['profitability'] == 3


def test_get_score_penny_stock():
    """Test that a penny stock gets a low score (less than 3)."""
    # Mock Fundamental to return a low score for a penny stock
    mock_fundamental = Mock()
    mock_fundamental.score.return_value = {
        'overall_score': 2.0,
        'profitability_score': 1,
        'leverage_score': 0,
        'operating_efficiency_score': 1,
        'positive_net_income': False,
        'positive_operating_cashflow': True,
        'higher_roa': False,
        'cashflow_greater_than_income': False,
        'lower_leverage_ratio': False,
        'higher_current_ratio': False,
        'no_dilution': False,
        'higher_gross_margin': True,
        'higher_asset_turnover': False
    }
    
    # Mock environment and cache
    with patch('os.environ.get', return_value='dummy_api_key'):
        with patch('src.scoring.buffett._get_from_cache', return_value=None):
            with patch('src.scoring.buffett._create_fundamental_analyzer', return_value=mock_fundamental):
                with patch('src.scoring.buffett._cache_result'):
                    score, details = get_score('SNDL')
    
    # Check that score is a float
    assert isinstance(score, float)
    
    # Check that penny stock score is less than 3
    assert score < 3.0


def test_get_score_error_handling():
    """Test error handling when valinvest raises an exception."""
    # Mock _create_fundamental_analyzer to raise an exception
    mock_create = Mock(side_effect=Exception("API Error"))
    
    with patch('os.environ.get', return_value='dummy_api_key'):
        with patch('src.scoring.buffett._get_from_cache', return_value=None):
            with patch('src.scoring.buffett._create_fundamental_analyzer', mock_create):
                # Check that RuntimeError is raised
                with pytest.raises(RuntimeError, match="Error calculating F-score for INVALID: API Error"):
                    get_score('INVALID')


def test_f_score_threshold():
    """Test that F_SCORE_THRESHOLD is properly set."""
    # The threshold should be an integer
    assert isinstance(F_SCORE_THRESHOLD, int)
    
    # The threshold should be between 0 and 9 (max F-score)
    assert 0 <= F_SCORE_THRESHOLD <= 9


def test_cache_operations():
    """Test cache initialization and operations."""
    # Mock data for the test
    ticker = 'TEST'
    score = 7.0
    details = {
        'profitability': 3,
        'leverage': 2,
        'operating_efficiency': 2,
        'components': {
            'positive_net_income': True,
            'positive_operating_cashflow': True,
            'higher_roa': True,
            'cashflow_greater_than_income': False,
            'lower_leverage_ratio': True,
            'higher_current_ratio': True,
            'no_dilution': False,
            'higher_gross_margin': True,
            'higher_asset_turnover': True
        }
    }
    today = date.today().isoformat()
    
    # Mock the database connection and cursor
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    
    # Mock the fetchone method to return our test data
    mock_cursor.fetchone.return_value = (score, json.dumps(details))
    
    # Test the cache functions
    with patch('sqlite3.connect', return_value=mock_conn):
        from src.scoring.buffett import _get_from_cache, _init_cache, _cache_result
        
        # Initialize the cache
        _init_cache()
        
        # Test that _get_from_cache works
        cached_result = _get_from_cache(ticker)
        
        # Verify the connection was used correctly
        assert mock_conn.cursor.call_count >= 1
        assert mock_cursor.execute.call_count >= 1
        
        # Check the result
        assert cached_result is not None
        cached_score, cached_details = cached_result
        assert cached_score == score
        assert cached_details['profitability'] == details['profitability']
        
        # Test that _cache_result works
        _cache_result(ticker, score, details)
        
        # Verify commit and close were called
        assert mock_conn.commit.call_count >= 1
        assert mock_conn.close.call_count >= 1 