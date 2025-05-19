"""
Backtesting module for strategy validation.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Tuple
import logging

from src.scoring.buffett import get_f_score
from src.technical.core import get_sma
from src.llm.embeddings import fetch_fundamentals

logger = logging.getLogger(__name__)

class StrategyValidator:
    def __init__(self, config: Dict):
        self.config = config
        self.results = []
        
    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical price data for a symbol."""
        try:
            data = yf.download(symbol, start=start_date, end=end_date)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return pd.DataFrame()
            
    def calculate_returns(self, data: pd.DataFrame) -> Tuple[float, float, float]:
        """Calculate key return metrics."""
        if data.empty:
            return 0.0, 0.0, 0.0
            
        returns = data['Close'].pct_change()
        total_return = (data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100
        annualized_return = (1 + total_return/100) ** (252/len(data)) - 1
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
        
        return total_return, annualized_return, sharpe_ratio
        
    def calculate_drawdown(self, data: pd.DataFrame) -> float:
        """Calculate maximum drawdown."""
        if data.empty:
            return 0.0
            
        peak = data['Close'].expanding().max()
        drawdown = (data['Close'] - peak) / peak
        return drawdown.min() * 100
        
    def validate_strategy(self, symbols: List[str], start_date: str, end_date: str) -> pd.DataFrame:
        """Validate strategy performance across multiple symbols."""
        results = []
        
        for symbol in symbols:
            # Fetch historical data
            data = self.fetch_historical_data(symbol, start_date, end_date)
            if data.empty:
                continue
                
            # Calculate metrics
            total_return, annualized_return, sharpe = self.calculate_returns(data)
            max_drawdown = self.calculate_drawdown(data)
            
            # Get fundamental metrics
            fundamentals = fetch_fundamentals(symbol)
            
            # Get F-score and SMA
            f_score = get_f_score().loc[symbol, 'score'] if symbol in get_f_score().index else 0
            sma_data = get_sma([symbol])
            sma_200 = sma_data.loc[symbol, 'sma_200'] if not sma_data.empty else 0
            
            results.append({
                'symbol': symbol,
                'total_return': total_return,
                'annualized_return': annualized_return,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_drawdown,
                'f_score': f_score,
                'sma_200': sma_200,
                'pe_ratio': fundamentals['pe_ratio'],
                'pb_ratio': fundamentals['pb_ratio'],
                'dividend_yield': fundamentals['dividend_yield'],
                'debt_to_equity': fundamentals['debt_to_equity']
            })
            
        return pd.DataFrame(results)
        
    def analyze_market_conditions(self, data: pd.DataFrame) -> Dict:
        """Analyze market conditions during the test period."""
        if data.empty:
            return {}
            
        # Calculate volatility
        returns = data['Close'].pct_change()
        volatility = returns.std() * np.sqrt(252) * 100
        
        # Calculate trend
        sma_200 = data['Close'].rolling(window=200).mean()
        trend = 'bullish' if data['Close'].iloc[-1] > sma_200.iloc[-1] else 'bearish'
        
        # Calculate market regime
        regime = 'high_volatility' if volatility > 20 else 'low_volatility'
        
        return {
            'volatility': volatility,
            'trend': trend,
            'regime': regime
        }
        
    def run_validation(self, symbols: List[str], start_date: str, end_date: str) -> Dict:
        """Run full strategy validation."""
        # Validate strategy
        results_df = self.validate_strategy(symbols, start_date, end_date)
        
        # Analyze market conditions
        market_data = yf.download('^GSPC', start=start_date, end=end_date)  # S&P 500 as market proxy
        market_conditions = self.analyze_market_conditions(market_data)
        
        # Calculate aggregate metrics
        aggregate_metrics = {
            'avg_return': results_df['total_return'].mean(),
            'avg_sharpe': results_df['sharpe_ratio'].mean(),
            'avg_drawdown': results_df['max_drawdown'].mean(),
            'win_rate': (results_df['total_return'] > 0).mean() * 100,
            'market_conditions': market_conditions
        }
        
        return {
            'results': results_df,
            'aggregate_metrics': aggregate_metrics
        }

def main():
    """Example usage of the validator."""
    # Example config
    config = {
        'strategy': 'long_term',
        'filters': {
            'f_score': 7,
            'sma_200': True
        }
    }
    
    # Initialize validator
    validator = StrategyValidator(config)
    
    # Example symbols
    symbols = ['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META']
    
    # Run validation
    start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    results = validator.run_validation(symbols, start_date, end_date)
    
    # Print results
    print("\nStrategy Validation Results:")
    print("=" * 50)
    print("\nIndividual Stock Performance:")
    print(results['results'].to_string())
    print("\nAggregate Metrics:")
    for metric, value in results['aggregate_metrics'].items():
        if metric != 'market_conditions':
            print(f"{metric}: {value:.2f}")
    print("\nMarket Conditions:")
    for condition, value in results['aggregate_metrics']['market_conditions'].items():
        print(f"{condition}: {value}")

if __name__ == "__main__":
    main() 