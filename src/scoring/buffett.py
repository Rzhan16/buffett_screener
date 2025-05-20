"""
Buffett scoring module using valinvest to calculate F-scores.
Includes SQLite caching for performance.
"""
import os
import sqlite3
import datetime
import json
from typing import Dict, Tuple, Optional, Any, Union, List
import logging
import pandas as pd
import yfinance as yf

from dotenv import load_dotenv
from valinvest import Fundamental
from src.utils.universe import get_universe_tickers, get_batch_tickers

# Import the score threshold from memory bank
F_SCORE_THRESHOLD = 7  # Default value if memory_bank.md is not available

# Try to read from memory_bank.md
try:
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'memory_bank.md'), 'r') as f:
        for line in f:
            if line.strip().startswith('F_SCORE_THRESHOLD'):
                F_SCORE_THRESHOLD = int(line.strip().split()[1])
                break
except (FileNotFoundError, ValueError, IndexError):
    pass  # Use default value if file not found or parsing error

__all__ = ["get_score", "F_SCORE_THRESHOLD", "get_f_score"]

logger = logging.getLogger(__name__)

def get_f_score(universe: str = "SP500") -> pd.DataFrame:
    """
    Get F-scores for all stocks from cache or calculate if needed.
    
    Parameters
    ----------
    universe : str, default "SP500"
        Stock universe to scan (SP500, NASDAQ, or ALL)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with F-scores and required data for position sizing
    """
    cache_file = f'score_cache_{universe.lower()}.sqlite'
    cache_freshness = 86400  # 24 hours in seconds
    
    # Check if cache exists and is fresh
    if os.path.exists(cache_file):
        cache_age = datetime.datetime.now().timestamp() - os.path.getmtime(cache_file)
        if cache_age < cache_freshness:
            logger.info(f"Using cached F-scores for {universe}")
            return _load_from_cache(cache_file)
    
    # Calculate new scores
    logger.info(f"Calculating new F-scores for {universe}")
    scores = _calculate_f_scores(universe)
    
    # Cache results
    _save_to_cache(scores, cache_file)
    
    return scores

def _calculate_f_scores(universe: str = "SP500") -> pd.DataFrame:
    """
    Calculate F-scores for stocks in the specified universe.
    
    Parameters
    ----------
    universe : str, default "SP500"
        Stock universe to scan (SP500, NASDAQ, or ALL)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with F-scores and required data
    """
    # Get tickers from specified universe
    tickers = get_universe_tickers(universe)
    logger.info(f"Fetched {len(tickers)} tickers from {universe}")
    
    # If we're in development/test mode and no tickers are found or API issues, use mock data
    if not tickers or universe.upper().startswith("MOCK"):
        logger.warning("Using mock data for development")
        if 'AFFORDABLE' in universe.upper() or universe.upper() == 'MOCK_AFFORDABLE':
            # Return mock data for affordable stocks
            return pd.DataFrame({
                'score': [8, 7, 9, 8, 7, 8, 7, 9, 8, 7, 7, 8],
                'close': [45, 28, 32, 18, 25, 42, 37, 22, 48, 39, 17, 30],
                'atr': [1.2, 0.8, 0.9, 0.5, 0.7, 1.1, 1.0, 0.6, 1.3, 1.0, 0.6, 0.8]
            }, index=['F', 'SOFI', 'PLTR', 'HOOD', 'NIO', 'PLUG', 'RIVN', 'COIN', 'SNAP', 'PINS', 'SKLZ', 'GM'])
        else:
            # Return mock data for large-cap stocks
            return pd.DataFrame({
                'score': [8, 7, 6, 9, 8, 7, 6, 5, 4, 3, 2, 1, 8, 7, 6, 9, 8, 7],
                'close': [100, 45, 30, 180, 450, 170, 400, 150, 120, 90, 80, 70, 25, 35, 40, 15, 20, 30],
                'atr': [2, 1.5, 1, 3, 4, 2.5, 3.5, 2, 1.8, 1.5, 1.2, 1, 0.8, 1, 1.2, 0.5, 0.7, 0.9]
            }, index=['AAPL', 'F', 'GM', 'AMZN', 'META', 'TSLA', 
                    'NVDA', 'AMD', 'INTC', 'IBM', 'ORCL', 'SAP',
                    'PLTR', 'RBLX', 'SNAP', 'HOOD', 'COIN', 'RIVN'])
    
    # Get price and ATR data
    price_data = _get_price_data(tickers)
    
    # Get F-scores for each ticker
    scores_data = {}
    load_dotenv()
    api_key = os.environ.get('FMP_KEY')
    
    # Process in batches to avoid API rate limits
    ticker_batches = get_batch_tickers(tickers, batch_size=50)
    
    for batch in ticker_batches:
        for ticker in batch:
            try:
                if ticker in price_data.index:
                    # Calculate F-score using valinvest if API key is available
                    if api_key:
                        analyzer = _create_fundamental_analyzer(ticker, api_key)
                        score_result = analyzer.score()
                        scores_data[ticker] = float(score_result['overall_score'])
                    else:
                        # Generate a random F-score between 1-9 if no API key
                        import random
                        scores_data[ticker] = random.randint(1, 9)
                        logger.warning(f"No API key, using random F-score for {ticker}")
            except Exception as e:
                logger.error(f"Failed to calculate F-score for {ticker}: {e}")
    
    # Combine price data and scores
    result = price_data.copy()
    result['score'] = pd.Series(scores_data)
    
    # Drop rows with missing data
    result = result.dropna()
    
    return result

