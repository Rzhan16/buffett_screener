"""
Tests for the embeddings utility module.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.utils.embeddings import (
    get_llm,
    embed,
    search_similar,
    init_collection,
    clear_collection,
    EMBEDDING_DIM
)
from src.llm.embeddings import fetch_fundamentals, explain_with_fingpt
import pandas as pd

@pytest.fixture
def mock_tokenizer():
    """Create a mock tokenizer."""
    tokenizer = Mock()
    def call(text, return_tensors=None, padding=None, truncation=None, max_length=None):
        return {'input_ids': [[1, 2, 3]], 'attention_mask': [[1, 1, 1]]}
    tokenizer.side_effect = call
    return tokenizer

@pytest.fixture
def mock_model():
    """Create a mock model that returns a mock output with last_hidden_state supporting slicing and .numpy()."""
    # Create a mock output with last_hidden_state supporting slicing and .numpy()
    class FakeTensor:
        def __init__(self, arr):
            self._arr = arr
        def __getitem__(self, idx):
            # Support slicing: outputs.last_hidden_state[:, 0, :]
            return FakeTensor(self._arr[idx]) if isinstance(self._arr[idx], np.ndarray) and self._arr[idx].ndim > 1 else self._arr[idx]
        def numpy(self):
            return self._arr
    arr = np.random.randn(1, 1, EMBEDDING_DIM)
    fake_tensor = FakeTensor(arr)
    mock_output = Mock()
    mock_output.last_hidden_state = fake_tensor
    model = Mock()
    model.__call__ = Mock(return_value=mock_output)
    def call(*args, **kwargs):
        return mock_output
    model.side_effect = call
    return model

@patch('src.utils.embeddings.QdrantClient')
def test_get_llm(mock_qdrant, mock_tokenizer, mock_model):
    """Test loading of FinGPT-2 model and tokenizer."""
    with patch('transformers.AutoTokenizer.from_pretrained', return_value=mock_tokenizer), \
         patch('transformers.AutoModel.from_pretrained', return_value=mock_model):
        tokenizer, model = get_llm()
        assert tokenizer == mock_tokenizer
        assert model == mock_model

@patch('src.utils.embeddings.QdrantClient')
def test_embed(mock_qdrant, mock_tokenizer, mock_model):
    """Test embedding generation."""
    with patch('transformers.AutoTokenizer.from_pretrained', return_value=mock_tokenizer), \
         patch('transformers.AutoModel.from_pretrained', return_value=mock_model):
        # Patch QdrantClient instance methods
        instance = mock_qdrant.return_value
        instance.upsert.return_value = None
        text = "Test financial text"
        embedding = embed(text, store=False)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (EMBEDDING_DIM,)

@patch('src.utils.embeddings.QdrantClient')
def test_search_similar(mock_qdrant, mock_tokenizer, mock_model):
    """Test similarity search."""
    with patch('transformers.AutoTokenizer.from_pretrained', return_value=mock_tokenizer), \
         patch('transformers.AutoModel.from_pretrained', return_value=mock_model):
        # Patch QdrantClient instance methods
        instance = mock_qdrant.return_value
        instance.upsert.return_value = None
        instance.search.return_value = [
            Mock(payload={"text": "Similar text 1"}, score=0.9),
            Mock(payload={"text": "Similar text 2"}, score=0.8)
        ]
        results = search_similar("Test query", limit=2)
        assert len(results) == 2
        assert all(isinstance(r, dict) for r in results)
        assert all("text" in r and "score" in r for r in results)

@patch('src.utils.embeddings.QdrantClient')
def test_init_collection(mock_qdrant):
    """Test collection initialization."""
    instance = mock_qdrant.return_value
    instance.get_collections.return_value.collections = []
    instance.create_collection.return_value = None
    init_collection()
    instance.create_collection.assert_called_once()

@patch('src.utils.embeddings.QdrantClient')
def test_clear_collection(mock_qdrant):
    """Test collection clearing."""
    instance = mock_qdrant.return_value
    instance.delete_collection.return_value = None
    instance.create_collection.return_value = None
    clear_collection()
    instance.delete_collection.assert_called_once()
    instance.create_collection.assert_called_once()

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

@patch('src.llm.embeddings.tokenizer')
@patch('src.llm.embeddings.model')
@patch('src.llm.embeddings.fetch_fundamentals')
def test_explain_with_fingpt(mock_fetch, mock_model, mock_tokenizer):
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
    assert mock_model.generate.called
    assert mock_tokenizer.decode.called 