"""
Tests for fundamental analysis and FinGPT explanations.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from src.llm.embeddings import fetch_fundamentals, explain_with_fingpt

# Mock data
@pytest.fixture
def mock_ticker_info():
    return {
        'trailingPE': 25.5,
        'priceToBook': 3.2,
        'priceToSalesTrailing12Months': 4.5,
        'enterpriseToEbitda': 15.8,
        'profitMargins': 0.25,
        'operatingMargins': 0.30,
        'currentRatio': 1.5,
        'quickRatio': 1.2,
        'debtToEquity': 45.0,
        'dividendYield': 0.02,
        'payoutRatio': 0.35,
        'marketCap': 1000000000,
        'beta': 1.2
    }

@pytest.fixture
def mock_income_stmt():
    # Create mock income statement with 2 years of data
    data = {
        'Total Revenue': [110000000, 100000000],
        'Net Income': [25000000, 20000000],
        'Basic EPS': [2.2, 2.0]
    }
    df = pd.DataFrame(data, index=['2023', '2022'])
    return df.T  # Transpose to match yfinance format

@pytest.fixture
def mock_balance_sheet():
    # Create mock balance sheet with 2 years of data
    data = {
        'Total Assets': [500000000, 450000000],
        'Total Stockholder Equity': [250000000, 230000000]
    }
    df = pd.DataFrame(data, index=['2023', '2022'])
    return df.T  # Transpose to match yfinance format

@pytest.fixture
def mock_cash_flow():
    # Create mock cash flow statement with 2 years of data
    data = {
        'Operating Cash Flow': [40000000, 35000000],
        'Capital Expenditure': [-15000000, -12000000]
    }
    df = pd.DataFrame(data, index=['2023', '2022'])
    return df.T  # Transpose to match yfinance format

def test_fetch_fundamentals(mock_ticker_info, mock_income_stmt, mock_balance_sheet, mock_cash_flow):
    """Test fetching and calculating fundamental metrics."""
    with patch('yfinance.Ticker') as mock_yf:
        # Setup mock
        instance = mock_yf.return_value
        instance.info = mock_ticker_info
        instance.income_stmt = mock_income_stmt
        instance.balance_sheet = mock_balance_sheet
        instance.cashflow = mock_cash_flow
        
        # Call function
        fundamentals = fetch_fundamentals('AAPL')
        
        # Verify basic metrics
        assert fundamentals['pe_ratio'] == 25.5
        assert fundamentals['pb_ratio'] == 3.2
        assert fundamentals['dividend_yield'] == 2.0
        
        # Verify calculated metrics
        assert abs(fundamentals['revenue_growth'] - 10.0) < 1e-10
        assert abs(fundamentals['eps_growth'] - 10.0) < 1e-10
        assert abs(fundamentals['roe'] - 10.0) < 1e-10
        assert abs(fundamentals['roa'] - 5.0) < 1e-10
        
        # Verify FCF growth calculation
        expected_fcf_growth = ((40000000 - 15000000) / (35000000 - 12000000) - 1) * 100
        assert abs(fundamentals['fcf_growth'] - expected_fcf_growth) < 1e-10

def test_fetch_fundamentals_error_handling():
    """Test error handling in fetch_fundamentals."""
    with patch('yfinance.Ticker', side_effect=Exception("API Error")):
        # Call function - should not raise an exception
        fundamentals = fetch_fundamentals('AAPL')
        
        # Verify default values are returned
        assert fundamentals['pe_ratio'] == 'N/A'
        assert fundamentals['revenue_growth'] == 'N/A'
        assert fundamentals['dividend_yield'] == 'N/A'

@patch('src.llm.embeddings.load_model')
@patch('src.llm.embeddings.tokenizer')
@patch('src.llm.embeddings.model')
@patch('src.llm.embeddings.fetch_fundamentals')
def test_explain_with_fingpt(mock_fetch, mock_model, mock_tokenizer, mock_load_model):
    """Test generating explanations with FinGPT."""
    # Setup mocks
    mock_fetch.return_value = {
        'pe_ratio': 25.5,
        'pb_ratio': 3.2,
        'ps_ratio': 4.5,
        'ev_to_ebitda': 15.8,
        'profit_margin': 0.25,
        'operating_margin': 0.30,
        'roe': 10.0,
        'roa': 5.0,
        'revenue_growth': 10.0,
        'eps_growth': 10.0,
        'fcf_growth': 8.5,
        'current_ratio': 1.5,
        'quick_ratio': 1.2,
        'debt_to_equity': 45.0,
        'dividend_yield': 2.0,
        'payout_ratio': 0.35,
        'market_cap': 1000000000,
        'beta': 1.2
    }
    
    mock_tokenizer.return_value = MagicMock()
    mock_model.generate.return_value = [MagicMock()]
    mock_tokenizer.decode.return_value = "This is a test explanation for AAPL stock."
    
    # Call function
    explanation = explain_with_fingpt('AAPL')
    
    # Verify
    assert explanation == "This is a test explanation for AAPL stock."
    assert mock_fetch.called
    assert mock_load_model.called 