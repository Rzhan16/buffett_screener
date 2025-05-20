#!/usr/bin/env python
"""
Debug script for Buffett Stock Screener
This script tests the stock screener with various configurations to identify issues
"""
import os
import sys
import pandas as pd
from datetime import datetime
import traceback

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    # Import required modules
    print("Importing modules...")
    from src.scoring.buffett import get_f_score
    from src.risk.position import position_size
    from src.utils.universe import get_universe_tickers
    print("Modules imported successfully!")
except Exception as e:
    print(f"Error importing modules: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

def test_universe_tickers():
    """Test getting tickers from different universes"""
    universes = ["SP500", "NASDAQ", "RUSSELL2000", "ALL"]
    
    print("\n=== Testing Universe Ticker Retrieval ===")
    for universe in universes:
        try:
            print(f"Getting tickers for {universe}...")
            tickers = get_universe_tickers(universe)
            print(f"✅ Found {len(tickers)} tickers for {universe}")
            print(f"Sample tickers: {', '.join(tickers[:5])}")
        except Exception as e:
            print(f"❌ Failed to get tickers for {universe}: {str(e)}")
            traceback.print_exc()

def test_f_score_calculation():
    """Test calculating F-scores for different universes"""
    universes = ["SP500", "NASDAQ", "MOCK_AFFORDABLE"]
    
    print("\n=== Testing F-Score Calculation ===")
    for universe in universes:
        try:
            print(f"Calculating F-scores for {universe}...")
            scores = get_f_score(universe)
            print(f"✅ Calculated F-scores for {universe}")
            print(f"Found {len(scores)} stocks with F-scores")
            if not scores.empty:
                print(f"Sample scores: {scores.head(3)}")
                print(f"Score range: {scores['score'].min()} to {scores['score'].max()}")
                print(f"Price range: ${scores['close'].min():.2f} to ${scores['close'].max():.2f}")
        except Exception as e:
            print(f"❌ Failed to calculate F-scores for {universe}: {str(e)}")
            traceback.print_exc()

def test_stock_filtering():
    """Test filtering stocks based on criteria"""
    test_cases = [
        {"universe": "MOCK_AFFORDABLE", "min_f_score": 5, "min_price": 1, "max_price": 1000, "name": "Default Filter"},
        {"universe": "MOCK_AFFORDABLE", "min_f_score": 8, "min_price": 1, "max_price": 1000, "name": "High F-Score"},
        {"universe": "MOCK_AFFORDABLE", "min_f_score": 5, "min_price": 30, "max_price": 50, "name": "Narrow Price Range"},
        {"universe": "NASDAQ", "min_f_score": 5, "min_price": 50, "max_price": 500, "name": "NASDAQ Mid-Cap"}
    ]
    
    print("\n=== Testing Stock Filtering ===")
    for case in test_cases:
        try:
            print(f"\nRunning test case: {case['name']}")
            stocks_df = get_f_score(case["universe"])
            
            if stocks_df.empty:
                print(f"❌ No stocks found for {case['universe']}.")
                continue
                
            print(f"Retrieved {len(stocks_df)} stocks from {case['universe']}")
            
            # Apply filters
            if case["min_f_score"] is not None:
                filtered_df = stocks_df[stocks_df['score'] >= case["min_f_score"]]
                print(f"Filtered to {len(filtered_df)} stocks with F-Score >= {case['min_f_score']}")
                stocks_df = filtered_df
            
            if case["min_price"] is not None:
                filtered_df = stocks_df[stocks_df['close'] >= case["min_price"]]
                print(f"Filtered to {len(filtered_df)} stocks with price >= ${case['min_price']}")
                stocks_df = filtered_df
                
            if case["max_price"] is not None:
                filtered_df = stocks_df[stocks_df['close'] <= case["max_price"]]
                print(f"Filtered to {len(filtered_df)} stocks with price <= ${case['max_price']}")
                stocks_df = filtered_df
            
            if stocks_df.empty:
                print(f"❌ No stocks match criteria for {case['name']} after filtering.")
            else:
                print(f"✅ Found {len(stocks_df)} stocks matching criteria for {case['name']}")
                print(f"Top stocks: {', '.join(stocks_df.sort_values('score', ascending=False).head(3).index.tolist())}")
        except Exception as e:
            print(f"❌ Failed test case {case['name']}: {str(e)}")
            traceback.print_exc()

def test_position_sizing():
    """Test position sizing calculations"""
    test_cases = [
        {"price": 100, "atr": 2, "account_size": 100000, "risk_pct": 0.01, "name": "Normal Stock"},
        {"price": 500, "atr": 10, "account_size": 100000, "risk_pct": 0.01, "name": "Expensive Stock"},
        {"price": 10, "atr": 0.5, "account_size": 100000, "risk_pct": 0.01, "name": "Cheap Stock"},
    ]
    
    print("\n=== Testing Position Sizing ===")
    for case in test_cases:
        try:
            print(f"\nRunning test case: {case['name']}")
            size = position_size(
                price=case["price"], 
                atr=case["atr"], 
                account_size=case["account_size"], 
                risk_pct=case["risk_pct"]
            )
            shares = int(size / case["price"]) if case["price"] > 0 else 0
            dollars = round(size, 2)
            percentage = round((dollars / case["account_size"]) * 100, 2)
            
            print(f"✅ Position size for {case['name']}:")
            print(f"   Shares: {shares}")
            print(f"   Dollars: ${dollars:,.2f}")
            print(f"   Percentage of Account: {percentage}%")
        except Exception as e:
            print(f"❌ Failed test case {case['name']}: {str(e)}")
            traceback.print_exc()

def run_streamlit_config_test():
    """Test if the current Streamlit configuration can run with the app settings"""
    print("\n=== Testing Streamlit Configuration ===")
    try:
        import importlib
        streamlit_spec = importlib.util.find_spec("streamlit")
        if streamlit_spec is None:
            print("❌ Streamlit is not installed.")
            return
            
        print("✅ Streamlit is installed.")
        
        # Check if the app directory exists
        app_dir = os.path.join(project_root, "app")
        main_py = os.path.join(app_dir, "main.py")
        
        if not os.path.exists(app_dir):
            print(f"❌ App directory not found: {app_dir}")
            return
            
        if not os.path.exists(main_py):
            print(f"❌ Main app file not found: {main_py}")
            return
            
        print(f"✅ App files found: {main_py}")
        
        # Check PYTHONPATH
        python_path = os.environ.get("PYTHONPATH", "")
        if project_root not in python_path and python_path:
            print(f"⚠️ Project root not in PYTHONPATH. Current PYTHONPATH: {python_path}")
        else:
            print("✅ PYTHONPATH configuration looks good.")
    except Exception as e:
        print(f"❌ Error testing Streamlit configuration: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    print("\n=== BUFFETT SCREENER DEBUG SCRIPT ===")
    print(f"Python version: {sys.version}")
    print(f"Project root: {project_root}")
    
    # Run tests
    test_universe_tickers()
    test_f_score_calculation()
    test_stock_filtering()
    test_position_sizing()
    run_streamlit_config_test()
    
    print("\n=== Debug tests completed ===") 