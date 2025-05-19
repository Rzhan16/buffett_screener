"""
Enhanced filters for the Buffett + Momentum screener.
Implements quality, sustainability, and momentum filters for long-term value investing.
"""
import logging
from typing import Dict, List, Optional, Union
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedScreener:
    def __init__(self, config_path: str):
        """
        Initialize the enhanced screener with configuration.
        
        Parameters
        ----------
        config_path : str
            Path to the YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.fmp_client = None  # Will be initialized with API key
        self.yahoo_client = None  # Will be initialized with API key
        
    def _load_config(self, config_path: str) -> Dict:
        """Load and validate the screener configuration."""
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    
    def _calculate_accruals_ratio(self, net_income: float, operating_cash_flow: float, total_assets: float) -> float:
        """Calculate the accruals ratio."""
        return (net_income - operating_cash_flow) / total_assets if total_assets != 0 else float('inf')
    
    def _calculate_industry_cagr(self, industry_revenues: pd.Series) -> float:
        """Calculate 3-year CAGR for industry revenue."""
        if len(industry_revenues) < 2:
            return float('-inf')
        periods = len(industry_revenues) - 1
        return (industry_revenues.iloc[-1] / industry_revenues.iloc[0]) ** (1/periods) - 1
    
    def _calculate_relative_strength(self, stock_returns: pd.Series, sector_returns: pd.Series) -> float:
        """Calculate relative strength compared to sector."""
        return (1 + stock_returns).prod() / (1 + sector_returns).prod() - 1
    
    def _check_earnings_quality(self, financials: Dict) -> bool:
        """Check earnings quality metrics."""
        config = self.config['earnings']
        
        # Check EPS growth
        eps_growth = financials.get('eps_growth', [])
        if len(eps_growth) < config['consistency']['min_positive_years']:
            return False
        if not all(g > 0 for g in eps_growth[-config['consistency']['min_positive_years']:]):
            return False
        
        # Check earnings surprises
        surprises = financials.get('earnings_surprises', [])
        if len(surprises) < 4:
            return False
        negative_surprises = sum(1 for s in surprises[-4:] if s < 0)
        if negative_surprises > config['consistency']['max_negative_surprises']:
            return False
        
        # Check revenue growth
        if financials.get('revenue_growth', 0) <= config['revenue']['min_growth']:
            return False
        
        # Check gross margin stability
        gross_margins = financials.get('gross_margins', [])
        if len(gross_margins) < 2:
            return False
        if np.std(gross_margins) > config['revenue']['max_gross_margin_std']:
            return False
        
        return True
    
    def _check_financial_health(self, financials: Dict) -> bool:
        """Check financial health metrics."""
        config = self.config['financial']
        
        # Check debt metrics
        if financials.get('interest_coverage', 0) < config['debt']['min_interest_coverage']:
            return False
        if financials.get('debt_to_equity', float('inf')) > config['debt']['max_debt_to_equity']:
            return False
        if financials.get('free_cash_flow_yield', 0) < config['debt']['min_free_cash_flow_yield']:
            return False
        
        # Check dividend metrics if company pays dividends
        if financials.get('dividend_yield', 0) > 0:
            if financials.get('payout_ratio', 1) > config['dividend']['max_payout_ratio']:
                return False
            if financials.get('dividend_growth_5y', 0) <= config['dividend']['min_growth_rate']:
                return False
        
        return True
    
    def _check_technical_indicators(self, technicals: Dict) -> bool:
        """Check technical indicators."""
        config = self.config['technical']
        
        # Check trend strength
        if technicals.get('adx', 0) < config['trend']['min_adx']:
            return False
        if technicals.get('rsi', 0) > config['trend']['max_rsi']:
            return False
        
        # Check support/resistance
        if not technicals.get('price_above_ma20', False):
            return False
        if technicals.get('price_std_dev', 0) > config['support_resistance']['max_std_dev']:
            return False
        
        return True
    
    def _check_risk_metrics(self, risk_metrics: Dict) -> bool:
        """Check risk management metrics."""
        config = self.config['risk']
        
        # Check volatility
        if risk_metrics.get('beta', float('inf')) > config['volatility']['max_beta']:
            return False
        if risk_metrics.get('volatility_vs_sector', float('inf')) > config['volatility']['max_volatility_vs_sector']:
            return False
        
        # Check liquidity
        if risk_metrics.get('market_cap', 0) < config['liquidity']['min_market_cap']:
            return False
        if risk_metrics.get('avg_volume', 0) < config['liquidity']['min_avg_volume']:
            return False
        
        return True
    
    def screen_stock(self, symbol: str) -> Optional[Dict]:
        """
        Screen a single stock against all filters.
        
        Parameters
        ----------
        symbol : str
            Stock symbol to screen
        
        Returns
        -------
        Optional[Dict]
            Dictionary containing stock data if it passes all filters,
            None otherwise
        """
        try:
            # Get financial data
            financials = self.fmp_client.get_financials(symbol)
            technicals = self.yahoo_client.get_technicals(symbol)
            risk_metrics = self.fmp_client.get_risk_metrics(symbol)
            
            # Check all filter categories
            if not self._check_earnings_quality(financials):
                return None
            if not self._check_financial_health(financials):
                return None
            if not self._check_technical_indicators(technicals):
                return None
            if not self._check_risk_metrics(risk_metrics):
                return None
            
            # If all checks pass, return the stock data
            return {
                'symbol': symbol,
                'financials': financials,
                'technicals': technicals,
                'risk_metrics': risk_metrics
            }
            
        except Exception as e:
            logger.error(f"Error screening {symbol}: {str(e)}")
            return None
    
    def screen_universe(self, symbols: List[str]) -> List[Dict]:
        """
        Screen a universe of stocks against all filters.
        
        Parameters
        ----------
        symbols : List[str]
            List of stock symbols to screen
        
        Returns
        -------
        List[Dict]
            List of dictionaries containing data for stocks that pass all filters
        """
        results = []
        for symbol in symbols:
            result = self.screen_stock(symbol)
            if result:
                results.append(result)
        
        # Sort results according to configuration
        sort_field = self.config['output']['sort_by']
        sort_order = self.config['output']['sort_order']
        results.sort(key=lambda x: x['financials'].get(sort_field, 0),
                    reverse=(sort_order == 'desc'))
        
        # Limit results
        max_results = self.config['output']['max_results']
        return results[:max_results]
    
    def format_output(self, results: List[Dict]) -> Union[str, Dict]:
        """
        Format the screening results according to configuration.
        
        Parameters
        ----------
        results : List[Dict]
            List of screening results
        
        Returns
        -------
        Union[str, Dict]
            Formatted results in the specified output format
        """
        output_format = self.config['output']['format']
        fields = self.config['output']['fields']
        
        formatted_results = []
        for result in results:
            formatted_result = {}
            for field in fields:
                if field == 'symbol' and 'symbol' in result:
                    formatted_result['symbol'] = result['symbol']
                elif field in result.get('financials', {}):
                    formatted_result[field] = result['financials'][field]
                elif field in result.get('technicals', {}):
                    formatted_result[field] = result['technicals'][field]
                elif field in result.get('risk_metrics', {}):
                    formatted_result[field] = result['risk_metrics'][field]
            formatted_results.append(formatted_result)
        
        if output_format == 'json':
            return formatted_results
        elif output_format == 'csv':
            df = pd.DataFrame(formatted_results)
            return df.to_csv(index=False)
        else:
            raise ValueError(f"Unsupported output format: {output_format}") 