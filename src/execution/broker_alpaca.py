"""
Alpaca broker integration module for trade execution.
"""
import os
import logging
import json
from typing import Dict, List, Optional, Union, Any
import time
import requests

import alpaca_trade_api as tradeapi
from alpaca_trade_api.rest import REST, APIError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Default Alpaca API URLs
APCA_API_BASE_URL_PAPER = "https://paper-api.alpaca.markets"
APCA_API_BASE_URL_LIVE = "https://api.alpaca.markets"

__all__ = ["submit_bracket", "cancel_symbol", "get_positions"]


def _get_alpaca_client() -> REST:
    """
    Create and return an Alpaca REST client.
    
    Returns
    -------
    alpaca_trade_api.REST
        Configured Alpaca REST client
    
    Raises
    ------
    ValueError
        If API key or secret environment variables are not set
    """
    # Get API credentials from environment variables
    api_key = os.environ.get("APCA_API_KEY_ID")
    api_secret = os.environ.get("APCA_API_SECRET_KEY")
    
    if not api_key or not api_secret:
        raise ValueError("Alpaca API credentials not found in environment variables")
    
    # Determine if using paper or live trading
    base_url = os.environ.get("APCA_API_BASE_URL", APCA_API_BASE_URL_PAPER)
    
    # Create and return the client
    return REST(api_key, api_secret, base_url)


def submit_bracket(
    symbol: str,
    qty: int,
    entry_price: float,
    take_profit_price: float,
    stop_loss_price: float,
    client_order_id: Optional[str] = None,
    time_in_force: str = "gtc"
) -> Dict[str, Any]:
    """
    Submit a bracket order to Alpaca.
    
    Parameters
    ----------
    symbol : str
        Stock symbol
    qty : int
        Number of shares to trade
    entry_price : float
        Entry price limit
    take_profit_price : float
        Take profit price limit
    stop_loss_price : float
        Stop loss price
    client_order_id : str, optional
        Custom client order ID for tracking
    time_in_force : str, default "gtc"
        Time in force for the order (day, gtc, opg, cls, ioc, fok)
    
    Returns
    -------
    dict
        Dictionary containing the order information
    
    Raises
    ------
    ValueError
        If any of the parameters are invalid
    RuntimeError
        If there is an error submitting the order
    """
    # Validate inputs
    if qty <= 0:
        raise ValueError("Quantity must be positive")
    
    if entry_price <= 0 or take_profit_price <= 0 or stop_loss_price <= 0:
        raise ValueError("Prices must be positive")
    
    # Validate order logic for a long position
    if take_profit_price <= entry_price:
        raise ValueError("Take profit price must be greater than entry price")
    
    if stop_loss_price >= entry_price:
        raise ValueError("Stop loss price must be less than entry price")
    
    try:
        # Get Alpaca client
        alpaca = _get_alpaca_client()
        
        # Generate a client order ID if not provided
        if client_order_id is None:
            client_order_id = f"{symbol}_{int(time.time())}"
        
        # Submit the bracket order
        order = alpaca.submit_order(
            symbol=symbol,
            qty=qty,
            side="buy",
            type="limit",
            time_in_force=time_in_force,
            limit_price=str(entry_price),
            client_order_id=client_order_id,
            order_class="bracket",
            take_profit=dict(limit_price=str(take_profit_price)),
            stop_loss=dict(stop_price=str(stop_loss_price))
        )
        
        logger.info(f"Submitted bracket order for {symbol}: {order.id}")
        
        # Return the order as a dictionary
        return order._raw
    
    except APIError as e:
        logger.error(f"Alpaca API error: {e}")
        raise RuntimeError(f"Failed to submit bracket order: {e}")
    
    except Exception as e:
        logger.error(f"Error submitting bracket order: {e}")
        raise RuntimeError(f"Failed to submit bracket order: {e}")


