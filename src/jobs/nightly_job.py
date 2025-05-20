"""
Nightly job to screen stocks, generate explanations, and submit orders.
"""
import os
import sys
import json
import logging
import argparse
from typing import Dict, List, Optional
from datetime import datetime
import yaml
import requests
import pandas as pd
from pathlib import Path
import yfinance as yf

# Add src to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.scoring.buffett import get_f_score
from src.technical.core import get_sma
from src.risk.position import position_size
from src.execution.broker_alpaca import submit_bracket
from src.llm.embeddings import explain_with_fingpt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_config(config_path: str = 'configs/long_term.yml') -> Dict:
    """Load and validate YAML configuration."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise

def get_top_stocks(config: Dict, dry_run: bool = False) -> pd.DataFrame:
    """Get top stocks based on F-score and other filters."""
    # Get F-scores
    universe = config.get("universe", "SP500")
    f_scores = get_f_score(universe=universe)
    
    # Apply F-score filter
    filtered = f_scores[f_scores['score'] >= config['filters']['f_score']]
    
    # Apply SMA filters
    if 'sma_200' in config['filters'] and config['filters']['sma_200']:
        sma_data = get_sma(filtered.index.tolist(), window=200)
        filtered = filtered[filtered.index.isin(sma_data[sma_data['close'] > sma_data['sma_200']].index)]
    
    if 'sma_50' in config['filters'] and config['filters']['sma_50']:
        sma_data = get_sma(filtered.index.tolist(), window=50)
        filtered = filtered[filtered.index.isin(sma_data[sma_data['close'] > sma_data['sma_50']].index)]
    
    # Apply price filter if configured
    if 'max_price' in config['filters']:
        filtered = filtered[filtered['close'] <= config['filters']['max_price']]
    
    # Apply market cap filters if configured
    if 'min_market_cap' in config['filters'] or 'max_market_cap' in config['filters']:
        for symbol in list(filtered.index):
            try:
                ticker_info = yf.Ticker(symbol).info
                market_cap = ticker_info.get('marketCap', 0)
                
                if 'min_market_cap' in config['filters'] and market_cap < config['filters']['min_market_cap']:
                    filtered = filtered.drop(symbol)
                if 'max_market_cap' in config['filters'] and market_cap > config['filters']['max_market_cap']:
                    filtered = filtered.drop(symbol)
            except Exception as e:
                logger.warning(f"Failed to get market cap for {symbol}: {e}")
                filtered = filtered.drop(symbol)
    
    # Sort by score and take top 10
    top_stocks = filtered.sort_values('score', ascending=False).head(10)
    
    logger.info(f"Found {len(top_stocks)} stocks matching criteria")
    return top_stocks

def generate_memo(stocks: pd.DataFrame, explanations: Dict[str, str]) -> str:
    """Generate memo with stock picks and explanations."""
    memo = f"Buffett Screener Results - {datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    for symbol in stocks.index:
        score = stocks.loc[symbol, 'score']
        memo += f"{symbol} (F-score: {score})\n"
        memo += f"Explanation: {explanations.get(symbol, 'No explanation available')}\n\n"
    
    return memo

def post_to_slack(summary: Dict, webhook_url: Optional[str] = None) -> None:
    """Post summary to Slack if webhook URL is provided."""
    if not webhook_url:
        logger.info("No Slack webhook URL provided, skipping notification")
        return
    
    try:
        response = requests.post(
            webhook_url,
            json=summary,
            headers={'Content-Type': 'application/json'}
        )
        response.raise_for_status()
        logger.info("Posted summary to Slack")
    except Exception as e:
        logger.error(f"Failed to post to Slack: {e}")

def main():
    parser = argparse.ArgumentParser(description='Run nightly stock screening job')
    parser.add_argument('--config', default='configs/long_term.yml',
                      help='Path to config file')
    parser.add_argument('--dry-run', action='store_true',
                      help='Run without submitting orders')
    parser.add_argument('--live', action='store_true',
                      help='Run in live trading mode')
    parser.add_argument('--verbose', action='store_true',
                      help='Enable verbose logging')
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # 1. Load config
        config = load_config(args.config)
        
        # 2. Get top stocks
        top_stocks = get_top_stocks(config, args.dry_run)
        
        # 3. Calculate position sizes
        positions = {}
        for symbol in top_stocks.index:
            price = top_stocks.loc[symbol, 'close']
            atr = top_stocks.loc[symbol, 'atr']
            size = position_size(price=price, atr=atr, account_size=100000)
            positions[symbol] = size
        
        # 4. Generate explanations
        explanations = {}
        for symbol in top_stocks.index:
            explanation = explain_with_fingpt(symbol)
            explanations[symbol] = explanation
        
        # 5. Write memo
        memo = generate_memo(top_stocks, explanations)
        memo_path = 'reports/buffett_memo.txt'
        os.makedirs('reports', exist_ok=True)
        with open(memo_path, 'w') as f:
            f.write(memo)
        logger.info(f"Wrote memo to {memo_path}")
        
        # 6. Submit orders if not dry run
        if not args.dry_run and args.live:
            for symbol, size in positions.items():
                price = top_stocks.loc[symbol, 'close']
                atr = top_stocks.loc[symbol, 'atr']
                # Calculate stop loss and take profit based on ATR
                stop_loss = price - (2 * atr)  # 2 ATR for stop loss
                take_profit = price + (4 * atr)  # 4 ATR for take profit (2:1 risk-reward)
                submit_bracket(symbol, size, price, take_profit, stop_loss)
                logger.info(f"Submitted order for {symbol}")
        
        # 7. Post summary to Slack
        summary = {
            'timestamp': datetime.now().isoformat(),
            'strategy': config['strategy'],
            'stocks': top_stocks.to_dict(),
            'positions': positions,
            'dry_run': args.dry_run,
            'live': args.live
        }
        post_to_slack(summary, os.getenv('SLACK_URL'))
        
        logger.info("Nightly job completed successfully")
        
    except Exception as e:
        logger.error(f"Nightly job failed: {e}")
        raise

if __name__ == '__main__':
    main() 