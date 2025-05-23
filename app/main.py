import streamlit as st
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend which doesn't require a display
import matplotlib.pyplot as plt
import yfinance as yf
import io
import base64
import sys
import os
from datetime import date, timedelta, datetime

# Add the parent directory to the Python path to import src modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.scoring.buffett import get_f_score
    from src.technical.core import get_sma
    from src.risk.position import position_size
    from src.utils.universe import get_universe_tickers, get_sp500_tickers, get_nasdaq_tickers
except ImportError as e:
    st.error(f"Error importing modules: {e}. Make sure the project is installed or PYTHONPATH is set correctly.")
    sys.exit(1)

# Page configuration
st.set_page_config(
    page_title="Buffett Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #2e3440;
        border-radius: 5px;
        padding: 12px;
        margin: 5px 0px;
        color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #0d3b66;
    }
    .stock-card {
        border: 1px solid #404756;
        border-radius: 8px;
        padding: 15px;
        margin: 15px 0px;
        background-color: #1f2937;
    }
    .chart-container {
        border: 1px solid #404756;
        border-radius: 8px;
        padding: 10px;
        background-color: #2e3440;
    }
    .positive {
        color: #a3be8c;
    }
    .negative {
        color: #bf616a;
    }
</style>
""", unsafe_allow_html=True)

# Cache functions for performance
@st.cache_data(ttl=3600)
def get_stocks_data(universe="SP500", max_price=None, min_price=None, min_f_score=None, demo=False):
    """Get stock data based on selected universe and filters"""
    if demo:
        # Mock data for demo mode
        data = {
            'score': [8, 7, 9, 6, 8],
            'close': [120, 45, 210, 33, 88],
            'atr': [2.5, 1.2, 3.8, 0.9, 1.7],
            'name': ['Apple Inc.', 'Ford Motor', 'Amazon', 'SoFi', 'Snap'],
            'market_cap': [2_500_000_000_000, 60_000_000_000, 1_800_000_000_000, 8_000_000_000, 20_000_000_000],
            'pe_ratio': [28, 12, 60, 18, 22],
            'dividend_yield': [0.006, 0.02, 0, 0, 0],
            'beta': [1.2, 1.1, 1.3, 1.5, 1.8],
            '52w_high': [180, 55, 220, 40, 95],
            '52w_low': [110, 35, 190, 25, 70],
        }
        index = ['AAPL', 'F', 'AMZN', 'SOFI', 'SNAP']
        df = pd.DataFrame(data, index=index)
        # Apply filters
        if min_f_score is not None:
            df = df[df['score'] >= min_f_score]
        if min_price is not None:
            df = df[df['close'] >= min_price]
        if max_price is not None:
            df = df[df['close'] <= max_price]
        return df.sort_values('score', ascending=False)
        
    try:
        # Get tickers based on selected universe
        if universe == "SP500":
            tickers = get_sp500_tickers()
        elif universe == "NASDAQ":
            tickers = get_nasdaq_tickers()
        elif universe == "RUSSELL2000":
            tickers = get_universe_tickers("RUSSELL2000")
        elif universe == "ALL":
            tickers = get_universe_tickers("ALL")
        else:
            tickers = universe.split(",")
        
        if not tickers:
            st.warning(f"No tickers found for {universe}. Using mock data instead.")
            return get_stocks_data(universe, max_price, min_price, min_f_score, demo=True)
            
        # Get F-scores
        scores = get_f_score(universe)
        
        if scores.empty:
            st.warning(f"No F-scores available for {universe}. Using mock data instead.")
            return get_stocks_data(universe, max_price, min_price, min_f_score, demo=True)
        
        # Apply filters
        if min_f_score is not None:
            scores = scores[scores['score'] >= min_f_score]
        
        if min_price is not None:
            scores = scores[scores['close'] >= min_price]
            
        if max_price is not None:
            scores = scores[scores['close'] <= max_price]
        
        if scores.empty:
            st.warning("No stocks match your criteria. Consider relaxing your filters.")
            # Return a subset of mock data that would match the criteria
            return get_stocks_data(universe, max_price, min_price, min_f_score, demo=True)
        
        # Fetch additional metrics for each stock
        metrics = pd.DataFrame(index=scores.index)
        for ticker in scores.index:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                metrics.loc[ticker, 'name'] = info.get('shortName', ticker)
                metrics.loc[ticker, 'sector'] = info.get('sector', 'Unknown')
                metrics.loc[ticker, 'industry'] = info.get('industry', 'Unknown')
                metrics.loc[ticker, 'market_cap'] = info.get('marketCap', 0)
                metrics.loc[ticker, 'pe_ratio'] = info.get('trailingPE', 0)
                metrics.loc[ticker, 'price'] = info.get('currentPrice', scores.loc[ticker, 'close'])
                metrics.loc[ticker, 'dividend_yield'] = info.get('dividendYield', 0)
                metrics.loc[ticker, 'beta'] = info.get('beta', 0)
                metrics.loc[ticker, '52w_high'] = info.get('fiftyTwoWeekHigh', 0)
                metrics.loc[ticker, '52w_low'] = info.get('fiftyTwoWeekLow', 0)
            except Exception as e:
                st.error(f"Error fetching data for {ticker}: {e}")
                continue
        
        # Merge scores with metrics
        result = pd.concat([scores, metrics], axis=1)
        return result.sort_values('score', ascending=False)
    except Exception as e:
        st.error(f"Error retrieving stock data: {e}")
        return get_stocks_data(universe, max_price, min_price, min_f_score, demo=True)

@st.cache_data(ttl=3600)
def get_stock_chart(ticker, period="6mo", demo=False):
    """Get stock chart data and generate image"""
    if demo:
        # Return a simple mock chart (blank or with random data)
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(30)
        y = np.random.normal(100, 5, size=30)
        ax.plot(x, y)
        ax.set_title(f"{ticker} - Demo Chart")
        ax.set_ylabel("Price ($)")
        ax.grid(True, alpha=0.3)
        buffer = io.BytesIO()
        plt.tight_layout()
        fig.savefig(buffer, format='png')
        buffer.seek(0)
        plt.close(fig)
        return base64.b64encode(buffer.read()).decode()
    stock = yf.Ticker(ticker)
    hist = stock.history(period=period)
    if hist.empty:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(hist.index, hist['Close'])
    ax.set_title(f"{ticker} - {period} Price History")
    ax.set_ylabel("Price ($)")
    ax.grid(True, alpha=0.3)
    
    # Add SMA lines
    hist['SMA50'] = hist['Close'].rolling(window=50).mean()
    hist['SMA200'] = hist['Close'].rolling(window=200).mean()
    ax.plot(hist.index, hist['SMA50'], 'r--', alpha=0.7, label='50-day SMA')
    ax.plot(hist.index, hist['SMA200'], 'b--', alpha=0.7, label='200-day SMA')
    ax.legend()
    
    # Save to buffer and return as base64
    buffer = io.BytesIO()
    plt.tight_layout()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close(fig)
    
    return base64.b64encode(buffer.read()).decode()

def calculate_position_sizes(stocks_df, buying_power, risk_pct):
    """Calculate suggested position size for each stock"""
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
    return positions

def parse_custom_tickers(text):
    """Parse custom ticker input"""
    return [t.strip().upper() for t in text.replace(',', ' ').split() if t.strip()]

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

# Main App
def main():
    # Header
    st.markdown('<p class="main-header">Buffett Screener</p>', unsafe_allow_html=True)
    
    # Sidebar - Settings and Filters
    st.sidebar.title("Settings")
    
    # Account Settings
    buying_power = st.sidebar.number_input("Buying Power ($)", min_value=1000, max_value=10_000_000, value=41000, step=1000)
    risk_pct = st.sidebar.slider("Risk % per Position", min_value=0.1, max_value=5.0, value=1.0, step=0.1) / 100
    
    # Add Demo Mode toggle to sidebar
    demo_mode = st.sidebar.checkbox("Demo Mode (Instant Mock Data)", value=False)
    
    # Universe Selection
    universe_options = {
        "SP500": "S&P 500",
        "NASDAQ": "NASDAQ 100",
        "RUSSELL2000": "Russell 2000",
        "ALL": "All Markets (S&P 500 + NASDAQ + Russell 2000)",
        "CUSTOM": "Custom List",
        "MOCK_AFFORDABLE": "Mock Affordable Stocks (Demo)"
    }
    selected_universe = st.sidebar.selectbox("Select Universe", list(universe_options.keys()), format_func=lambda x: universe_options[x])
    
    # Custom universe input
    custom_universe = None
    if selected_universe == "CUSTOM":
        custom_tickers_input = st.sidebar.text_area("Enter tickers separated by commas", "AAPL, MSFT, GOOG")
        custom_universe = parse_custom_tickers(custom_tickers_input)
        if not custom_universe:
            st.sidebar.error("Please enter at least one valid ticker")
            return
    
    # Filters
    st.sidebar.title("Filters")
    
    # F-Score Slider
    min_f_score = st.sidebar.slider("Minimum F-Score", min_value=1, max_value=9, value=7)
    
    # Price Range Slider
    min_price, max_price = st.sidebar.slider("Price Range ($)", min_value=1, max_value=1000, value=(1, 1000))
    
    # More advanced filters (hidden by default)
    advanced_filters = st.sidebar.expander("Advanced Filters", expanded=False)
    with advanced_filters:
        min_dividend = st.slider("Minimum Dividend Yield (%)", min_value=0.0, max_value=10.0, value=0.0, step=0.5)
        max_pe = st.slider("Maximum P/E Ratio", min_value=1, max_value=100, value=50, step=1)
        
    # Run the screener
    if st.button("Run Scanner", key="run_scanner_button"):
        with st.spinner("Loading data and analyzing stocks..."):
            # Get stock data based on specified criteria
            stocks_df = get_stocks_data(
                universe=selected_universe if selected_universe != "CUSTOM" else ",".join(custom_universe) if "custom_universe" in locals() else "MOCK_AFFORDABLE",
                max_price=max_price,
                min_price=min_price,
                min_f_score=min_f_score,
                demo=demo_mode
            )
            
            # If we got results, display them
            if not stocks_df.empty:
                # Calculate position sizes
                positions = calculate_position_sizes(stocks_df, buying_power, risk_pct)
                
                # Display results
                st.subheader("Top Stocks by F-Score")
                
                # Display the top 5 stocks
                for ticker in stocks_df.head(5).index:
                    # Get position information
                    position_info = positions.get(ticker, {})
                    shares = position_info.get('shares', 0)
                    dollars = position_info.get('dollars', 0)
                    percentage = position_info.get('percentage', 0)
                    
                    # Create a card for each stock
                    with st.container():
                        st.markdown(f"<div class='stock-card'>", unsafe_allow_html=True)
                        
                        # Stock header
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            stock_name = stocks_df.loc[ticker, 'name'] if 'name' in stocks_df.columns and not pd.isna(stocks_df.loc[ticker, 'name']) else ticker
                            st.markdown(f"### {ticker} - {stock_name}")
                            st.markdown(f"**F-Score:** {int(stocks_df.loc[ticker, 'score'])}/9")
                        
                        with col2:
                            st.metric("Current Price", f"${stocks_df.loc[ticker, 'close']:.2f}")
                        
                        with col3:
                            st.metric("Suggested Position", f"{shares} shares (${dollars:,.2f})")
                        
                        # Stock charts and metrics
                        col1, col2 = st.columns([1, 1])
                        
                        with col1:
                            # Display the stock chart
                            chart_data = get_stock_chart(ticker, period="6mo", demo=demo_mode)
                            if chart_data:
                                st.markdown(f"<div class='chart-container'><img src='data:image/png;base64,{chart_data}' style='width:100%'></div>", unsafe_allow_html=True)
                        
                        with col2:
                            # Metrics
                            metrics_data = [
                                ("Market Cap", format_large_number(stocks_df.loc[ticker, 'market_cap']) if 'market_cap' in stocks_df.columns else "N/A"),
                                ("P/E Ratio", f"{stocks_df.loc[ticker, 'pe_ratio']:.1f}" if 'pe_ratio' in stocks_df.columns and not pd.isna(stocks_df.loc[ticker, 'pe_ratio']) else "N/A"),
                                ("Dividend Yield", f"{stocks_df.loc[ticker, 'dividend_yield']*100:.2f}%" if 'dividend_yield' in stocks_df.columns and not pd.isna(stocks_df.loc[ticker, 'dividend_yield']) else "0.00%"),
                                ("Beta", f"{stocks_df.loc[ticker, 'beta']:.2f}" if 'beta' in stocks_df.columns and not pd.isna(stocks_df.loc[ticker, 'beta']) else "N/A"),
                                ("Portfolio %", f"{percentage:.1f}%"),
                                ("ATR", f"${stocks_df.loc[ticker, 'atr']:.2f}")
                            ]
                            
                            # Create a grid of metrics
                            metric_cols = st.columns(2)
                            for i, (label, value) in enumerate(metrics_data):
                                with metric_cols[i % 2]:
                                    st.markdown(f"<div class='metric-card'><span style='font-weight:bold'>{label}</span><br>{value}</div>", unsafe_allow_html=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                
                # Show full results table
                with st.expander("View Full Results Table", expanded=False):
                    st.dataframe(stocks_df)
            else:
                st.warning("No stocks found matching your criteria. Try adjusting your filters.")
    else:
        # Show placeholder messaging
        if st.session_state.get('has_run_scanner', False) == False:
            st.info("Adjust the filters in the sidebar, then click 'Run Scanner' to find stocks.")
            st.session_state['has_run_scanner'] = True

# Run the app
if __name__ == "__main__":
    main() 