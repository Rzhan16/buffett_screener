"""
Buffett scoring module using valinvest to calculate F-scores.
Includes SQLite caching for performance.
"""
import os
import sqlite3
import datetime
import json
from typing import Dict, Tuple, Optional, Any, Union
import logging
import pandas as pd

from dotenv import load_dotenv
from valinvest import Fundamental

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

__all__ = ["get_score", "F_SCORE_THRESHOLD"]

logger = logging.getLogger(__name__)

def get_f_score() -> pd.DataFrame:
    """
    Get F-scores for all stocks from cache or calculate if needed.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with F-scores and required data for position sizing
    """
    cache_file = 'score_cache.sqlite'
    cache_freshness = 86400  # 24 hours in seconds
    
    # Check if cache exists and is fresh
    if os.path.exists(cache_file):
        cache_age = datetime.datetime.now().timestamp() - os.path.getmtime(cache_file)
        if cache_age < cache_freshness:
            logger.info("Using cached F-scores")
            return _load_from_cache(cache_file)
    
    # Calculate new scores
    logger.info("Calculating new F-scores")
    scores = _calculate_f_scores()
    
    # Cache results
    _save_to_cache(scores, cache_file)
    
    return scores

def _calculate_f_scores() -> pd.DataFrame:
    """
    Calculate F-scores for all stocks.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with F-scores and required data
    """
    # TODO: Implement actual F-score calculation
    # For now, return mock data for testing
    return pd.DataFrame({
        'score': [8, 7, 6, 9, 8, 7, 6, 5, 4, 3, 2, 1],
        'close': [100] * 12,
        'atr': [2] * 12
    }, index=['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 
              'NVDA', 'AMD', 'INTC', 'IBM', 'ORCL', 'SAP'])

def _load_from_cache(cache_file: str) -> pd.DataFrame:
    """Load F-scores from SQLite cache."""
    try:
        with sqlite3.connect(cache_file) as conn:
            return pd.read_sql("SELECT * FROM f_scores", conn, index_col='symbol')
    except Exception as e:
        logger.error(f"Failed to load from cache: {e}")
        return _calculate_f_scores()

def _save_to_cache(scores: pd.DataFrame, cache_file: str) -> None:
    """Save F-scores to SQLite cache."""
    try:
        with sqlite3.connect(cache_file) as conn:
            scores.to_sql('f_scores', conn, if_exists='replace')
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
    if cached_result:
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