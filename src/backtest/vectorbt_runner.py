"""
Backtest runner using vectorbt for Buffett + momentum strategies.
"""
import os
import time
import numpy as np
import pandas as pd
import vectorbt as vbt
from typing import Dict
import yfinance as yf
from datetime import datetime

REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def download_with_retry(symbol: str, start: str, end: str, max_retries: int = 3, delay: int = 2) -> pd.DataFrame:
    """
    Download data with retry logic and better error handling.
    
    Parameters
    ----------
    symbol : str
        Stock symbol to download
    start : str
        Start date in YYYY-MM-DD format
    end : str
        End date in YYYY-MM-DD format
    max_retries : int, default 3
        Maximum number of retry attempts
    delay : int, default 2
        Delay between retries in seconds
        
    Returns
    -------
    pd.DataFrame
        Downloaded data with lowercase column names
        
    Raises
    ------
    RuntimeError
        If download fails after all retries
    """
    for attempt in range(max_retries):
        try:
            # Use Ticker class instead of download function
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=start, end=end, interval="1d")
            
            if df.empty:
                raise ValueError(f"No data downloaded for {symbol}")
                
            # Ensure we have all required columns
            required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
                
            # Rename columns to lowercase
            df = df.rename(columns={c: c.lower() for c in df.columns})
            
            # Ensure index is datetime
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
                
            return df
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise RuntimeError(f"Failed to download data for {symbol} after {max_retries} attempts: {str(e)}")

def build_factor_df(df: pd.DataFrame, score_col: str = 'score', thr: int = 7) -> pd.DataFrame:
    """
    Add entry/exit signals to the DataFrame based on score and SMA-200.
    Entry: score >= thr and close > SMA200
    Exit: close < SMA200 or ATR stop
    """
    df = df.copy()
    df['sma_200'] = vbt.MA.run(df['close'], window=200).ma
    df['atr'] = vbt.ATR.run(df['high'], df['low'], df['close'], window=14).atr
    df['entry'] = (df[score_col] >= thr) & (df['close'] > df['sma_200'])
    df['exit_sma'] = df['close'] < df['sma_200']
    # ATR stop: exit if close < entry - n*ATR (n=2)
    df['entry_price'] = np.where(df['entry'], df['close'], np.nan)
    df['entry_price'] = pd.Series(df['entry_price']).ffill()
    df['atr_stop'] = df['entry_price'] - 2 * df['atr']
    df['exit_atr'] = df['close'] < df['atr_stop']
    df['exit'] = df['exit_sma'] | df['exit_atr']
    return df

def backtest(
    df: pd.DataFrame,
    start: str,
    end: str,
    cash: float = 100_000,
    score_col: str = 'score',
    thr: int = 7,
    symbol: str = 'AAPL',
    plot: bool = True
) -> Dict:
    """
    Run vectorbt backtest for the given DataFrame and parameters.
    Returns dict with total return, max drawdown, sharpe, and figure path.
    """
    df = df.loc[start:end].copy()
    factor_df = build_factor_df(df, score_col=score_col, thr=thr)
    entries = factor_df['entry']
    exits = factor_df['exit']
    price = factor_df['close']
    pf = vbt.Portfolio.from_signals(
        price,
        entries,
        exits,
        init_cash=cash,
        fees=0.001,
        slippage=0.001,
        direction='longonly',
        freq='1D',
        accumulate=True
    )
    stats = pf.stats()
    print('Stats keys:', list(stats.keys()))
    print('Stats:', stats)
    total_return = stats['Total Return [%]']
    max_dd = stats['Max Drawdown [%]']
    sharpe = stats['Sharpe Ratio']
    fig_path = os.path.join(REPORTS_DIR, f"{symbol}_{start}_{end}_bt.png")
    if plot:
        pf.plot().write_image(fig_path)
    return dict(total_return=total_return, max_dd=max_dd, sharpe=sharpe, fig_path=fig_path)

# Smoke test: AAPL 2015-2020
def _smoke_test():
    try:
        df = download_with_retry('AAPL', '2015-01-01', '2020-12-31')
        # Fake score: always 8
        df['score'] = 8
        result = backtest(df, start='2015-01-01', end='2020-12-31', symbol='AAPL')
        print("Smoke test result:", result)
    except Exception as e:
        print(f"Smoke test failed: {str(e)}")
        raise

if __name__ == "__main__":
    _smoke_test() 