def _get_price_data(tickers: List[str]) -> pd.DataFrame:
    """
    Get price and ATR data for a list of tickers using Yahoo Finance.
    
    Parameters
    ----------
    tickers : List[str]
        List of ticker symbols
        
    Returns
    -------
    pd.DataFrame
        DataFrame with close prices and ATR values
    """
    try:
        # Download historical data for all tickers
        data = yf.download(tickers, period="3mo", progress=False)
        
        # Calculate close price (most recent)
        close = data['Close'].iloc[-1]
        
        # Calculate ATR (14-day)
        high = data['High']
        low = data['Low']
        close_prev = data['Close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        
        # Combine into result DataFrame
        result = pd.DataFrame({
            'close': close,
            'atr': atr
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get price data: {e}")
        return pd.DataFrame(columns=['close', 'atr'])

def _load_from_cache(cache_file: str) -> pd.DataFrame:
    """Load F-scores from SQLite cache."""
    try:
        with sqlite3.connect(cache_file) as conn:
            return pd.read_sql("SELECT * FROM f_scores", conn, index_col='symbol')
    except Exception as e:
        logger.error(f"Failed to load from cache: {e}")
        return pd.DataFrame(columns=['score', 'close', 'atr'])

def _save_to_cache(scores: pd.DataFrame, cache_file: str) -> None:
    """Save F-scores to SQLite cache."""
    try:
        with sqlite3.connect(cache_file) as conn:
            scores.to_sql('f_scores', conn, if_exists='replace', index_label='symbol')
        logger.info(f"Saved F-scores to {cache_file}")
    except Exception as e:
        logger.error(f"Failed to save to cache: {e}")

def _create_fundamental_analyzer(ticker: str, api_key: str) -> Fundamental:
    """
    Create a valinvest Fundamental analyzer instance.
    This function is separated to make testing easier.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    api_key : str
        API key for FMP
        
    Returns
    -------
    Fundamental
        Valinvest Fundamental analyzer instance
    """
    return Fundamental(ticker, apikey=api_key)


def get_score(ticker: str, fundamentals: Optional[Dict[str, Any]] = None) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate the Buffett F-score for a ticker using valinvest.
    Uses SQLite caching to avoid redundant calculations.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    fundamentals : dict, optional
        Optional pre-fetched fundamental data
        
    Returns
    -------
    tuple
        (score, details_dict) where details_dict contains component scores
        
    Raises
    ------
    RuntimeError
        If valinvest encounters an error or API request fails
        
    Examples
    --------
    >>> score, details = get_score("AAPL")
    >>> print(f"F-Score: {score}")
    F-Score: 8.0
    >>> print(f"Profitability score: {details['profitability']}")
    Profitability score: 4
    """
    # Check cache first
    cached_result = _get_from_cache(ticker)
    if cached_result is not None:
        return cached_result
    
    # If no cache hit, calculate the score
    try:
        # Load API key from .env file
        load_dotenv()
        api_key = os.environ.get('FMP_KEY')
        if not api_key:
            raise RuntimeError("FMP_KEY environment variable not set")
            
        # Initialize valinvest Fundamental analyzer
        analyzer = _create_fundamental_analyzer(ticker, api_key)
        
        # Calculate F-score
        score_result = analyzer.score()
        
        # Extract the overall score and component details
        overall_score = float(score_result['overall_score'])
        
        # Create details dictionary with component scores
        details = {
            'profitability': score_result['profitability_score'],
            'leverage': score_result['leverage_score'],
            'operating_efficiency': score_result['operating_efficiency_score'],
            'components': {
                'positive_net_income': score_result['positive_net_income'],
                'positive_operating_cashflow': score_result['positive_operating_cashflow'],
                'higher_roa': score_result['higher_roa'],
                'cashflow_greater_than_income': score_result['cashflow_greater_than_income'],
                'lower_leverage_ratio': score_result['lower_leverage_ratio'],
                'higher_current_ratio': score_result['higher_current_ratio'],
                'no_dilution': score_result['no_dilution'],
                'higher_gross_margin': score_result['higher_gross_margin'],
                'higher_asset_turnover': score_result['higher_asset_turnover']
            }
        }
        
        # Cache the result
        _cache_result(ticker, overall_score, details)
        
        return overall_score, details
        
    except Exception as e:
        # Raise a RuntimeError with the original error message
        raise RuntimeError(f"Error calculating F-score for {ticker}: {str(e)}")


def _get_from_cache(ticker: str) -> Optional[Tuple[float, Dict[str, Any]]]:
    """
    Check if we have a recent score in the cache.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    
    Returns
    -------
    tuple or None
        Cached (score, details) tuple if available and fresh, None otherwise
    """
    # Initialize the cache if it doesn't exist
    _init_cache()
    
    try:
        # Connect to the cache database
        conn = sqlite3.connect('score_cache.sqlite')
        cursor = conn.cursor()
        
        # Get the current date
        today = datetime.date.today().isoformat()
        
        # Query for today's cached score
        cursor.execute(
            "SELECT score, details FROM scores WHERE ticker = ? AND date = ?",
            (ticker.upper(), today)
        )
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            score, details_json = result
            # Convert the JSON string back to a dictionary
            details = json.loads(details_json)
            return float(score), details
            
        return None
        
    except Exception:
        return None


def _cache_result(ticker: str, score: float, details: Dict[str, Any]) -> None:
    """
    Cache a score result in the SQLite database.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    score : float
        The calculated F-score
    details : dict
        Dictionary with component scores and other details
    """
    # Initialize the cache if it doesn't exist
    _init_cache()
    
    try:
        # Connect to the cache database
        conn = sqlite3.connect('score_cache.sqlite')
        cursor = conn.cursor()
        
        # Get the current date
        today = datetime.date.today().isoformat()
        
        # Convert details to JSON for storage
        details_json = json.dumps(details)
        
        # Insert or replace the score
        cursor.execute(
            """
            INSERT OR REPLACE INTO scores (ticker, date, score, details)
            VALUES (?, ?, ?, ?)
            """,
            (ticker.upper(), today, score, details_json)
        )
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        pass  # Silently fail on cache errors


def _init_cache() -> None:
    """Initialize the SQLite cache database if it doesn't exist."""
    try:
        conn = sqlite3.connect('score_cache.sqlite')
        cursor = conn.cursor()
        
        # Create the scores table if it doesn't exist
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scores (
                ticker TEXT,
                date TEXT,
                score REAL,
                details TEXT,
                PRIMARY KEY (ticker, date)
            )
            """
        )
        
        conn.commit()
        conn.close()
        
    except Exception:
        pass  # Silently fail on initialization errors


if __name__ == "__main__":
    """Simple demo of the scoring functionality."""
    import sys
    
    # Get ticker from command line or use default
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    print(f"Calculating Buffett score for {ticker}...")
    score, details = get_score(ticker)
    
    print(f"Score: {score:.1f} / 9.0")
    print(f"Meets threshold ({F_SCORE_THRESHOLD}): {'Yes' if score >= F_SCORE_THRESHOLD else 'No'}")
    
    print("\nComponent Scores:")
    print(f"- Profitability: {details['profitability']}")
    print(f"- Leverage: {details['leverage']}")
    print(f"- Operating Efficiency: {details['operating_efficiency']}")
    
    print("\nIndividual Metrics:")
    for metric, value in details['components'].items():
        print(f"- {metric.replace('_', ' ').title()}: {'✓' if value else '✗'}") 