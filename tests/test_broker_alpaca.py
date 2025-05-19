"""
Tests for Alpaca broker integration.
"""
import os
import pytest
from unittest.mock import patch, Mock, MagicMock
import json

from src.execution.broker_alpaca import (
    submit_bracket,
    cancel_symbol,
    get_positions,
    _get_alpaca_client,
    APCA_API_BASE_URL_PAPER,
    APCA_API_BASE_URL_LIVE
)


@pytest.fixture
def mock_env():
    """Set up mock environment variables for testing."""
    with patch.dict(os.environ, {
        "APCA_API_KEY_ID": "test_key",
        "APCA_API_SECRET_KEY": "test_secret",
        "APCA_API_BASE_URL": APCA_API_BASE_URL_PAPER
    }):
        yield


@pytest.fixture
def mock_alpaca_client():
    """Create a mock Alpaca client."""
    mock_client = Mock()
    
    # Mock order object
    mock_order = Mock()
    mock_order.id = "test_order_id"
    mock_order.symbol = "AAPL"  # Add symbol attribute for filtering
    mock_order._raw = {
        "id": "test_order_id",
        "client_order_id": "test_client_order_id",
        "symbol": "AAPL",
        "status": "new"
    }
    mock_client.submit_order.return_value = mock_order
    
    # Mock position object
    mock_position = Mock()
    mock_position._raw = {
        "symbol": "AAPL",
        "qty": "10",
        "avg_entry_price": "150.0",
        "current_price": "155.0"
    }
    mock_client.get_position.return_value = mock_position
    
    # Mock list positions
    mock_positions = [mock_position]
    mock_client.list_positions.return_value = mock_positions
    
    # Mock list orders
    mock_order_list = [mock_order]
    mock_client.list_orders.return_value = mock_order_list
    
    return mock_client


def test_get_alpaca_client(mock_env):
    """Test creating an Alpaca client."""
    # Patch the REST class at the location where it's imported in the module
    with patch('src.execution.broker_alpaca.REST') as mock_rest:
        client = _get_alpaca_client()
        mock_rest.assert_called_once_with("test_key", "test_secret", APCA_API_BASE_URL_PAPER)


