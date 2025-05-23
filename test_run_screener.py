#!/usr/bin/env python
"""
Test script to run the stock screener and verify it works
Uses mock data by default to ensure consistent results
"""
import os
import sys
import pandas as pd

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import from the run_live_screener.py script
from run_live_screener import get_buffett_recommendations

def test_with_mock_data():
    """Test the stock screener with mock data"""
    print("\n=== Testing Buffett Screener with Mock Data ===")
    
    # Default values for testing
    buying_power = 41000
    risk_pct = 0.01  # 1% risk per position
    min_f_score = 5
    min_price = 1
    max_price = 1000
    
    # Run with mock data
    memo = get_buffett_recommendations(
        buying_power=buying_power,
        risk_pct=risk_pct,
        min_f_score=min_f_score,
        min_price=min_price,
        max_price=max_price,
        universe="MOCK_AFFORDABLE"  # Use mock data
    )
    
    # Save the memo to a file for inspection
    output_file = "test_memo_output.md"
    with open(output_file, "w") as f:
        f.write(memo)
    
    print(f"Test memo saved to {output_file}")
    print("✅ Test completed successfully!")

def test_with_different_parameters():
    """Test the stock screener with various parameter combinations"""
    print("\n=== Testing Buffett Screener with Different Parameters ===")
    
    test_cases = [
        {
            "name": "High F-Score Filter",
            "buying_power": 41000,
            "risk_pct": 0.01,
            "min_f_score": 8,
            "min_price": 1,
            "max_price": 1000,
            "universe": "MOCK_AFFORDABLE"
        },
        {
            "name": "Low Price Range",
            "buying_power": 41000,
            "risk_pct": 0.01,
            "min_f_score": 5,
            "min_price": 1,
            "max_price": 30,
            "universe": "MOCK_AFFORDABLE"
        },
        {
            "name": "High Price Range",
            "buying_power": 41000,
            "risk_pct": 0.01,
            "min_f_score": 5,
            "min_price": 30,
            "max_price": 1000,
            "universe": "MOCK_AFFORDABLE"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nRunning test case {i}: {case['name']}")
        
        # Run with case parameters
        memo = get_buffett_recommendations(
            buying_power=case["buying_power"],
            risk_pct=case["risk_pct"],
            min_f_score=case["min_f_score"],
            min_price=case["min_price"],
            max_price=case["max_price"],
            universe=case["universe"]
        )
        
        # Save the memo to a file for inspection
        output_file = f"test_memo_output_{i}.md"
        with open(output_file, "w") as f:
            f.write(memo)
        
        print(f"Test memo saved to {output_file}")
    
    print("\n✅ All test cases completed successfully!")

if __name__ == "__main__":
    print("=== BUFFETT SCREENER TEST SCRIPT ===")
    
    # Run tests
    test_with_mock_data()
    test_with_different_parameters()
    
    print("\n=== All tests completed! ===") 