def cancel_symbol(symbol: str) -> List[Dict[str, Any]]:
    """
    Cancel all open orders for a specific symbol.
    
    Parameters
    ----------
    symbol : str
        Stock symbol to cancel orders for
    
    Returns
    -------
    list
        List of dictionaries with details of canceled orders
    
    Raises
    ------
    RuntimeError
        If there is an error canceling the orders
    """
    try:
        # Get Alpaca client
        alpaca = _get_alpaca_client()
        
        # Get all open orders
        open_orders = alpaca.list_orders(status="open")
        
        # Filter orders for the specified symbol
        symbol_orders = [order for order in open_orders if order.symbol == symbol]
        
        # If no orders found for the symbol, return empty list
        if not symbol_orders:
            logger.info(f"No open orders found for {symbol}")
            return []
        
        # Cancel each order
        canceled_orders = []
        for order in symbol_orders:
            alpaca.cancel_order(order.id)
            logger.info(f"Canceled order {order.id} for {symbol}")
            canceled_orders.append(order._raw)
        
        return canceled_orders
    
    except APIError as e:
        logger.error(f"Alpaca API error: {e}")
        raise RuntimeError(f"Failed to cancel orders for {symbol}: {e}")
    
    except Exception as e:
        logger.error(f"Error canceling orders: {e}")
        raise RuntimeError(f"Failed to cancel orders for {symbol}: {e}")


def get_positions(symbol: Optional[str] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Get current positions from Alpaca.
    
    Parameters
    ----------
    symbol : str, optional
        Stock symbol. If provided, returns the position for that symbol.
        If None, returns all positions.
    
    Returns
    -------
    dict or list
        Dictionary with position details if symbol is provided,
        or list of dictionaries with all positions if symbol is None
    
    Raises
    ------
    RuntimeError
        If there is an error retrieving the positions
    """
    try:
        # Get Alpaca client
        alpaca = _get_alpaca_client()
        
        if symbol:
            # Get position for specific symbol
            try:
                position = alpaca.get_position(symbol)
                logger.info(f"Retrieved position for {symbol}")
                return position._raw
            except APIError as e:
                # Check if the error message contains "position does not exist"
                error_message = str(e).lower()
                if "position does not exist" in error_message:
                    logger.info(f"No position found for {symbol}")
                    return {}
                raise
        else:
            # Get all positions
            positions = alpaca.list_positions()
            logger.info(f"Retrieved {len(positions)} positions")
            return [pos._raw for pos in positions]
    
    except APIError as e:
        logger.error(f"Alpaca API error: {e}")
        raise RuntimeError(f"Failed to retrieve positions: {e}")
    
    except Exception as e:
        logger.error(f"Error retrieving positions: {e}")
        raise RuntimeError(f"Failed to retrieve positions: {e}")


if __name__ == "__main__":
    # Example usage
    try:
        # Set these environment variables before running
        # os.environ["APCA_API_KEY_ID"] = "your_api_key"
        # os.environ["APCA_API_SECRET_KEY"] = "your_api_secret"
        # os.environ["APCA_API_BASE_URL"] = APCA_API_BASE_URL_PAPER
        
        # Print which environment we're using
        base_url = os.environ.get("APCA_API_BASE_URL", APCA_API_BASE_URL_PAPER)
        mode = "PAPER" if base_url == APCA_API_BASE_URL_PAPER else "LIVE"
        print(f"Running in {mode} mode")
        
        # Get current positions
        positions = get_positions()
        print(f"Current positions: {json.dumps(positions, indent=2)}")
        
        # Example bracket order (uncomment to test)
        # order = submit_bracket(
        #     symbol="AAPL",
        #     qty=1,
        #     entry_price=150.0,
        #     take_profit_price=155.0,
        #     stop_loss_price=145.0
        # )
        # print(f"Submitted order: {json.dumps(order, indent=2)}")
        
        # Example cancel orders for a symbol (uncomment to test)
        # canceled = cancel_symbol("AAPL")
        # print(f"Canceled orders: {json.dumps(canceled, indent=2)}")
        
    except Exception as e:
        print(f"Error: {e}") 