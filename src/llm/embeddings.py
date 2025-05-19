"""
FinGPT-2 embeddings and explanations module.
"""
import os
import logging
from typing import Dict, Optional
import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM
import yfinance as yf

logger = logging.getLogger(__name__)

# Initialize model and tokenizer
MODEL_ID = "FinGPT/fingpt-sentiment-en"
tokenizer = None
model = None

def load_model():
    """Lazy load the FinGPT model."""
    global tokenizer, model
    if tokenizer is None or model is None:
        try:
            tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
            model = AutoModelForCausalLM.from_pretrained(MODEL_ID)
            logger.info("Loaded FinGPT model")
        except Exception as e:
            logger.error(f"Failed to load FinGPT model: {e}")
            raise

def fetch_fundamentals(symbol: str) -> Dict:
    """
    Fetch comprehensive fundamental data for a stock using yfinance.
    
    Parameters
    ----------
    symbol : str
        Stock ticker symbol
        
    Returns
    -------
    Dict
        Dictionary containing fundamental metrics
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Get financial statements for growth metrics
        income_stmt = ticker.income_stmt
        balance_sheet = ticker.balance_sheet
        cash_flow = ticker.cashflow
        
        # Calculate growth metrics if statements are available
        revenue_growth = None
        eps_growth = None
        fcf_growth = None
        
        if not income_stmt.empty and len(income_stmt.columns) >= 2:
            # Revenue growth (year-over-year)
            revenues = income_stmt.loc['Total Revenue']
            if len(revenues) >= 2:
                revenue_growth = (revenues.iloc[0] / revenues.iloc[1] - 1) * 100
            
            # EPS growth (year-over-year)
            eps = income_stmt.loc['Basic EPS'] if 'Basic EPS' in income_stmt.index else None
            if eps is not None and len(eps) >= 2:
                eps_growth = (eps.iloc[0] / eps.iloc[1] - 1) * 100
        
        if not cash_flow.empty and len(cash_flow.columns) >= 2:
            # Free Cash Flow growth
            if 'Free Cash Flow' in cash_flow.index:
                fcf = cash_flow.loc['Free Cash Flow']
                if len(fcf) >= 2:
                    fcf_growth = (fcf.iloc[0] / fcf.iloc[1] - 1) * 100
            else:
                # Calculate FCF as Operating Cash Flow - Capital Expenditures
                if 'Operating Cash Flow' in cash_flow.index and 'Capital Expenditure' in cash_flow.index:
                    ocf = cash_flow.loc['Operating Cash Flow']
                    capex = cash_flow.loc['Capital Expenditure']
                    if len(ocf) >= 2 and len(capex) >= 2:
                        fcf_current = ocf.iloc[0] + capex.iloc[0]  # CapEx is negative
                        fcf_previous = ocf.iloc[1] + capex.iloc[1]
                        if fcf_previous != 0:
                            fcf_growth = (fcf_current / fcf_previous - 1) * 100
        
        # Calculate ROE and ROA if balance sheet is available
        roe = None
        roa = None
        
        if not balance_sheet.empty and not income_stmt.empty:
            if 'Net Income' in income_stmt.index and 'Total Stockholder Equity' in balance_sheet.index:
                net_income = income_stmt.loc['Net Income'].iloc[0] if not income_stmt.loc['Net Income'].empty else None
                equity = balance_sheet.loc['Total Stockholder Equity'].iloc[0] if not balance_sheet.loc['Total Stockholder Equity'].empty else None
                if net_income is not None and equity is not None and equity != 0:
                    roe = (net_income / equity) * 100
            
            if 'Net Income' in income_stmt.index and 'Total Assets' in balance_sheet.index:
                net_income = income_stmt.loc['Net Income'].iloc[0] if not income_stmt.loc['Net Income'].empty else None
                assets = balance_sheet.loc['Total Assets'].iloc[0] if not balance_sheet.loc['Total Assets'].empty else None
                if net_income is not None and assets is not None and assets != 0:
                    roa = (net_income / assets) * 100
        
        # Compile all metrics
        return {
            # Valuation metrics
            'pe_ratio': info.get('trailingPE', 'N/A'),
            'pb_ratio': info.get('priceToBook', 'N/A'),
            'ps_ratio': info.get('priceToSalesTrailing12Months', 'N/A'),
            'ev_to_ebitda': info.get('enterpriseToEbitda', 'N/A'),
            
            # Profitability metrics
            'profit_margin': info.get('profitMargins', 'N/A'),
            'operating_margin': info.get('operatingMargins', 'N/A'),
            'roe': roe,
            'roa': roa,
            
            # Growth metrics
            'revenue_growth': revenue_growth,
            'eps_growth': eps_growth,
            'fcf_growth': fcf_growth,
            
            # Financial health metrics
            'current_ratio': info.get('currentRatio', 'N/A'),
            'quick_ratio': info.get('quickRatio', 'N/A'),
            'debt_to_equity': info.get('debtToEquity', 'N/A'),
            
            # Dividend metrics
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'payout_ratio': info.get('payoutRatio', 'N/A'),
            
            # Market metrics
            'market_cap': info.get('marketCap', 'N/A'),
            'beta': info.get('beta', 'N/A')
        }
    except Exception as e:
        logger.error(f"Failed to fetch fundamentals for {symbol}: {e}")
        return {
            'pe_ratio': 'N/A',
            'pb_ratio': 'N/A',
            'ps_ratio': 'N/A',
            'ev_to_ebitda': 'N/A',
            'profit_margin': 'N/A',
            'operating_margin': 'N/A',
            'roe': 'N/A',
            'roa': 'N/A',
            'revenue_growth': 'N/A',
            'eps_growth': 'N/A',
            'fcf_growth': 'N/A',
            'current_ratio': 'N/A',
            'quick_ratio': 'N/A',
            'debt_to_equity': 'N/A',
            'dividend_yield': 'N/A',
            'payout_ratio': 'N/A',
            'market_cap': 'N/A',
            'beta': 'N/A'
        }

def explain_with_fingpt(symbol: str) -> str:
    """
    Generate explanation for a stock using FinGPT-2.
    
    Parameters
    ----------
    symbol : str
        Stock symbol to explain
        
    Returns
    -------
    str
        Generated explanation
    """
    try:
        load_model()
        
        # Get real fundamental data
        fundamentals = fetch_fundamentals(symbol)
        
        # Construct prompt with comprehensive fundamentals
        prompt = f"""
        Analyze {symbol} stock based on these fundamentals:
        
        Valuation:
        - P/E Ratio: {fundamentals['pe_ratio']}
        - P/B Ratio: {fundamentals['pb_ratio']}
        - P/S Ratio: {fundamentals['ps_ratio']}
        - EV/EBITDA: {fundamentals['ev_to_ebitda']}
        
        Profitability:
        - Profit Margin: {fundamentals['profit_margin']}
        - Operating Margin: {fundamentals['operating_margin']}
        - Return on Equity: {fundamentals['roe']}
        - Return on Assets: {fundamentals['roa']}
        
        Growth:
        - Revenue Growth: {fundamentals['revenue_growth']}
        - EPS Growth: {fundamentals['eps_growth']}
        - Free Cash Flow Growth: {fundamentals['fcf_growth']}
        
        Financial Health:
        - Current Ratio: {fundamentals['current_ratio']}
        - Quick Ratio: {fundamentals['quick_ratio']}
        - Debt/Equity: {fundamentals['debt_to_equity']}
        
        Dividend:
        - Dividend Yield: {fundamentals['dividend_yield']}%
        - Payout Ratio: {fundamentals['payout_ratio']}
        
        Provide a comprehensive analysis of {symbol}'s investment potential:
        """
        
        # Generate explanation
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(
            inputs["input_ids"],
            max_length=300,  # Increased for more detailed analysis
            num_return_sequences=1,
            temperature=0.7,
            do_sample=True
        )
        
        explanation = tokenizer.decode(outputs[0], skip_special_tokens=True)
        return explanation.strip()
        
    except Exception as e:
        logger.error(f"Failed to generate explanation for {symbol}: {e}")
        return f"Failed to generate explanation: {str(e)}" 