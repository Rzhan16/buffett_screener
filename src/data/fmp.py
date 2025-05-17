"""
Financial Modeling Prep (FMP) API client for fetching fundamental data.
Includes caching and retry logic for efficient and reliable data retrieval.
"""
import os
import time
import requests
import requests_cache
from typing import Dict, Any


def fetch_fundamentals(ticker: str, years: int = 10) -> Dict[str, Any]:
    """
    Fetch fundamental ratios data for a ticker from FMP API.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        years: Number of years of data to retrieve (default: 10)
    
    Returns:
        Dictionary containing fundamental data
    
    Raises:
        RuntimeError: If API calls fail after retries or if ticker is invalid
    """
    # Initialize cache
    requests_cache.install_cache(
        'fmp_cache.sqlite',
        backend='sqlite',
        expire_after=86400  # 24 hours in seconds
    )
    
    # Get API key from environment
    api_key = os.environ.get('FMP_KEY')
    if not api_key:
        raise RuntimeError("FMP_KEY environment variable not set")
    
    # Prepare API request
    url = f"https://financialmodelingprep.com/api/v3/ratios/{ticker}"
    params = {
        'apikey': api_key,
        'limit': years  # Get data for the specified number of years
    }
    
    # Retry logic
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            response = requests.get(url, params=params)
            
            # Check for rate limiting
            if response.status_code == 429:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(2)  # Sleep for 2 seconds before retrying
                    continue
                else:
                    raise RuntimeError(f"Rate limit exceeded after {max_retries} retries")
            
            # Check for other errors
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            
            # Validate response
            if not data:
                raise RuntimeError(f"No data found for ticker: {ticker}")
                
            return data
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            if retry_count < max_retries:
                time.sleep(2)
            else:
                raise RuntimeError(f"Failed to fetch data for {ticker}: {str(e)}")
    
    # This should never be reached due to the logic above
    raise RuntimeError("Unexpected error in fetch_fundamentals") 