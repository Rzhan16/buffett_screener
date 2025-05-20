#!/usr/bin/env python
"""
Small-Cap Growth Stock Screener
Finds high-potential growth stocks under $20 with strong momentum and growth metrics
"""
import os
import sys
import pandas as pd
import argparse
from datetime import datetime, timedelta
import numpy as np
import yfinance as yf
import traceback

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import required modules
from src.utils.universe import get_universe_tickers
from src.risk.position import position_size

def get_growth_metrics(ticker):
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
        
        # Try to get financial metrics if available
        revenue_growth = info.get('revenueGrowth', None)
        earnings_growth = info.get('earningsGrowth', None)
        
        if revenue_growth is not None:
            revenue_growth = revenue_growth * 100  # Convert to percentage
            
        if earnings_growth is not None:
            earnings_growth = earnings_growth * 100  # Convert to percentage
        
        # Calculate volume ratio
        avg_volume = hist['Volume'].mean() if not hist.empty else 0
        recent_volume = hist['Volume'].tail(5).mean() if not hist.empty and len(hist) >= 5 else 0
        volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # Calculate volatility (standard deviation of daily returns)
        if not hist.empty and len(hist) > 5:
            daily_returns = hist['Close'].pct_change().dropna()
            volatility = daily_returns.std() * 100  # Convert to percentage
            
            # Also calculate ATR for position sizing
            high = hist['High']
            low = hist['Low']
            close_prev = hist['Close'].shift(1)
            
            tr1 = high - low
            tr2 = (high - close_prev).abs()
            tr3 = (low - close_prev).abs()
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean().iloc[-1]
        else:
            volatility = 5  # Default 5% if not enough data
            atr = current_price * 0.05  # Default to 5% of price
            
        # Calculate growth score (0-100)
        growth_score = 0
        
        # Momentum component (up to 50 points)
        if momentum_3m > 0:
            growth_score += min(momentum_3m, 30)  # Up to 30 points for 3-month momentum
        if momentum_1m > 0:
            growth_score += min(momentum_1m, 20)  # Up to 20 points for 1-month momentum
            
        # Volume component (up to 15 points)
        if volume_ratio > 1:
            growth_score += min((volume_ratio - 1) * 15, 15)  # Up to 15 points for increasing volume
            
        # Price component (up to 10 points)
        if 5 <= current_price <= 20:
            growth_score += 10  # Ideal price range gets full points
        elif current_price < 5:
            growth_score += current_price * 2  # 2 points per dollar under $5
            
        # Volatility component (up to 20 points)
        optimal_volatility = 25  # Optimal volatility for growth stocks (25%)
        volatility_score = 20 - abs(volatility - optimal_volatility) * 0.8
        growth_score += max(0, volatility_score)
        
        # Fundamental component (up to 25 points)
        if revenue_growth is not None and revenue_growth > 0:
            growth_score += min(revenue_growth * 0.5, 15)  # Up to 15 points for revenue growth
            
        if earnings_growth is not None and earnings_growth > 0:
            growth_score += min(earnings_growth * 0.5, 10)  # Up to 10 points for earnings growth
        
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
            'revenue_growth': revenue_growth,
            'earnings_growth': earnings_growth,
            'atr': atr
        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def find_growth_stocks(max_price=20, min_price=1, min_growth_score=50, universe="ALL", max_stocks=10):
    """Find growth stocks matching criteria"""
    print(f"Searching for growth stocks under ${max_price} with high potential...")
    print(f"This may take several minutes to fetch and process data from financial APIs...")
    
    try:
        # Get tickers from specified universe
        if universe == "SMALLCAP":
            # Could use a dedicated small-cap list here
            # For now, we'll use ALL and filter by market cap later
            tickers = get_universe_tickers("ALL")
        else:
            tickers = get_universe_tickers(universe)
            
        print(f"Retrieved {len(tickers)} tickers from {universe}")
        
        # Process stocks in batches
        results = []
        batch_size = 100
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1}...")
            
            batch_count = 0
            for ticker in batch:
                metrics = get_growth_metrics(ticker)
                if metrics and metrics['price'] >= min_price and metrics['price'] <= max_price:
                    results.append(metrics)
                    batch_count += 1
            
            # Show progress
            print(f"Found {batch_count} matching stocks in this batch ({len(results)} total)")
        
        # Convert to DataFrame
        if not results:
            return "No growth stocks found matching your criteria."
            
        stocks_df = pd.DataFrame(results)
        
        # Filter based on growth score
        if min_growth_score is not None:
            filtered_df = stocks_df[stocks_df['growth_score'] >= min_growth_score]
            print(f"Filtered to {len(filtered_df)} stocks with growth score >= {min_growth_score}")
            stocks_df = filtered_df
            
        if stocks_df.empty:
            return "No stocks matching your growth criteria after filtering."
            
        # Sort by growth score (descending)
        stocks_df = stocks_df.sort_values('growth_score', ascending=False)
        
        # Take top N stocks
        top_stocks = stocks_df.head(max_stocks)
        
        # Show top results
        print("\nTop Growth Stocks:")
        for i, (ticker, row) in enumerate(top_stocks.iterrows(), 1):
            price = row['price']
            score = row['growth_score']
            momentum = row['momentum_3m']
            print(f"{i}. {ticker}: ${price:.2f} - Growth Score: {score:.1f}/100 - 3M Momentum: {momentum:.1f}%")
        
        # Generate memo
        memo = generate_growth_memo(top_stocks)
        return memo
        
    except Exception as e:
        print(f"Error running growth screener: {e}")
        traceback.print_exc()
        return f"Error: {e}"

