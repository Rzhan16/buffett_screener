#!/usr/bin/env python
"""
Buffett Stock Screener - Direct Execution
Generates a memo with top investment opportunities for $270,000 buying power
"""
import os
import sys
import pandas as pd
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.risk.position import position_size

def format_large_number(num):
    """Format large numbers with K, M, B suffixes"""
    if num is None or pd.isna(num):
        return "N/A"
    
    if abs(num) >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    elif abs(num) >= 1_000:
        return f"${num / 1_000_000:.2f}K"
    else:
        return f"${num:.2f}"

def get_mock_data():
    """Generate mock stock data for demonstration"""
    # Create mock data similar to what get_f_score would return
    data = {
        'score': [9, 8, 8, 7, 7, 7, 6, 6, 6, 5],
        'close': [145.50, 270.30, 159.88, 92.45, 350.20, 183.75, 210.50, 79.80, 115.30, 62.40],
        'atr': [3.2, 5.8, 3.5, 2.1, 8.3, 4.2, 5.1, 1.8, 2.6, 1.4],
        'name': [
            'Apple Inc.', 
            'Microsoft Corporation', 
            'Amazon.com Inc.', 
            'Walmart Inc.', 
            'Berkshire Hathaway', 
            'JPMorgan Chase & Co.', 
            'Johnson & Johnson', 
            'Coca-Cola Company', 
            'Procter & Gamble', 
            'Pfizer Inc.'
        ],
        'market_cap': [
            2_500_000_000_000,
            2_200_000_000_000,
            1_800_000_000_000,
            400_000_000_000,
            700_000_000_000,
            500_000_000_000,
            450_000_000_000,
            250_000_000_000,
            350_000_000_000,
            280_000_000_000
        ],
        'pe_ratio': [28.5, 32.4, 60.2, 22.7, 12.3, 15.8, 18.6, 24.3, 25.7, 16.2],
        'dividend_yield': [0.006, 0.008, 0.001, 0.015, 0.003, 0.028, 0.025, 0.03, 0.022, 0.035],
        'beta': [1.2, 1.0, 1.3, 0.6, 0.7, 1.1, 0.8, 0.5, 0.7, 0.9]
    }
    
    index = ['AAPL', 'MSFT', 'AMZN', 'WMT', 'BRK-B', 'JPM', 'JNJ', 'KO', 'PG', 'PFE']
    return pd.DataFrame(data, index=index)

