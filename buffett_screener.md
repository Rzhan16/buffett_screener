🎯  Goal  
Nightly & intraday screener: Valinvest F-score ≥7 + SMA-200 momentum,
FinGPT-2 explanations, ATR/percent-risk sizing, Alpaca paper orders,
vectorbt back-test, Streamlit dashboard.

Folder map  
src/ code | app/ dashboard | tests/ | configs/ YAML modes | reports/

Data flow  
1. FMP API: Fundamental data fetched with 24-hour SQLite caching
2. Technical indicators via pandas-ta with price data
3. F-score calculation and SMA-200 momentum filter
4. Risk calculation and position sizing
5. Results to dashboard and trading signals
6. src/scoring/buffett.py caches daily F-Scores (Valinvest wrapper)