def generate_growth_memo(stocks_df, buying_power=50000):
    """Generate an investment memo for growth stocks"""
    now = datetime.now().strftime("%B %d, %Y")
    
    memo = f"""
# GROWTH STOCK RECOMMENDATIONS
## Date: {now}
## Account Value: ${buying_power:,}

Dear Investor,

After scanning the market for high-potential small-cap growth stocks,
I've identified the following opportunities that match your criteria for
stocks under $20 with strong growth metrics and momentum.

## TOP GROWTH RECOMMENDATIONS:

"""
    
    # Calculate position sizes
    # For growth stocks, we'll allocate equal amounts (e.g. 10% per position for 10 stocks)
    num_positions = len(stocks_df)
    position_pct = 1.0 / num_positions
    
    # Add each stock recommendation
    for i, (_, row) in enumerate(stocks_df.iterrows(), 1):
        ticker = row['ticker']
        price = row['price']
        
        # Calculate position
        position_dollars = buying_power * position_pct
        position_shares = int(position_dollars / price) if price > 0 else 0
        
        # Format metrics
        revenue_growth = f"{row['revenue_growth']:.1f}%" if pd.notna(row['revenue_growth']) else "N/A"
        earnings_growth = f"{row['earnings_growth']:.1f}%" if pd.notna(row['earnings_growth']) else "N/A"
        momentum_3m = f"{row['momentum_3m']:.1f}%" if pd.notna(row['momentum_3m']) else "N/A"
        momentum_1m = f"{row['momentum_1m']:.1f}%" if pd.notna(row['momentum_1m']) else "N/A"
        market_cap = f"${row['market_cap']/1000000000:.2f}B" if row['market_cap'] >= 1000000000 else f"${row['market_cap']/1000000:.2f}M"
        
        memo += f"""
### {i}. {ticker} - {row['name']} - Growth Score: {int(row['growth_score'])}/100
- Current Price: ${price:.2f}
- Market Cap: {market_cap}
- Sector: {row['sector']}
- Industry: {row['industry']}
- Revenue Growth: {revenue_growth}
- Earnings Growth: {earnings_growth}
- 3-Month Momentum: {momentum_3m}
- 1-Month Momentum: {momentum_1m}
- Suggested Position: {position_shares} shares (${position_shares * price:,.2f})
- Portfolio Allocation: {position_pct*100:.1f}% of capital
"""
    
    # Add investment rationale
    memo += f"""
## INVESTMENT RATIONALE

These growth-focused recommendations target companies with strong revenue growth, positive price momentum, and favorable
analyst sentiment. Unlike traditional value investments, these stocks offer higher upside potential but also come with
increased volatility and risk.

## RISK MANAGEMENT

Consider the following risk management strategies for these growth positions:
1. Position sizing is equal across all recommendations to limit single-stock exposure
2. Use stop-loss orders 10-15% below purchase price to limit downside
3. Consider scaling into positions over time rather than all at once
4. These should complement (not replace) your core value holdings

I've focused on finding stocks similar to your examples (NBIS, RXRX) with strong growth characteristics and prices
under $20 per share, emphasizing companies with promising fundamental and technical indicators.

"""
    return memo

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Find high-potential growth stocks under $20")
    parser.add_argument("--max-price", type=float, default=20,
                        help="Maximum stock price")
    parser.add_argument("--min-price", type=float, default=1,
                        help="Minimum stock price")
    parser.add_argument("--min-growth", type=float, default=50,
                        help="Minimum growth score (0-100)")
    parser.add_argument("--universe", type=str, default="ALL",
                        help="Stock universe to screen (SP500, NASDAQ, RUSSELL2000, ALL, SMALLCAP)")
    parser.add_argument("--max-stocks", type=int, default=10,
                        help="Maximum number of stocks to return")
    parser.add_argument("--output", type=str, default="growth_stocks.md",
                        help="Output file for the investment memo")
    
    args = parser.parse_args()
    
    print(f"Running Growth Stock Screener with the following settings:")
    print(f"Price Range: ${args.min_price} - ${args.max_price}")
    print(f"Minimum Growth Score: {args.min_growth}/100")
    print(f"Universe: {args.universe}")
    print(f"Maximum Stocks: {args.max_stocks}")
    print(f"Output File: {args.output}")
    print()
    
    # Run the screener
    memo = find_growth_stocks(
        max_price=args.max_price,
        min_price=args.min_price,
        min_growth_score=args.min_growth,
        universe=args.universe,
        max_stocks=args.max_stocks
    )
    
    # Save the memo to a file
    with open(args.output, "w") as f:
        f.write(memo)
    
    print(f"\nGrowth stock recommendations saved to {args.output}") 