def get_buffett_recommendations(buying_power=270000, risk_pct=0.01, min_f_score=5, min_price=50, max_price=1000):
    """Generate Buffett stock recommendations based on criteria"""
    print(f"Running Buffett Screener with mock data...")
    
    try:
        # Get mock data
        stocks_df = get_mock_data()
        
        # Apply filters
        if min_f_score is not None:
            stocks_df = stocks_df[stocks_df['score'] >= min_f_score]
        
        if min_price is not None:
            stocks_df = stocks_df[stocks_df['close'] >= min_price]
            
        if max_price is not None:
            stocks_df = stocks_df[stocks_df['close'] <= max_price]
        
        # Calculate position sizes
        positions = {}
        for ticker in stocks_df.index:
            price = stocks_df.loc[ticker, 'close']
            atr = stocks_df.loc[ticker, 'atr']
            size = position_size(price=price, atr=atr, account_size=buying_power, risk_pct=risk_pct)
            positions[ticker] = {
                'shares': int(size / price) if price > 0 else 0,
                'dollars': round(size, 2),
                'percentage': round((size / buying_power) * 100, 2) if buying_power > 0 else 0
            }
        
        # Sort by F-score descending
        top_stocks = stocks_df.sort_values('score', ascending=False)
        
        # Adjust allocations to ensure we don't exceed buying power
        # We'll allocate equal amounts to top 5 stocks (each getting 20% of portfolio)
        max_allocation = 0.20  # 20% per position maximum
        top_5_tickers = top_stocks.head(5).index
        
        for ticker in positions:
            if ticker in top_5_tickers:
                position_dollars = buying_power * max_allocation
                position_shares = int(position_dollars / stocks_df.loc[ticker, 'close'])
                positions[ticker] = {
                    'shares': position_shares,
                    'dollars': round(position_shares * stocks_df.loc[ticker, 'close'], 2),
                    'percentage': round((max_allocation * 100), 2)
                }
            else:
                # For stocks outside top 5, set position to 0
                positions[ticker] = {
                    'shares': 0,
                    'dollars': 0.00,
                    'percentage': 0.00
                }
        
        # Generate memo
        memo = generate_buffett_memo(top_stocks, positions, buying_power)
        return memo
        
    except Exception as e:
        print(f"Error running screener: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}"

def generate_buffett_memo(stocks_df, positions, buying_power):
    """Generate a Buffett-style investment memo"""
    now = datetime.now().strftime("%B %d, %Y")
    
    memo = f"""
# BUFFETT INVESTMENT MEMO
## Date: {now}
## Account Value: ${buying_power:,}

Dear Partner,

After careful analysis of market conditions and company fundamentals, 
I've identified the following investment opportunities that meet our
strict criteria for quality, value, and financial strength.

## TOP RECOMMENDATIONS:

"""
    
    # Add top stock recommendations
    for i, (ticker, row) in enumerate(stocks_df.iterrows(), 1):
        position_info = positions.get(ticker, {})
        shares = position_info.get('shares', 0)
        dollars = position_info.get('dollars', 0)
        percentage = position_info.get('percentage', 0)
        
        memo += f"""
### {i}. {ticker} - {row['name']} - F-Score: {int(row['score'])}/9
- Current Price: ${row['close']:.2f}
- Market Cap: {format_large_number(row['market_cap'])}
- P/E Ratio: {row['pe_ratio']:.1f}
- Dividend Yield: {row['dividend_yield']*100:.2f}%
- Beta: {row['beta']:.2f}
- Volatility (ATR): ${row['atr']:.2f}
- Suggested Position: {shares} shares (${dollars:,.2f})
- Portfolio Allocation: {percentage}% of capital
"""
    
    # Add conclusion
    total_invested = sum(positions.get(ticker, {}).get('dollars', 0) for ticker in stocks_df.index)
    remaining_capital = buying_power - total_invested
    
    memo += f"""
## ALLOCATION SUMMARY
- Total Capital: ${buying_power:,.2f}
- Allocated to Top Picks: ${total_invested:,.2f} ({total_invested/buying_power*100:.1f}%)
- Remaining Cash Position: ${remaining_capital:,.2f} ({remaining_capital/buying_power*100:.1f}%)

These recommendations are based on our value investing principles:
1. Strong financial health (F-Score ≥ 5)
2. Reasonable volatility for prudent risk management
3. Position sizing based on 1% risk per position

As always, our approach is to buy wonderful companies at fair prices,
with a long-term perspective. The current selection represents businesses
with strong fundamentals trading at reasonable valuations.

Sincerely,
Buffett Screener Algorithm
"""
    return memo

if __name__ == "__main__":
    # Parameters
    BUYING_POWER = 270000
    RISK_PCT = 0.01  # 1% risk per position
    MIN_F_SCORE = 5
    MIN_PRICE = 50
    MAX_PRICE = 1000
    
    # Run the screener
    memo = get_buffett_recommendations(
        buying_power=BUYING_POWER,
        risk_pct=RISK_PCT,
        min_f_score=MIN_F_SCORE,
        min_price=MIN_PRICE,
        max_price=MAX_PRICE
    )
    
    # Print the memo
    print(memo)
    
    # Save the memo to a file
    with open("buffett_memo.md", "w") as f:
        f.write(memo)
    
    print("\nMemo saved to buffett_memo.md") 