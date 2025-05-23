#!/usr/bin/env python
"""
Buffett Value Stock Screener
Finds undervalued stocks with strong moats, good management, and financial strength
based on Warren Buffett's investment principles
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

def get_value_metrics(ticker):
    """Get value investing metrics for a stock based on Buffett principles"""
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
        
        # Get financial data
        try:
            balance_sheet = stock.balance_sheet
            income_stmt = stock.income_stmt
            cash_flow = stock.cashflow
        except:
            # If quarterly statements fail, try annual
            balance_sheet = stock.get_balance_sheet() if hasattr(stock, 'get_balance_sheet') else None
            income_stmt = stock.get_income_stmt() if hasattr(stock, 'get_income_stmt') else None
            cash_flow = stock.get_cashflow() if hasattr(stock, 'get_cashflow') else None
            
        # Calculate key Buffett metrics
        
        # 1. Profitability metrics
        roe = info.get('returnOnEquity', 0)  # Return on Equity
        roa = info.get('returnOnAssets', 0)  # Return on Assets
        gross_margin = info.get('grossMargins', 0)  # Gross Margins
        operating_margin = info.get('operatingMargins', 0)  # Operating Margins
        profit_margin = info.get('profitMargins', 0)  # Profit Margins
        
        # 2. Value metrics
        pe_ratio = info.get('trailingPE', float('inf'))  # Price-to-Earnings
        pb_ratio = info.get('priceToBook', float('inf'))  # Price-to-Book
        free_cash_flow_yield = 0  # Will calculate if data available
        
        # 3. Financial Strength
        debt_to_equity = info.get('debtToEquity', float('inf'))  # Debt-to-Equity
        current_ratio = 0  # Current Assets / Current Liabilities
        
        # 4. Competitive Advantage (Moat) indicators
        revenue_growth_5y = info.get('revenueGrowth', 0)  # Consistent growth is a moat indicator
        
        # Calculate current ratio from balance sheet if available
        if balance_sheet is not None and not balance_sheet.empty:
            if 'Total Current Assets' in balance_sheet.index and 'Total Current Liabilities' in balance_sheet.index:
                current_assets = balance_sheet.loc['Total Current Assets'].iloc[0]
                current_liabilities = balance_sheet.loc['Total Current Liabilities'].iloc[0]
                if current_liabilities != 0:
                    current_ratio = current_assets / current_liabilities
        
        # Calculate FCF yield if we have the data
        if cash_flow is not None and not cash_flow.empty and market_cap > 0:
            if 'Free Cash Flow' in cash_flow.index:
                free_cash_flow = cash_flow.loc['Free Cash Flow'].iloc[0]
                free_cash_flow_yield = (free_cash_flow / market_cap) * 100
                
            # If FCF not available directly, try to calculate it
            elif 'Operating Cash Flow' in cash_flow.index and 'Capital Expenditures' in cash_flow.index:
                operating_cash_flow = cash_flow.loc['Operating Cash Flow'].iloc[0]
                capex = abs(cash_flow.loc['Capital Expenditures'].iloc[0])
                free_cash_flow = operating_cash_flow - capex
                free_cash_flow_yield = (free_cash_flow / market_cap) * 100
        
        # Calculate Buffett Score (0-100)
        buffett_score = 0
        
        # 1. Financial Strength (0-25 points)
        financial_strength_score = 0
        
        # Debt to Equity: Lower is better (0-10 points)
        if debt_to_equity <= 0.3:
            financial_strength_score += 10
        elif debt_to_equity <= 0.5:
            financial_strength_score += 8
        elif debt_to_equity <= 0.8:
            financial_strength_score += 6
        elif debt_to_equity <= 1.0:
            financial_strength_score += 4
        elif debt_to_equity <= 1.5:
            financial_strength_score += 2
        
        # Current Ratio: Higher is better (0-5 points)
        if current_ratio >= 2.0:
            financial_strength_score += 5
        elif current_ratio >= 1.5:
            financial_strength_score += 4
        elif current_ratio >= 1.2:
            financial_strength_score += 3
        elif current_ratio >= 1.0:
            financial_strength_score += 2
            
        # Interest Coverage (using proxies if not directly available)
        interest_coverage_proxy = operating_margin
        if interest_coverage_proxy >= 0.20:  # 20% operating margin
            financial_strength_score += 5
        elif interest_coverage_proxy >= 0.15:
            financial_strength_score += 4
        elif interest_coverage_proxy >= 0.10:
            financial_strength_score += 3
        elif interest_coverage_proxy >= 0.05:
            financial_strength_score += 2
            
        # Free Cash Flow positivity (0-5 points)
        if free_cash_flow_yield > 7:
            financial_strength_score += 5
        elif free_cash_flow_yield > 5:
            financial_strength_score += 4
        elif free_cash_flow_yield > 3:
            financial_strength_score += 3
        elif free_cash_flow_yield > 0:
            financial_strength_score += 2
            
        buffett_score += financial_strength_score
            
        # 2. Profitability (0-25 points)
        profitability_score = 0
        
        # Return on Equity (0-10 points)
        if roe >= 0.20:  # 20%+ ROE
            profitability_score += 10
        elif roe >= 0.15:
            profitability_score += 8
        elif roe >= 0.12:
            profitability_score += 6
        elif roe >= 0.10:
            profitability_score += 4
        elif roe >= 0.08:
            profitability_score += 2
            
        # Profit Margins (0-10 points)  
        if profit_margin >= 0.20:  # 20%+ profit margin
            profitability_score += 10
        elif profit_margin >= 0.15:
            profitability_score += 8
        elif profit_margin >= 0.10:
            profitability_score += 6
        elif profit_margin >= 0.05:
            profitability_score += 4
        elif profit_margin > 0:
            profitability_score += 2
            
        # Gross Margin (0-5 points) - High margins indicate moat
        if gross_margin >= 0.50:  # 50%+ gross margin
            profitability_score += 5
        elif gross_margin >= 0.40:
            profitability_score += 4
        elif gross_margin >= 0.30:
            profitability_score += 3
        elif gross_margin >= 0.20:
            profitability_score += 2
        elif gross_margin > 0:
            profitability_score += 1
            
        buffett_score += profitability_score
        
        # 3. Moat/Competitive Advantage (0-25 points)
        moat_score = 0
        
        # Consistent revenue growth (0-5 points)
        if revenue_growth_5y >= 0.10:  # 10%+ growth
            moat_score += 5
        elif revenue_growth_5y >= 0.07:
            moat_score += 4
        elif revenue_growth_5y >= 0.05:
            moat_score += 3
        elif revenue_growth_5y > 0:
            moat_score += 2
            
        # Consistent profitability (using operating margin as proxy) (0-5 points)
        if operating_margin >= 0.25:
            moat_score += 5
        elif operating_margin >= 0.20:
            moat_score += 4
        elif operating_margin >= 0.15:
            moat_score += 3
        elif operating_margin >= 0.10:
            moat_score += 2
        elif operating_margin > 0:
            moat_score += 1
            
        # Brand strength (using market cap as proxy) (0-5 points)
        if market_cap >= 100000000000:  # $100B+
            moat_score += 5
        elif market_cap >= 50000000000:  # $50B+
            moat_score += 4
        elif market_cap >= 10000000000:  # $10B+
            moat_score += 3
        elif market_cap >= 1000000000:   # $1B+
            moat_score += 2
        else:
            moat_score += 1
                
        # Industry leadership (using arbitrary sector assignment) (0-10 points)
        # Favoring industries Buffett traditionally likes
        buffett_preferred_sectors = [
            'Financial Services', 'Consumer Defensive', 'Financial',
            'Consumer Cyclical', 'Communication Services', 'Industrials',
            'Insurance', 'Banking', 'Beverages', 'Retail'
        ]
        
        buffett_preferred_industries = [
            'Insurance', 'Banks', 'Beverages', 'Railroads', 'Credit Services',
            'Software', 'Consumer Packaged Goods', 'Financial Data & Stock Exchanges',
            'Retail', 'Oil & Gas', 'Transportation', 'Healthcare'
        ]
        
        # Check if in Buffett's preferred sectors/industries
        if sector in buffett_preferred_sectors:
            moat_score += 5
        if industry in buffett_preferred_industries:
            moat_score += 5
            
        buffett_score += moat_score
        
        # 4. Valuation (0-25 points)
        valuation_score = 0
        
        # P/E Ratio (0-10 points)
        if pe_ratio > 0:  # Must be profitable
            if pe_ratio <= 10:
                valuation_score += 10
            elif pe_ratio <= 15:
                valuation_score += 8
            elif pe_ratio <= 20:
                valuation_score += 6
            elif pe_ratio <= 25:
                valuation_score += 4
            elif pe_ratio <= 30:
                valuation_score += 2
                
        # P/B Ratio (0-5 points)
        if pb_ratio <= 1.0:
            valuation_score += 5
        elif pb_ratio <= 2.0:
            valuation_score += 4
        elif pb_ratio <= 3.0:
            valuation_score += 3
        elif pb_ratio <= 4.0:
            valuation_score += 2
        elif pb_ratio <= 5.0:
            valuation_score += 1
            
        # Free Cash Flow Yield (0-10 points)
        if free_cash_flow_yield >= 10:  # 10%+ FCF yield
            valuation_score += 10
        elif free_cash_flow_yield >= 7:
            valuation_score += 8
        elif free_cash_flow_yield >= 5:
            valuation_score += 6
        elif free_cash_flow_yield >= 3:
            valuation_score += 4
        elif free_cash_flow_yield > 0:
            valuation_score += 2
            
        buffett_score += valuation_score
        
        # Return metrics
        return {
            'ticker': ticker,
            'name': name,
            'price': current_price,
            'market_cap': market_cap,
            'sector': sector,
            'industry': industry,
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'debt_to_equity': debt_to_equity,
            'current_ratio': current_ratio,
            'roe': roe * 100 if roe else 0,  # Convert to percentage
            'roa': roa * 100 if roa else 0,  # Convert to percentage
            'gross_margin': gross_margin * 100 if gross_margin else 0,  # Convert to percentage
            'operating_margin': operating_margin * 100 if operating_margin else 0,  # Convert to percentage
            'profit_margin': profit_margin * 100 if profit_margin else 0,  # Convert to percentage
            'free_cash_flow_yield': free_cash_flow_yield,
            'revenue_growth': revenue_growth_5y * 100 if revenue_growth_5y else 0,  # Convert to percentage
            'buffett_score': buffett_score,
            'financial_strength_score': financial_strength_score,
            'profitability_score': profitability_score,
            'moat_score': moat_score,
            'valuation_score': valuation_score
        }
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def find_value_stocks(max_price=None, min_price=None, min_buffett_score=70, universe="SP500", max_stocks=10):
    """Find value stocks matching Buffett's criteria"""
    print(f"Searching for value stocks with strong Buffett characteristics...")
    print(f"This may take several minutes to fetch and process data from financial APIs...")
    
    try:
        # Get tickers from specified universe
        tickers = get_universe_tickers(universe)
        print(f"Retrieved {len(tickers)} tickers from {universe}")
        
        # Process stocks in batches
        results = []
        batch_size = 50
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1}...")
            
            batch_count = 0
            for ticker in batch:
                metrics = get_value_metrics(ticker)
                if metrics:
                    price_check = True
                    if min_price is not None and metrics['price'] < min_price:
                        price_check = False
                    if max_price is not None and metrics['price'] > max_price:
                        price_check = False
                        
                    if price_check:
                        results.append(metrics)
                        batch_count += 1
            
            # Show progress
            print(f"Found {batch_count} matching stocks in this batch ({len(results)} total)")
        
        # Convert to DataFrame
        if not results:
            return "No value stocks found matching your criteria."
            
        stocks_df = pd.DataFrame(results)
        
        # Filter based on Buffett score
        if min_buffett_score is not None:
            filtered_df = stocks_df[stocks_df['buffett_score'] >= min_buffett_score]
            print(f"Filtered to {len(filtered_df)} stocks with Buffett score >= {min_buffett_score}")
            stocks_df = filtered_df
            
        if stocks_df.empty:
            return "No stocks matching your value criteria after filtering."
            
        # Sort by Buffett score (descending)
        stocks_df = stocks_df.sort_values('buffett_score', ascending=False)
        
        # Take top N stocks
        top_stocks = stocks_df.head(max_stocks)
        
        # Show top results
        print("\nTop Value Stocks:")
        for i, row in enumerate(top_stocks.itertuples(), 1):
            price = row.price
            score = row.buffett_score
            pe = row.pe_ratio if row.pe_ratio != float('inf') else 'N/A'
            print(f"{i}. {row.ticker}: ${price:.2f} - Buffett Score: {score:.1f}/100 - P/E: {pe}")
        
        # Generate memo
        memo = generate_value_memo(top_stocks)
        return memo
        
    except Exception as e:
        print(f"Error running value screener: {e}")
        traceback.print_exc()
        return f"Error: {e}"

