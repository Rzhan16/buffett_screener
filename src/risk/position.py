"""
Risk management and position sizing module.
"""
import pandas as pd
import numpy as np
import logging
from typing import Dict, Union, List, Tuple, Optional

logger = logging.getLogger(__name__)

class RiskManager:
    """
    Risk management class for position sizing and portfolio risk.
    
    This class provides methods for:
    - Position sizing based on ATR (Average True Range)
    - Stop-loss and take-profit calculation
    - Portfolio-level risk management
    - Dynamic position adjustment
    """
    
    def __init__(self, account_size: float, max_risk_pct: float = 0.01, max_position_pct: float = 0.05):
        """
        Initialize risk manager.
        
        Parameters
        ----------
        account_size : float
            Total account size in dollars
        max_risk_pct : float, default 0.01
            Maximum risk per trade as percentage of account (e.g., 0.01 = 1%)
        max_position_pct : float, default 0.05
            Maximum position size as percentage of account (e.g., 0.05 = 5%)
        """
        self.account_size = account_size
        self.max_risk_pct = max_risk_pct
        self.max_position_pct = max_position_pct
        self.positions = {}  # Current positions
        
    def calculate_position_size(self, ticker: str, price: float, atr: float, 
                               risk_multiple: float = 2.0) -> Dict[str, float]:
        """
        Calculate position size based on ATR and risk parameters.
        
        Parameters
        ----------
        ticker : str
            Stock ticker symbol
        price : float
            Current price of the stock
        atr : float
            Average True Range value
        risk_multiple : float, default 2.0
            Multiple of ATR to use for stop loss
            
        Returns
        -------
        Dict[str, float]
            Dictionary with position details including:
            - shares: Number of shares to buy
            - dollar_amount: Total position value
            - stop_loss: Stop loss price
            - risk_amount: Dollar amount at risk
            - risk_pct: Percentage of account at risk
        """
        # Calculate stop loss based on ATR
        stop_loss = price - (atr * risk_multiple)
        
        # Calculate dollar risk per share
        risk_per_share = price - stop_loss
        
        # Calculate max dollar risk for this trade
        max_dollar_risk = self.account_size * self.max_risk_pct
        
        # Calculate number of shares based on risk
        shares = int(max_dollar_risk / risk_per_share) if risk_per_share > 0 else 0
        
        # Calculate total position value
        position_value = shares * price
        
        # Cap position size based on max_position_pct
        max_position_value = self.account_size * self.max_position_pct
        if position_value > max_position_value:
            shares = int(max_position_value / price)
            position_value = shares * price
        
        # Calculate actual risk amount and percentage
        risk_amount = shares * risk_per_share
        risk_pct = risk_amount / self.account_size
        
        return {
            'ticker': ticker,
            'shares': shares,
            'entry_price': price,
            'dollar_amount': position_value,
            'stop_loss': stop_loss,
            'risk_amount': risk_amount,
            'risk_pct': risk_pct
        }
    
    def calculate_take_profit(self, entry_price: float, stop_loss: float, 
                             risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take profit level based on risk-reward ratio.
        
        Parameters
        ----------
        entry_price : float
            Entry price of the position
        stop_loss : float
            Stop loss price
        risk_reward_ratio : float, default 2.0
            Desired risk-reward ratio (e.g., 2.0 = 2:1)
            
        Returns
        -------
        float
            Take profit price
        """
        risk = entry_price - stop_loss
        take_profit = entry_price + (risk * risk_reward_ratio)
        return take_profit
    
    def add_position(self, ticker: str, position_data: Dict[str, float]) -> None:
        """
        Add a position to the portfolio.
        
        Parameters
        ----------
        ticker : str
            Stock ticker symbol
        position_data : Dict[str, float]
            Position details from calculate_position_size
        """
        self.positions[ticker] = position_data
        logger.info(f"Added position: {ticker}, shares: {position_data['shares']}, "
                   f"value: ${position_data['dollar_amount']:.2f}, "
                   f"risk: ${position_data['risk_amount']:.2f} ({position_data['risk_pct']*100:.2f}%)")
    
    def remove_position(self, ticker: str) -> None:
        """
        Remove a position from the portfolio.
        
        Parameters
        ----------
        ticker : str
            Stock ticker symbol
        """
        if ticker in self.positions:
            del self.positions[ticker]
            logger.info(f"Removed position: {ticker}")
    
    def get_portfolio_risk(self) -> Dict[str, float]:
        """
        Calculate total portfolio risk.
        
        Returns
        -------
        Dict[str, float]
            Dictionary with portfolio risk metrics:
            - total_value: Total portfolio value
            - total_risk_amount: Total dollar amount at risk
            - total_risk_pct: Total percentage of account at risk
            - position_count: Number of positions
        """
        total_value = sum(pos['dollar_amount'] for pos in self.positions.values())
        total_risk = sum(pos['risk_amount'] for pos in self.positions.values())
        
        return {
            'total_value': total_value,
            'total_risk_amount': total_risk,
            'total_risk_pct': total_risk / self.account_size if self.account_size > 0 else 0,
            'position_count': len(self.positions)
        }
    
    def adjust_position_sizes(self, max_portfolio_risk_pct: float = 0.05) -> Dict[str, Dict[str, float]]:
        """
        Adjust position sizes to keep total portfolio risk under threshold.
        
        Parameters
        ----------
        max_portfolio_risk_pct : float, default 0.05
            Maximum total portfolio risk as percentage of account
            
        Returns
        -------
        Dict[str, Dict[str, float]]
            Dictionary of adjusted positions
        """
        portfolio_risk = self.get_portfolio_risk()
        
        # If portfolio risk is acceptable, return current positions
        if portfolio_risk['total_risk_pct'] <= max_portfolio_risk_pct:
            return self.positions
        
        # Calculate scaling factor to reduce all positions proportionally
        scaling_factor = max_portfolio_risk_pct / portfolio_risk['total_risk_pct']
        
        # Adjust each position
        adjusted_positions = {}
        for ticker, position in self.positions.items():
            adjusted_shares = int(position['shares'] * scaling_factor)
            
            if adjusted_shares > 0:
                adjusted_position = position.copy()
                adjusted_position['shares'] = adjusted_shares
                adjusted_position['dollar_amount'] = adjusted_shares * position['entry_price']
                adjusted_position['risk_amount'] = adjusted_shares * (position['entry_price'] - position['stop_loss'])
                adjusted_position['risk_pct'] = adjusted_position['risk_amount'] / self.account_size
                
                adjusted_positions[ticker] = adjusted_position
                
                logger.info(f"Adjusted position: {ticker}, shares: {adjusted_shares} "
                           f"(scaled by {scaling_factor:.2f})")
        
        self.positions = adjusted_positions
        return self.positions
    
    def calculate_trailing_stop(self, ticker: str, current_price: float, atr_multiple: float = 2.0) -> float:
        """
        Calculate trailing stop loss based on current price and ATR multiple.
        
        Parameters
        ----------
        ticker : str
            Stock ticker symbol
        current_price : float
            Current price of the stock
        atr_multiple : float, default 2.0
            Multiple of ATR to use for trailing stop
            
        Returns
        -------
        float
            New stop loss price
        """
        if ticker not in self.positions:
            logger.warning(f"Position {ticker} not found for trailing stop calculation")
            return 0.0
            
        position = self.positions[ticker]
        entry_price = position['entry_price']
        current_stop = position['stop_loss']
        
        # If position is profitable, calculate new stop loss
        if current_price > entry_price:
            # Calculate how many ATRs we've moved
            price_movement = current_price - entry_price
            original_stop_distance = entry_price - position['stop_loss']
            
            # Move stop loss proportionally to price movement
            # but keep at least original ATR multiple distance from current price
            new_stop = current_price - max(original_stop_distance, atr_multiple * original_stop_distance / 2)
            
            # Only move stop loss up, never down
            if new_stop > current_stop:
                self.positions[ticker]['stop_loss'] = new_stop
                logger.info(f"Updated trailing stop for {ticker}: ${new_stop:.2f}")
                return new_stop
        
        # Return current stop loss if we didn't update it
        return current_stop

def position_size(price: float, atr: float, account_size: float, risk_pct: float = 0.01) -> float:
    """
    Calculate position size based on ATR.
    
    Parameters
    ----------
    price : float
        Current price
    atr : float
        Average True Range value
    account_size : float
        Account size in dollars
    risk_pct : float
        Risk percentage per trade (e.g., 0.01 for 1%)
        
    Returns
    -------
    float
        Position size in dollars
    """
    # Calculate risk amount
    risk_amount = account_size * risk_pct
    
    # Use 2x ATR as stop loss distance
    risk_per_share = 2 * atr
    
    # Calculate position size
    if risk_per_share == 0:
        return 0
    
    # Return position size in dollars
    return (risk_amount / risk_per_share) * price 