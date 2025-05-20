"""
Utility module for fetching stock market universes.
"""
import pandas as pd
import requests
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

def get_sp500_tickers() -> List[str]:
    """
    Fetches S&P 500 tickers from Wikipedia.
    
    Returns:
        List[str]: List of S&P 500 ticker symbols
    """
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        return df['Symbol'].tolist()
    except Exception as e:
        logger.error(f"Failed to fetch S&P 500 tickers: {e}")
        return []

def get_nasdaq_tickers() -> List[str]:
    """
    Fetches NASDAQ tickers from NASDAQ's official API.
    
    Returns:
        List[str]: List of NASDAQ ticker symbols
    """
    try:
        url = "https://api.nasdaq.com/api/screener/stocks?exchange=NASDAQ&limit=3000"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        tickers = [item['symbol'] for item in data['data']['table']['rows']]
        return tickers
    except Exception as e:
        logger.error(f"Failed to fetch NASDAQ tickers: {e}")
        return []

def get_russell2000_tickers() -> List[str]:
    """
    Fetches Russell 2000 tickers from Wikipedia.
    
    Returns:
        List[str]: List of Russell 2000 ticker symbols
    """
    try:
        # Note: Wikipedia doesn't maintain a reliable list of Russell 2000 companies
        # This is a fallback approach using the ETF holdings
        # In a real implementation, you would want to use a data provider or paid API
        url = "https://www.ishares.com/us/products/239710/ishares-russell-2000-etf/1467271812596.ajax?fileType=csv&fileName=IWM_holdings&dataType=fund"
        df = pd.read_csv(url, skiprows=9)
        
        # Extract ticker symbols
        tickers = []
        for ticker_str in df['Ticker']:
            try:
                if isinstance(ticker_str, str) and ticker_str.strip():
                    tickers.append(ticker_str.strip())
            except:
                continue
                
        logger.info(f"Fetched {len(tickers)} Russell 2000 tickers")
        return tickers
        
    except Exception as e:
        logger.error(f"Failed to fetch Russell 2000 tickers: {e}")
        return []

def get_universe_tickers(universe: str) -> List[str]:
    """
    Gets ticker symbols for the specified universe.
    
    Args:
        universe: String specifying which universe to use ("SP500", "NASDAQ", "RUSSELL2000", or "ALL")
        
    Returns:
        List[str]: Combined list of unique ticker symbols
    """
    if universe.upper() == "SP500":
        return get_sp500_tickers()
    elif universe.upper() == "NASDAQ":
        return get_nasdaq_tickers()
    elif universe.upper() == "RUSSELL2000" or universe.upper() == "RUSSELL":
        return get_russell2000_tickers()
    elif universe.upper() == "ALL":
        sp500 = set(get_sp500_tickers())
        nasdaq = set(get_nasdaq_tickers())
        russell = set(get_russell2000_tickers())
        return list(sp500 | nasdaq | russell)  # Union of all sets
    else:
        logger.warning(f"Unknown universe: {universe}. Defaulting to S&P 500")
        return get_sp500_tickers()

def get_batch_tickers(ticker_list: List[str], batch_size: int = 100) -> List[List[str]]:
    """
    Split tickers into batches to avoid API rate limits.
    
    Args:
        ticker_list: List of ticker symbols
        batch_size: Number of tickers per batch
        
    Returns:
        List[List[str]]: List of ticker batches
    """
    return [ticker_list[i:i + batch_size] for i in range(0, len(ticker_list), batch_size)] 