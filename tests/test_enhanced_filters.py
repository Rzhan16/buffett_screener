"""
Tests for the enhanced screener filters.
"""
import os
import pytest
from unittest.mock import Mock, patch
import pandas as pd
import numpy as np

from src.screener.enhanced_filters import EnhancedScreener


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return {
        'api': {
            'fmp': {'base_url': 'https://test.fmp.com', 'cache_ttl': 3600},
            'yahoo': {'base_url': 'https://test.yahoo.com', 'cache_ttl': 3600}
        },
        'quality': {
            'piotroski': {
                'operating_cash_flow': True,
                'roa_increasing': True,
                'debt_to_assets_decreasing': True,
                'current_ratio_increasing': True
            },
            'accruals': {'max_ratio': 0.1},
            'f_score': {'min_score': 7}
        },
        'earnings': {
            'consistency': {
                'min_positive_years': 3,
                'max_negative_surprises': 0
            },
            'revenue': {
                'min_growth': 0,
                'max_gross_margin_std': 0.05
            }
        },
        'financial': {
            'debt': {
                'min_interest_coverage': 3.0,
                'max_debt_to_equity': 1.5,
                'min_free_cash_flow_yield': 0.04
            },
            'dividend': {
                'max_payout_ratio': 0.60,
                'min_growth_rate': 0
            }
        },
        'technical': {
            'trend': {
                'min_adx': 25,
                'max_rsi': 70
            },
            'support_resistance': {
                'min_ma20': True,
                'max_std_dev': 2.0
            }
        },
        'risk': {
            'volatility': {
                'max_beta': 1.5,
                'max_volatility_vs_sector': 1.0
            },
            'liquidity': {
                'min_market_cap': 1000000000,
                'min_avg_volume': 100000
            }
        },
        'output': {
            'format': 'json',
            'fields': ['symbol', 'name', 'price', 'f_score'],
            'sort_by': 'f_score',
            'sort_order': 'desc',
            'max_results': 50
        }
    }


@pytest.fixture
def mock_fmp_client():
    """Create a mock FMP client."""
    client = Mock()
    
    # Mock financial data
    client.get_financials.return_value = {
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'price': 150.0,
        'f_score': 8,
        'eps_growth': [0.1, 0.15, 0.2],
        'earnings_surprises': [0.02, 0.01, 0.03, 0.02],
        'revenue_growth': 0.1,
        'gross_margins': [0.4, 0.41, 0.39, 0.42],
        'interest_coverage': 5.0,
        'debt_to_equity': 1.0,
        'free_cash_flow_yield': 0.05,
        'dividend_yield': 0.02,
        'payout_ratio': 0.3,
        'dividend_growth_5y': 0.1
    }
    
    # Mock risk metrics
    client.get_risk_metrics.return_value = {
        'beta': 1.2,
        'volatility_vs_sector': 0.8,
        'market_cap': 2000000000000,
        'avg_volume': 50000000
    }
    
    return client


@pytest.fixture
def mock_yahoo_client():
    """Create a mock Yahoo client."""
    client = Mock()
    
    # Mock technical data
    client.get_technicals.return_value = {
        'adx': 30,
        'rsi': 60,
        'price_above_ma20': True,
        'price_std_dev': 1.5
    }
    
    return client


@pytest.fixture
def screener(mock_config):
    """Create a screener instance with mocked configuration."""
    with patch('src.screener.enhanced_filters.EnhancedScreener._load_config', return_value=mock_config):
        return EnhancedScreener('dummy_config.yaml')


def test_enhanced_screener_initialization(screener, mock_config):
    """Test screener initialization with configuration."""
    assert screener.config == mock_config


def test_calculate_accruals_ratio(screener):
    """Test accruals ratio calculation."""
    # Test normal case
    ratio = screener._calculate_accruals_ratio(100, 80, 1000)
    assert ratio == 0.02
    
    # Test zero total assets
    ratio = screener._calculate_accruals_ratio(100, 80, 0)
    assert ratio == float('inf')


def test_calculate_industry_cagr(screener):
    """Test industry CAGR calculation."""
    # Test normal case
    revenues = pd.Series([100, 110, 121])
    cagr = screener._calculate_industry_cagr(revenues)
    assert abs(cagr - 0.1) < 0.0001
    
    # Test two points (should be valid)
    revenues = pd.Series([100, 110])
    cagr = screener._calculate_industry_cagr(revenues)
    assert abs(cagr - 0.1) < 0.0001
    
    # Test insufficient data (one point)
    revenues = pd.Series([100])
    cagr = screener._calculate_industry_cagr(revenues)
    assert cagr == float('-inf')


