#!/usr/bin/env python
"""
Test script for Growth Stock Screener
Focused on finding stocks like NBIS and RXRX (under $20 with high growth potential)
"""
import os
import sys
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import the memo generation function from growth screener
from run_growth_screener import generate_growth_memo

def get_simplified_growth_metrics(ticker):
    """Get growth metrics for a stock using a simplified approach"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get basic info
        name = info.get('shortName', ticker)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        market_cap = info.get('marketCap', 0)
        sector = info.get('sector', 'Unknown')
        industry = info.get('industry', 'Unknown')
        
        # If price is zero, try to get from history
        if current_price == 0:
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = hist['Close'].iloc[-1]
        
        # Get price history for momentum calculations
        hist = stock.history(period="6mo")
        
        if hist.empty:
            print(f"No price history available for {ticker}")
            return None
            
        # Calculate momentum over different timeframes
        end_price = hist['Close'].iloc[-1] if not hist.empty else 0
        
        # 3-month momentum
        three_months_ago = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        three_month_data = hist[hist.index <= three_months_ago]
        start_price_3m = three_month_data['Close'].iloc[0] if not three_month_data.empty else end_price
        momentum_3m = ((end_price / start_price_3m) - 1) * 100 if start_price_3m > 0 else 0
        
        # 1-month momentum
        one_month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        one_month_data = hist[hist.index <= one_month_ago]
        start_price_1m = one_month_data['Close'].iloc[0] if not one_month_data.empty else end_price
        momentum_1m = ((end_price / start_price_1m) - 1) * 100 if start_price_1m > 0 else 0
        
        # Calculate volume ratio
        avg_volume = hist['Volume'].mean() if not hist.empty else 0
        recent_volume = hist['Volume'].tail(5).mean() if not hist.empty and len(hist) >= 5 else 0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Calculate volatility (standard deviation of daily returns)
        if not hist.empty and len(hist) > 5:
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * 100  # Convert to percentage
        else:
            volatility = 5  # Default 5% if not enough data
            
        # Calculate growth score (0-100)
        growth_score = 0
        
        # Momentum component (up to 50 points)
        if momentum_3m > 0:
            growth_score += min(momentum_3m, 30)  # Up to 30 points for 3-month momentum
        if momentum_1m > 0:
            growth_score += min(momentum_1m, 20)  # Up to 20 points for 1-month momentum
            
        # Volume component (up to 20 points)
        if volume_ratio > 1:
            growth_score += min((volume_ratio - 1) * 20, 20)  # Up to 20 points for increasing volume
            
        # Price component (up to 10 points)
        if 5 <= current_price <= 20:
            growth_score += 10  # Ideal price range gets full points
        elif current_price < 5:
            growth_score += current_price * 2  # 2 points per dollar under $5
            
        # Volatility component (up to 20 points)
        optimal_volatility = 25  # Optimal volatility for growth stocks (25%)
        volatility_score = 20 - abs(volatility - optimal_volatility) * 0.8
        growth_score += max(0, volatility_score)
        
        # Return metrics
        return {
            'ticker': ticker,
            'name': name,
            'price': current_price,
            'market_cap': market_cap,
            'sector': sector,
            'industry': industry,
            'momentum_3m': momentum_3m,
            'momentum_1m': momentum_1m,
            'volume_ratio': volume_ratio,
            'volatility': volatility,
            'growth_score': growth_score,
            'revenue_growth': None,  # We don't calculate these in the simplified version
            'earnings_growth': None
        }
    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return None

def test_specific_stocks():
    """Test the growth metrics on specific stocks like NBIS and RXRX"""
    print("\n=== Testing Growth Metrics for Specific Stocks ===")
    
    # List of stocks similar to NBIS and RXRX to test
    test_stocks = [
        "NBIS",  # NBI Solutions - your example
        "RXRX",  # Recursion Pharmaceuticals - your example
        "SOFI",  # SoFi Technologies - fintech under $20
        "PLTR",  # Palantir - AI/data analytics
        "DNA",   # Ginkgo Bioworks - synthetic biology
        "IONQ",  # IonQ - quantum computing
        "AFRM",  # Affirm Holdings - fintech
        "ME",    # 23andMe - genomics
        "JOBY",  # Joby Aviation - electric air vehicles
        "HOOD"   # Robinhood - fintech
    ]
    
    results = []
    
    for ticker in test_stocks:
        print(f"Analyzing {ticker}...")
        metrics = get_simplified_growth_metrics(ticker)
        if metrics:
            results.append(metrics)
            print(f"✅ {ticker}: Growth Score = {metrics['growth_score']:.1f}/100")
            print(f"   Price: ${metrics['price']:.2f}")
            print(f"   3-Month Momentum: {metrics['momentum_3m']:.1f}%")
            print(f"   Volume Ratio: {metrics['volume_ratio']:.2f}x")
        else:
            print(f"❌ Could not get metrics for {ticker}")
    
    if results:
        # Convert to DataFrame
        stocks_df = pd.DataFrame(results)
        
        # Sort by growth score
        stocks_df = stocks_df.sort_values('growth_score', ascending=False)
        
        # Generate memo
        memo = generate_growth_memo(stocks_df)
        
        # Save the memo to a file
        output_file = "test_growth_stocks.md"
        with open(output_file, "w") as f:
            f.write(memo)
        
        print(f"\nTest results saved to {output_file}")
        
        # Print summary
        print("\n=== Growth Score Ranking ===")
        for i, (_, row) in enumerate(stocks_df.sort_values('growth_score', ascending=False).iterrows(), 1):
            print(f"{i}. {row['ticker']} - Score: {row['growth_score']:.1f}/100 - ${row['price']:.2f}")
    
    return results

def find_real_small_cap_growth():
    """Find real small-cap growth stocks under $20 with a smaller test set"""
    print("\n=== Finding Real Small-Cap Growth Stocks ===")
    
    # Use a smaller list of tickers to test
    # These are some tickers from Russell 2000 small-cap index
    test_universe = [
        # Biotech/Healthcare
        "RXRX", "NBIX", "MGLN", "NBIS", "NVAX", "SGEN", "HALO", "INO", "SRPT", 
        # Technology
        "APPS", "DDOG", "CRWD", "NET", "TWLO", "ZS",
        # Fintech
        "SOFI", "AFRM", "UPST", "LC", "HOOD",
        # Green Energy
        "ENPH", "SEDG", "SPWR", "FSLR", "BE", "PLUG",
        # Others
        "PTON", "ABNB", "DASH", "RBLX", "U", "CVNA", "ME", "DNA", 
        "JOBY", "IONQ", "OUST", "DM"
    ]
    
    results = []
    max_price = 20  # Only stocks under $20
    
    print(f"Testing {len(test_universe)} potential growth stocks...")
    
    for ticker in test_universe:
        try:
            metrics = get_simplified_growth_metrics(ticker)
            if metrics and metrics['price'] <= max_price and metrics['price'] > 0:
                results.append(metrics)
                print(f"Found {ticker} at ${metrics['price']:.2f} with growth score {metrics['growth_score']:.1f}")
        except Exception as e:
            print(f"Error with {ticker}: {e}")
    
    if results:
        # Convert to DataFrame
        stocks_df = pd.DataFrame(results)
        
        # Sort by growth score
        stocks_df = stocks_df.sort_values('growth_score', ascending=False)
        
        # Take top 10
        top_stocks = stocks_df.head(10)
        
        # Generate memo
        memo = generate_growth_memo(top_stocks)
        
        # Save the memo to a file
        output_file = "small_cap_growth_stocks.md"
        with open(output_file, "w") as f:
            f.write(memo)
        
        print(f"\nFound {len(stocks_df)} stocks under ${max_price}")
        print(f"Top results saved to {output_file}")
    else:
        print("No suitable growth stocks found.")
    
    return results

if __name__ == "__main__":
    print("=== GROWTH STOCK SCREENER TEST ===")
    
    # Test specific stocks first
    test_specific_stocks()
    
    # Find real small-cap growth stocks
    find_real_small_cap_growth()
    
    print("\n=== Test completed! ===")
    print("Run with full universe: ./run_buffett_screener.sh --growth") 