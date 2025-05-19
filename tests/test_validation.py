"""
Tests for strategy validation module.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.validation.backtest import StrategyValidator

# Mock data
MOCK_PRICE_DATA = pd.DataFrame({
    'Close': [100, 110, 105, 115, 120],
    'High': [105, 115, 110, 120, 125],
    'Low': [95, 105, 100, 110, 115],
    'Volume': [1000] * 5
}, index=pd.date_range(start='2023-01-01', periods=5))

MOCK_FUNDAMENTALS = {
    'pe_ratio': 15.0,
    'pb_ratio': 2.0,
    'dividend_yield': 2.5,
    'debt_to_equity': 0.5
}

@pytest.fixture
def mock_config():
    return {
        'strategy': 'long_term',
        'filters': {
            'f_score': 7,
            'sma_200': True
        }
    }

@pytest.fixture
def validator(mock_config):
    return StrategyValidator(mock_config)

def test_fetch_historical_data(validator):
    """Test historical data fetching."""
    with patch('yfinance.download', return_value=MOCK_PRICE_DATA):
        data = validator.fetch_historical_data('AAPL', '2023-01-01', '2023-01-05')
        assert not data.empty
        assert len(data) == 5
        assert 'Close' in data.columns

def test_calculate_returns(validator):
    """Test return calculations."""
    total_return, annualized_return, sharpe = validator.calculate_returns(MOCK_PRICE_DATA)
    assert abs(total_return - 20.0) < 1e-10  # Use small epsilon for float comparison
    assert isinstance(annualized_return, float)
    assert isinstance(sharpe, float)

def test_calculate_drawdown(validator):
    """Test drawdown calculation."""
    drawdown = validator.calculate_drawdown(MOCK_PRICE_DATA)
    assert isinstance(drawdown, float)
    assert drawdown <= 0  # Drawdown should be negative

@patch('src.llm.embeddings.fetch_fundamentals')
@patch('src.scoring.buffett.get_f_score')
@patch('src.technical.core.get_sma')
def test_validate_strategy(mock_get_sma, mock_get_f_score, mock_fetch_fundamentals, validator):
    """Test strategy validation."""
    # Setup mocks
    mock_fetch_fundamentals.return_value = MOCK_FUNDAMENTALS
    mock_get_f_score.return_value = pd.DataFrame({
        'score': [8],
        'close': [100],
        'atr': [2]
    }, index=['AAPL'])
    mock_get_sma.return_value = pd.DataFrame({
        'close': [100],
        'sma_200': [90]
    }, index=['AAPL'])
    
    with patch('yfinance.download', return_value=MOCK_PRICE_DATA):
        results = validator.validate_strategy(['AAPL'], '2023-01-01', '2023-01-05')
        assert not results.empty
        assert 'symbol' in results.columns
        assert 'total_return' in results.columns
        assert 'f_score' in results.columns
        assert 'pe_ratio' in results.columns

def test_analyze_market_conditions(validator):
    """Test market condition analysis."""
    conditions = validator.analyze_market_conditions(MOCK_PRICE_DATA)
    assert 'volatility' in conditions
    assert 'trend' in conditions
    assert 'regime' in conditions
    assert isinstance(conditions['volatility'], float)
    assert conditions['trend'] in ['bullish', 'bearish']
    assert conditions['regime'] in ['high_volatility', 'low_volatility']

@patch('src.validation.backtest.StrategyValidator.validate_strategy')
@patch('src.validation.backtest.StrategyValidator.analyze_market_conditions')
def test_run_validation(mock_analyze_conditions, mock_validate_strategy, validator):
    """Test full validation run."""
    # Setup mocks
    mock_validate_strategy.return_value = pd.DataFrame({
        'symbol': ['AAPL'],
        'total_return': [20.0],
        'annualized_return': [0.15],
        'sharpe_ratio': [1.5],
        'max_drawdown': [-10.0],
        'f_score': [8],
        'sma_200': [90],
        'pe_ratio': [15.0],
        'pb_ratio': [2.0],
        'dividend_yield': [2.5],
        'debt_to_equity': [0.5]
    })
    mock_analyze_conditions.return_value = {
        'volatility': 15.0,
        'trend': 'bullish',
        'regime': 'low_volatility'
    }
    
    results = validator.run_validation(['AAPL'], '2023-01-01', '2023-01-05')
    assert 'results' in results
    assert 'aggregate_metrics' in results
    assert 'avg_return' in results['aggregate_metrics']
    assert 'market_conditions' in results['aggregate_metrics'] 