def generate_value_memo(stocks_df, buying_power=50000):
    """Generate an investment memo for value stocks"""
    now = datetime.now().strftime("%B %d, %Y")
    
    memo = f"""
# BUFFETT VALUE STOCK RECOMMENDATIONS
## Date: {now}
## Account Value: ${buying_power:,}

Dear Investor,

After analyzing the market using Warren Buffett's value investing principles,
I've identified the following opportunities that demonstrate solid financials,
competitive advantages, and reasonable valuations.

## TOP VALUE RECOMMENDATIONS:

"""
    
    # For value stocks, position size should be larger for higher conviction (higher scores)
    total_score = sum(row.buffett_score for row in stocks_df.itertuples())
    
    # Add each stock recommendation
    for i, row in enumerate(stocks_df.itertuples(), 1):
        ticker = row.ticker
        price = row.price
        
        # Calculate position based on Buffett score weighting
        position_weight = row.buffett_score / total_score if total_score > 0 else 1.0 / len(stocks_df)
        position_dollars = buying_power * position_weight
        position_shares = int(position_dollars / price) if price > 0 else 0
        
        # Format metrics
        pe_ratio = f"{row.pe_ratio:.1f}" if row.pe_ratio != float('inf') and pd.notna(row.pe_ratio) else "N/A"
        pb_ratio = f"{row.pb_ratio:.1f}" if row.pb_ratio != float('inf') and pd.notna(row.pb_ratio) else "N/A"
        roe = f"{row.roe:.1f}%" if pd.notna(row.roe) else "N/A"
        fcf_yield = f"{row.free_cash_flow_yield:.1f}%" if pd.notna(row.free_cash_flow_yield) else "N/A"
        market_cap = f"${row.market_cap/1000000000:.2f}B" if row.market_cap >= 1000000000 else f"${row.market_cap/1000000:.2f}M"
        
        memo += f"""
### {i}. {ticker} - {row.name} - Buffett Score: {int(row.buffett_score)}/100
- Current Price: ${price:.2f}
- Market Cap: {market_cap}
- P/E Ratio: {pe_ratio}
- P/B Ratio: {pb_ratio}
- Return on Equity: {roe}
- Free Cash Flow Yield: {fcf_yield}
- Debt to Equity: {row.debt_to_equity:.2f}
- Current Ratio: {row.current_ratio:.2f}
- Sector: {row.sector}
- Industry: {row.industry}

**Score Breakdown:**
- Financial Strength: {row.financial_strength_score}/25
- Profitability: {row.profitability_score}/25
- Moat/Competitive Advantage: {row.moat_score}/25
- Valuation: {row.valuation_score}/25

**Suggested Position:** {position_shares} shares (${position_shares * price:,.2f})
**Portfolio Allocation:** {position_weight*100:.1f}% of capital
"""
    
    # Add investment rationale
    memo += f"""
## INVESTMENT RATIONALE

These value-focused recommendations adhere to Warren Buffett's investment philosophy of buying wonderful companies
at fair prices. Key criteria include:

1. **Strong Financial Position** - Low debt, ample cash flow, and financial stability to weather economic storms
2. **Competitive Advantages** - Companies with sustainable moats protecting their business from competition
3. **Consistent Profitability** - High returns on equity and assets demonstrating operational excellence
4. **Reasonable Valuation** - Stocks trading at fair multiples relative to their intrinsic value
5. **Proven Management** - Companies with leadership that allocates capital efficiently

## PORTFOLIO CONSTRUCTION

This portfolio follows Buffett's concentrated approach:
- Highest-scoring companies receive larger allocations
- Focus on quality over diversification
- Long-term holding periods (potentially 5+ years)
- Higher allocations to companies with the strongest moats and balance sheets

## RISK MANAGEMENT

While these stocks exhibit strong Buffett characteristics, maintain prudent risk management:
1. Monitor for fundamental deterioration
2. Watch for increases in debt levels
3. Be alert to competitive threats to each company's moat
4. Potential economic and interest rate risks

Remember that even the best value investments require patience to fully realize their potential.

"""
    return memo

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Find stocks matching Warren Buffett's investment criteria")
    parser.add_argument("--max-price", type=float, default=None,
                        help="Maximum stock price (optional)")
    parser.add_argument("--min-price", type=float, default=None,
                        help="Minimum stock price (optional)")
    parser.add_argument("--min-buffett", type=float, default=70,
                        help="Minimum Buffett score (0-100)")
    parser.add_argument("--universe", type=str, default="SP500",
                        help="Stock universe to screen (SP500, NASDAQ, RUSSELL2000, ALL)")
    parser.add_argument("--max-stocks", type=int, default=10,
                        help="Maximum number of stocks to return")
    parser.add_argument("--output", type=str, default="value_stocks.md",
                        help="Output file for the investment memo")
    
    args = parser.parse_args()
    
    print(f"Running Buffett Value Stock Screener with the following settings:")
    print(f"Price Range: {'No minimum' if args.min_price is None else '$' + str(args.min_price)} - {'No maximum' if args.max_price is None else '$' + str(args.max_price)}")
    print(f"Minimum Buffett Score: {args.min_buffett}/100")
    print(f"Universe: {args.universe}")
    print(f"Maximum Stocks: {args.max_stocks}")
    print(f"Output File: {args.output}")
    print()
    
    # Run the screener
    memo = find_value_stocks(
        max_price=args.max_price,
        min_price=args.min_price,
        min_buffett_score=args.min_buffett,
        universe=args.universe,
        max_stocks=args.max_stocks
    )
    
    # Save the memo to a file
    with open(args.output, "w") as f:
        f.write(memo)
    
    print(f"\nValue stock recommendations saved to {args.output}") 