"""
Tests for the embeddings utility module.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
from src.utils.embeddings import (
    get_llm,
    embed,
    search_similar,
    init_collection,
    clear_collection,
    EMBEDDING_DIM
)

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