def test_get_alpaca_client_missing_credentials():
    """Test error when credentials are missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Alpaca API credentials not found"):
            _get_alpaca_client()


def test_submit_bracket_success(mock_env, mock_alpaca_client):
    """Test successful bracket order submission."""
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        result = submit_bracket(
            symbol="AAPL",
            qty=1,
            entry_price=150.0,
            take_profit_price=155.0,
            stop_loss_price=145.0,
            client_order_id="test_id",
            time_in_force="day"
        )
        
        # Check the result
        assert result["id"] == "test_order_id"
        assert result["symbol"] == "AAPL"
        
        # Check that submit_order was called with correct parameters
        mock_alpaca_client.submit_order.assert_called_once_with(
            symbol="AAPL",
            qty=1,
            side="buy",
            type="limit",
            time_in_force="day",
            limit_price="150.0",
            client_order_id="test_id",
            order_class="bracket",
            take_profit={"limit_price": "155.0"},
            stop_loss={"stop_price": "145.0"}
        )


def test_submit_bracket_invalid_inputs(mock_env, mock_alpaca_client):
    """Test validation of bracket order inputs."""
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        # Test negative quantity
        with pytest.raises(ValueError, match="Quantity must be positive"):
            submit_bracket(
                symbol="AAPL",
                qty=-1,
                entry_price=150.0,
                take_profit_price=155.0,
                stop_loss_price=145.0
            )
        
        # Test negative price
        with pytest.raises(ValueError, match="Prices must be positive"):
            submit_bracket(
                symbol="AAPL",
                qty=1,
                entry_price=-150.0,
                take_profit_price=155.0,
                stop_loss_price=145.0
            )
        
        # Test take profit <= entry
        with pytest.raises(ValueError, match="Take profit price must be greater than entry price"):
            submit_bracket(
                symbol="AAPL",
                qty=1,
                entry_price=150.0,
                take_profit_price=150.0,
                stop_loss_price=145.0
            )
        
        # Test stop loss >= entry
        with pytest.raises(ValueError, match="Stop loss price must be less than entry price"):
            submit_bracket(
                symbol="AAPL",
                qty=1,
                entry_price=150.0,
                take_profit_price=155.0,
                stop_loss_price=150.0
            )


def test_submit_bracket_api_error(mock_env):
    """Test handling of API errors during order submission."""
    mock_client = Mock()
    mock_client.submit_order.side_effect = Exception("API Error")
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_client):
        with pytest.raises(RuntimeError, match="Failed to submit bracket order"):
            submit_bracket(
                symbol="AAPL",
                qty=1,
                entry_price=150.0,
                take_profit_price=155.0,
                stop_loss_price=145.0
            )


def test_cancel_symbol_success(mock_env, mock_alpaca_client):
    """Test successful cancellation of orders for a symbol."""
    # Ensure the mock order has the right attribute
    mock_order = Mock()
    mock_order.id = "test_order_id"
    mock_order.symbol = "AAPL"
    mock_order._raw = {
        "id": "test_order_id",
        "symbol": "AAPL",
        "status": "new"
    }
    mock_alpaca_client.list_orders.return_value = [mock_order]
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        result = cancel_symbol("AAPL")
        
        # Check that list_orders was called
        mock_alpaca_client.list_orders.assert_called_once_with(status="open")
        
        # Check that cancel_order was called
        mock_alpaca_client.cancel_order.assert_called_once_with("test_order_id")
        
        # Check the result
        assert len(result) == 1
        assert result[0]["id"] == "test_order_id"
        assert result[0]["symbol"] == "AAPL"


def test_cancel_symbol_no_orders(mock_env, mock_alpaca_client):
    """Test cancellation when no orders exist for the symbol."""
    # Set up mock to return empty list
    mock_alpaca_client.list_orders.return_value = []
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        result = cancel_symbol("AAPL")
        
        # Check that list_orders was called
        mock_alpaca_client.list_orders.assert_called_once_with(status="open")
        
        # Check that cancel_order was not called
        mock_alpaca_client.cancel_order.assert_not_called()
        
        # Check the result is an empty list
        assert result == []


def test_cancel_symbol_api_error(mock_env):
    """Test handling of API errors during order cancellation."""
    mock_client = Mock()
    mock_client.list_orders.side_effect = Exception("API Error")
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_client):
        with pytest.raises(RuntimeError, match="Failed to cancel orders"):
            cancel_symbol("AAPL")


def test_get_positions_all(mock_env, mock_alpaca_client):
    """Test retrieving all positions."""
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        result = get_positions()
        
        # Check that list_positions was called
        mock_alpaca_client.list_positions.assert_called_once()
        
        # Check the result
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["qty"] == "10"


def test_get_positions_symbol(mock_env, mock_alpaca_client):
    """Test retrieving a position for a specific symbol."""
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        result = get_positions("AAPL")
        
        # Check that get_position was called with the correct symbol
        mock_alpaca_client.get_position.assert_called_once_with("AAPL")
        
        # Check the result
        assert result["symbol"] == "AAPL"
        assert result["qty"] == "10"


def test_get_positions_symbol_not_found(mock_env, mock_alpaca_client):
    """Test retrieving a position that doesn't exist."""
    # Create a mock APIError with a proper error message
    class MockAPIError(Exception):
        pass
    
    # Set up mock to raise APIError for non-existent position
    mock_api_error = MockAPIError("position does not exist")
    mock_alpaca_client.get_position.side_effect = mock_api_error
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_alpaca_client):
        with patch('src.execution.broker_alpaca.APIError', MockAPIError):
            result = get_positions("MSFT")
            
            # Check that get_position was called with the correct symbol
            mock_alpaca_client.get_position.assert_called_once_with("MSFT")
            
            # Check the result is an empty dict
            assert result == {}


def test_get_positions_api_error(mock_env):
    """Test handling of API errors during position retrieval."""
    mock_client = Mock()
    mock_client.list_positions.side_effect = Exception("API Error")
    
    with patch('src.execution.broker_alpaca._get_alpaca_client', return_value=mock_client):
        with pytest.raises(RuntimeError, match="Failed to retrieve positions"):
            get_positions()


def test_toggle_paper_live():
    """Test toggling between paper and live trading."""
    # Test paper trading
    with patch.dict(os.environ, {
        "APCA_API_KEY_ID": "test_key",
        "APCA_API_SECRET_KEY": "test_secret",
        "APCA_API_BASE_URL": APCA_API_BASE_URL_PAPER
    }):
        with patch('src.execution.broker_alpaca.REST') as mock_rest:
            client = _get_alpaca_client()
            mock_rest.assert_called_once_with("test_key", "test_secret", APCA_API_BASE_URL_PAPER)
    
    # Test live trading
    with patch.dict(os.environ, {
        "APCA_API_KEY_ID": "test_key",
        "APCA_API_SECRET_KEY": "test_secret",
        "APCA_API_BASE_URL": APCA_API_BASE_URL_LIVE
    }):
        with patch('src.execution.broker_alpaca.REST') as mock_rest:
            client = _get_alpaca_client()
            mock_rest.assert_called_once_with("test_key", "test_secret", APCA_API_BASE_URL_LIVE) 