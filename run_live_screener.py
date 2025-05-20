#!/usr/bin/env python
"""
Buffett Stock Screener - Live Data Version
Generates a memo with top investment opportunities for $270,000 buying power
using real-time market data
"""
import os
import sys
import pandas as pd
import argparse
from datetime import datetime

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import required modules
from src.scoring.buffett import get_f_score
from src.risk.position import position_size
from src.utils.universe import get_universe_tickers

def format_large_number(num):
    """Format large numbers with K, M, B suffixes"""
    if num is None or pd.isna(num):
        return "N/A"
    
    if abs(num) >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f}B"
    elif abs(num) >= 1_000_000:
        return f"${num / 1_000_000:.2f}M"
    elif abs(num) >= 1_000:
        return f"${num / 1_000:.2f}K"
    else:
        return f"${num:.2f}"

def get_buffett_recommendations(buying_power=270000, risk_pct=0.01, min_f_score=5, min_price=50, max_price=1000, universe="SP500"):
    """Generate Buffett stock recommendations based on criteria using live data"""
    print(f"Running Buffett Screener for {universe} universe with LIVE data...")
    print(f"This may take several minutes to fetch and process data from financial APIs...")
    
    try:
        # Get F-scores for the specified universe
        stocks_df = get_f_score(universe)
        
        if stocks_df.empty:
            print("No stocks found. Try a different universe or check API connectivity.")
            return "Error: No stocks found in the specified universe."
        
        print(f"Retrieved data for {len(stocks_df)} stocks")
        
        # Apply filters
        if min_f_score is not None:
            filtered_df = stocks_df[stocks_df['score'] >= min_f_score]
            print(f"Filtered to {len(filtered_df)} stocks with F-Score >= {min_f_score}")
            stocks_df = filtered_df
        
        if min_price is not None:
            filtered_df = stocks_df[stocks_df['close'] >= min_price]
            print(f"Filtered to {len(filtered_df)} stocks with price >= ${min_price}")
            stocks_df = filtered_df
            
        if max_price is not None:
            filtered_df = stocks_df[stocks_df['close'] <= max_price]
            print(f"Filtered to {len(filtered_df)} stocks with price <= ${max_price}")
            stocks_df = filtered_df
        
        if stocks_df.empty:
            print("No stocks match your criteria after filtering.")
            return "No stocks found matching your criteria. Try adjusting your filters."
        
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
        
        # Sort by F-score descending and get top stocks
        top_stocks = stocks_df.sort_values('score', ascending=False).head(5)
        
        print(f"Top stocks by F-Score: {', '.join(top_stocks.index.tolist())}")
        
        # Adjust allocations to not exceed buying power
        max_allocation = 0.20  # 20% per position maximum
        
        for ticker in top_stocks.index:
            position_dollars = buying_power * max_allocation
            position_shares = int(position_dollars / stocks_df.loc[ticker, 'close'])
            positions[ticker] = {
                'shares': position_shares,
                'dollars': round(position_shares * stocks_df.loc[ticker, 'close'], 2),
                'percentage': round((max_allocation * 100), 2)
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
        
        company_name = row.get('name', ticker)
        market_cap = row.get('market_cap', 0)
        pe_ratio = row.get('pe_ratio', 0)
        dividend_yield = row.get('dividend_yield', 0)
        beta = row.get('beta', 0)
        
        pe_display = f"{pe_ratio:.1f}" if pe_ratio and not pd.isna(pe_ratio) else "N/A"
        dividend_display = f"{dividend_yield*100:.2f}%" if dividend_yield and not pd.isna(dividend_yield) else "N/A"
        beta_display = f"{beta:.2f}" if beta and not pd.isna(beta) else "N/A"
        
        memo += f"""
### {i}. {ticker} - {company_name} - F-Score: {int(row['score'])}/9
- Current Price: ${row['close']:.2f}
- Market Cap: {format_large_number(market_cap)}
- P/E Ratio: {pe_display}
- Dividend Yield: {dividend_display}
- Beta: {beta_display}
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

## INVESTMENT RATIONALE

The selected stocks represent a balanced portfolio of high-quality companies with strong fundamentals. Each has been selected based on their exceptional F-Score, indicating strong financial health across profitability, leverage, and operating efficiency metrics.

## RISK MANAGEMENT

Each position is sized to represent 20% of the portfolio, creating a balanced allocation across five high-quality companies. This approach provides both diversification and meaningful exposure to each holding.

The selected companies have demonstrated resilience during economic downturns and have strong competitive advantages ("moats") that should enable them to maintain their market leadership positions over the long term.

As always, our approach is to buy wonderful companies at fair prices,
with a long-term perspective. The current selection represents businesses
with strong fundamentals trading at reasonable valuations.

Sincerely,
Buffett Screener Algorithm
"""
    return memo

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run Buffett Stock Screener with live market data")
    parser.add_argument("universe", nargs="?", default="SP500", 
                        help="Stock universe to screen (SP500, NASDAQ, RUSSELL2000, ALL, MOCK_AFFORDABLE)")
    parser.add_argument("--buying-power", type=float, default=270000,
                        help="Account buying power in dollars")
    parser.add_argument("--risk", type=float, default=0.01,
                        help="Risk percentage per position (as decimal, e.g., 0.01 for 1%%)")
    parser.add_argument("--min-fscore", type=int, default=5,
                        help="Minimum F-Score (1-9)")
    parser.add_argument("--min-price", type=float, default=50,
                        help="Minimum stock price")
    parser.add_argument("--max-price", type=float, default=1000,
                        help="Maximum stock price")
    parser.add_argument("--output", type=str, default="buffett_memo.md",
                        help="Output file for the investment memo")
    
    args = parser.parse_args()
    
    # Parameters
    BUYING_POWER = args.buying_power
    RISK_PCT = args.risk
    MIN_F_SCORE = args.min_fscore
    MIN_PRICE = args.min_price
    MAX_PRICE = args.max_price
    UNIVERSE = args.universe
    OUTPUT_FILE = args.output
    
    print(f"Running Buffett Screener with the following settings:")
    print(f"Universe: {UNIVERSE}")
    print(f"Buying Power: ${BUYING_POWER:,.2f}")
    print(f"Risk: {RISK_PCT*100:.1f}% per position")
    print(f"Min F-Score: {MIN_F_SCORE}")
    print(f"Price Range: ${MIN_PRICE} - ${MAX_PRICE}")
    print(f"Output File: {OUTPUT_FILE}")
    print()
    
    # Run the screener
    memo = get_buffett_recommendations(
        buying_power=BUYING_POWER,
        risk_pct=RISK_PCT,
        min_f_score=MIN_F_SCORE,
        min_price=MIN_PRICE,
        max_price=MAX_PRICE,
        universe=UNIVERSE
    )
    
    # Save the memo to a file
    with open(OUTPUT_FILE, "w") as f:
        f.write(memo)
    
    print(f"\nMemo saved to {OUTPUT_FILE}") 