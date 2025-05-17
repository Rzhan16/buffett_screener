"""
Realtime data streaming module for Alpaca websocket with Yahoo Finance fallback.
Provides 1-minute bars for stock tickers with auto-reconnect capability.
"""
import os
import json
import time
import logging
import websocket
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Generator, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def connect_alpaca_websocket(tickers: List[str], retries: int = 3) -> Generator[Dict[str, Any], None, None]:
    """
    Connect to Alpaca websocket API and stream 1-minute bars.
    Auto-reconnects on disconnection.
    
    Args:
        tickers: List of ticker symbols to stream
        retries: Number of connection retry attempts before raising error
    
    Yields:
        Dictionary with timestamp, symbol, price, and volume data
    
    Raises:
        RuntimeError: If connection fails after specified retries
    """
    # Get API credentials from environment
    api_key = os.environ.get('ALPACA_API_KEY')
    api_secret = os.environ.get('ALPACA_API_SECRET')
    
    if not api_key or not api_secret:
        logger.warning("Alpaca API credentials not found. Falling back to Yahoo Finance.")
        yield from _fallback_to_yahoo(tickers)
        return
    
    # Prepare subscription message
    subscription_msg = {
        "action": "subscribe",
        "bars": tickers
    }
    
    # Track retry attempts
    attempt = 0
    last_reconnect_time = None
    
    while attempt <= retries:
        try:
            # Create websocket connection
            ws = websocket.WebSocketApp(
                "wss://stream.data.alpaca.markets/v2/iex",
                on_open=lambda ws: _on_open(ws, subscription_msg, api_key, api_secret),
                on_message=lambda ws, msg: _process_message(ws, msg),
                on_error=lambda ws, error: logger.error(f"WebSocket error: {error}"),
                on_close=lambda ws, close_status_code, close_msg: logger.info("WebSocket connection closed")
            )
            
            # Store message queue for yielding
            ws.message_queue = []
            
            # Start websocket in a separate thread
            ws_thread = websocket.WebSocketApp.run_forever
            
            # Start the connection
            logger.info(f"Connecting to Alpaca WebSocket (attempt {attempt+1}/{retries+1})...")
            ws_thread(ws)
            
            # Process messages while connected
            while ws.sock and ws.sock.connected:
                if ws.message_queue:
                    yield ws.message_queue.pop(0)
                else:
                    time.sleep(0.1)
            
            # If we reach here, the connection was closed
            logger.warning("WebSocket connection lost. Attempting to reconnect...")
            
            # Implement exponential backoff for reconnection
            current_time = time.time()
            if last_reconnect_time and (current_time - last_reconnect_time) < 60:
                backoff = min(2 ** attempt, 30)  # Max 30 seconds backoff
                logger.info(f"Backing off for {backoff} seconds before reconnecting...")
                time.sleep(backoff)
            
            last_reconnect_time = time.time()
            attempt += 1
            
        except Exception as e:
            logger.error(f"Error in WebSocket connection: {e}")
            attempt += 1
            
            if attempt > retries:
                logger.error(f"Failed to connect after {retries} attempts. Falling back to Yahoo Finance.")
                yield from _fallback_to_yahoo(tickers)
                return
            
            time.sleep(2)
    
    # If we've exhausted retries, raise an error
    raise RuntimeError(f"Failed to maintain Alpaca WebSocket connection after {retries} attempts")


def _on_open(ws, subscription_msg, api_key, api_secret):
    """Handle WebSocket open event and authenticate."""
    logger.info("WebSocket connection established")
    
    # Send authentication message
    auth_msg = {
        "action": "auth",
        "key": api_key,
        "secret": api_secret
    }
    
    ws.send(json.dumps(auth_msg))
    logger.info("Authentication message sent")
    
    # Subscribe to the requested tickers
    ws.send(json.dumps(subscription_msg))
    logger.info(f"Subscribed to {len(subscription_msg['bars'])} tickers")


def _process_message(ws, message):
    """Process incoming WebSocket messages."""
    try:
        data = json.loads(message)
        
        # Handle different message types
        if isinstance(data, list) and len(data) > 0:
            msg_type = data[0].get('T')
            
            # Handle bar updates
            if msg_type == 'b':
                for bar in data:
                    # Format the data in our standard format
                    formatted_data = {
                        'ts': datetime.fromtimestamp(bar['t'] / 1000000000),  # Convert nanoseconds to datetime
                        'symbol': bar['S'],
                        'price': bar['c'],  # Use closing price
                        'volume': bar['v']
                    }
                    
                    # Add to message queue for yielding
                    ws.message_queue.append(formatted_data)
            
            # Handle authentication responses
            elif msg_type == 'success' or msg_type == 'error':
                logger.info(f"Received {msg_type} message: {data}")
                
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def _fallback_to_yahoo(tickers: List[str]) -> Generator[Dict[str, Any], None, None]:
    """
    Fallback to Yahoo Finance for data when Alpaca is unavailable.
    Simulates streaming by fetching recent data and yielding at 1-minute intervals.
    
    Args:
        tickers: List of ticker symbols
    
    Yields:
        Dictionary with timestamp, symbol, price, and volume data
    """
    logger.info(f"Using Yahoo Finance fallback for tickers: {tickers}")
    
    while True:
        try:
            # Get current time
            now = datetime.now()
            
            # For each ticker, get the latest data
            for ticker in tickers:
                try:
                    # Get data for the last day
                    data = yf.Ticker(ticker).history(period="1d", interval="1m")
                    
                    if not data.empty:
                        # Get the latest bar
                        latest = data.iloc[-1]
                        
                        yield {
                            'ts': now,
                            'symbol': ticker,
                            'price': latest['Close'],
                            'volume': latest['Volume']
                        }
                    else:
                        logger.warning(f"No data available for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Error fetching Yahoo data for {ticker}: {e}")
            
            # Sleep for approximately 1 minute to simulate 1-minute bars
            time.sleep(60)
            
        except Exception as e:
            logger.error(f"Error in Yahoo Finance fallback: {e}")
            time.sleep(60)  # Retry after a minute


if __name__ == "__main__":
    """Demo script to show realtime data streaming."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Stream realtime market data")
    parser.add_argument("--tickers", type=str, default="AAPL,MSFT,GOOGL", 
                        help="Comma-separated list of tickers")
    parser.add_argument("--source", type=str, choices=["alpaca", "yahoo"], default="alpaca",
                        help="Data source to use")
    args = parser.parse_args()
    
    tickers = args.tickers.split(",")
    
    print(f"Starting realtime data stream for: {tickers}")
    
    try:
        if args.source == "alpaca":
            stream = connect_alpaca_websocket(tickers)
        else:
            stream = _fallback_to_yahoo(tickers)
            
        for data in stream:
            print(f"{data['ts']} | {data['symbol']} | ${data['price']:.2f} | Vol: {data['volume']}")
            
    except KeyboardInterrupt:
        print("\nStream terminated by user")
    except Exception as e:
        print(f"Error: {e}") 