def test_calculate_relative_strength(screener):
    """Test relative strength calculation."""
    # Test normal case
    stock_returns = pd.Series([0.1, 0.2, 0.3])
    sector_returns = pd.Series([0.05, 0.1, 0.15])
    rs = screener._calculate_relative_strength(stock_returns, sector_returns)
    assert rs > 0


def test_check_earnings_quality(screener):
    """Test earnings quality checks."""
    # Test passing case
    financials = {
        'eps_growth': [0.1, 0.15, 0.2],
        'earnings_surprises': [0.02, 0.01, 0.03, 0.02],
        'revenue_growth': 0.1,
        'gross_margins': [0.4, 0.41, 0.39, 0.42]
    }
    assert screener._check_earnings_quality(financials)
    
    # Test failing cases
    financials['eps_growth'] = [0.1, -0.15, 0.2]
    assert not screener._check_earnings_quality(financials)
    
    financials['eps_growth'] = [0.1, 0.15, 0.2]
    financials['earnings_surprises'] = [0.02, -0.01, 0.03, 0.02]
    assert not screener._check_earnings_quality(financials)


def test_check_financial_health(screener):
    """Test financial health checks."""
    # Test passing case
    financials = {
        'interest_coverage': 5.0,
        'debt_to_equity': 1.0,
        'free_cash_flow_yield': 0.05,
        'dividend_yield': 0.02,
        'payout_ratio': 0.3,
        'dividend_growth_5y': 0.1
    }
    assert screener._check_financial_health(financials)
    
    # Test failing cases
    financials['interest_coverage'] = 2.0
    assert not screener._check_financial_health(financials)
    
    financials['interest_coverage'] = 5.0
    financials['debt_to_equity'] = 2.0
    assert not screener._check_financial_health(financials)


def test_check_technical_indicators(screener):
    """Test technical indicator checks."""
    # Test passing case
    technicals = {
        'adx': 30,
        'rsi': 60,
        'price_above_ma20': True,
        'price_std_dev': 1.5
    }
    assert screener._check_technical_indicators(technicals)
    
    # Test failing cases
    technicals['adx'] = 20
    assert not screener._check_technical_indicators(technicals)
    
    technicals['adx'] = 30
    technicals['rsi'] = 75
    assert not screener._check_technical_indicators(technicals)


def test_check_risk_metrics(screener):
    """Test risk metric checks."""
    # Test passing case
    risk_metrics = {
        'beta': 1.2,
        'volatility_vs_sector': 0.8,
        'market_cap': 2000000000000,
        'avg_volume': 50000000
    }
    assert screener._check_risk_metrics(risk_metrics)
    
    # Test failing cases
    risk_metrics['beta'] = 2.0
    assert not screener._check_risk_metrics(risk_metrics)
    
    risk_metrics['beta'] = 1.2
    risk_metrics['market_cap'] = 500000000
    assert not screener._check_risk_metrics(risk_metrics)


def test_screen_stock(screener, mock_fmp_client, mock_yahoo_client):
    """Test screening a single stock."""
    screener.fmp_client = mock_fmp_client
    screener.yahoo_client = mock_yahoo_client
    
    # Test passing case
    result = screener.screen_stock('AAPL')
    assert result is not None
    assert result['symbol'] == 'AAPL'
    
    # Test failing case (modify mock data to fail)
    mock_fmp_client.get_financials.return_value['eps_growth'] = [0.1, -0.15, 0.2]
    result = screener.screen_stock('AAPL')
    assert result is None


def test_screen_universe(screener, mock_fmp_client, mock_yahoo_client):
    """Test screening a universe of stocks."""
    screener.fmp_client = mock_fmp_client
    screener.yahoo_client = mock_yahoo_client
    
    # Test with multiple stocks
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    results = screener.screen_universe(symbols)
    
    assert len(results) > 0
    assert all(isinstance(r, dict) for r in results)
    assert all('symbol' in r for r in results)


def test_format_output(screener):
    """Test output formatting."""
    # Test JSON output
    results = [{
        'symbol': 'AAPL',
        'financials': {'name': 'Apple Inc.', 'price': 150.0, 'f_score': 8},
        'technicals': {},
        'risk_metrics': {}
    }]
    
    formatted = screener.format_output(results)
    assert isinstance(formatted, list)
    assert len(formatted) == 1
    assert formatted[0]['symbol'] == 'AAPL'
    
    # Test CSV output
    screener.config['output']['format'] = 'csv'
    formatted = screener.format_output(results)
    assert isinstance(formatted, str)
    assert 'symbol,name,price,f_score' in formatted 