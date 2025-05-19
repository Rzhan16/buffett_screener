"""
Tests for risk management and position sizing module.
"""
import pytest
from src.risk.position import RiskManager, position_size

def test_position_size_legacy():
    """Test legacy position_size function."""
    # Basic position size calculation
    shares = position_size(price=100, atr=2, account_size=10000, risk_pct=0.01)
    assert shares > 0
    
    # With different risk percentage
    shares_higher_risk = position_size(price=100, atr=2, account_size=10000, risk_pct=0.02)
    assert shares_higher_risk >= shares  # May be equal due to position cap
    
    # With different risk multiple
    shares_higher_multiple = position_size(price=100, atr=2, account_size=10000, risk_multiple=3)
    assert shares_higher_multiple <= shares  # May be equal due to position cap


class TestRiskManager:
    """Tests for the RiskManager class."""
    
    @pytest.fixture
    def risk_manager(self):
        """Create a risk manager instance."""
        return RiskManager(account_size=100000, max_risk_pct=0.01, max_position_pct=0.05)
    
    def test_calculate_position_size(self, risk_manager):
        """Test position size calculation."""
        position = risk_manager.calculate_position_size(
            ticker="AAPL",
            price=150,
            atr=3,
            risk_multiple=2
        )
        
        # Check position structure
        assert position['ticker'] == "AAPL"
        assert position['shares'] > 0
        assert position['entry_price'] == 150
        assert position['stop_loss'] == 144  # 150 - (3 * 2)
        assert position['risk_amount'] > 0
        assert position['risk_pct'] <= 0.01  # Should not exceed max risk
        
        # Check position value cap
        assert position['dollar_amount'] <= 5000  # 5% of 100000
    
    def test_calculate_take_profit(self, risk_manager):
        """Test take profit calculation."""
        entry_price = 100
        stop_loss = 90
        
        # Default 2:1 risk-reward
        take_profit = risk_manager.calculate_take_profit(entry_price, stop_loss)
        assert take_profit == 120  # 100 + (10 * 2)
        
        # Custom risk-reward
        take_profit = risk_manager.calculate_take_profit(entry_price, stop_loss, risk_reward_ratio=3)
        assert take_profit == 130  # 100 + (10 * 3)
    
    def test_portfolio_management(self, risk_manager):
        """Test portfolio management functions."""
        # Add positions
        position1 = risk_manager.calculate_position_size("AAPL", 150, 3)
        position2 = risk_manager.calculate_position_size("MSFT", 250, 5)
        
        risk_manager.add_position("AAPL", position1)
        risk_manager.add_position("MSFT", position2)
        
        # Check portfolio risk
        portfolio_risk = risk_manager.get_portfolio_risk()
        assert portfolio_risk['position_count'] == 2
        assert portfolio_risk['total_value'] > 0
        assert portfolio_risk['total_risk_amount'] > 0
        assert portfolio_risk['total_risk_pct'] <= 0.02  # Should be around 2% (0.01 * 2)
        
        # Test position removal
        risk_manager.remove_position("AAPL")
        portfolio_risk = risk_manager.get_portfolio_risk()
        assert portfolio_risk['position_count'] == 1
        assert "MSFT" in risk_manager.positions
        assert "AAPL" not in risk_manager.positions
    
    def test_adjust_position_sizes(self, risk_manager):
        """Test position size adjustment."""
        # Add multiple positions to exceed max portfolio risk
        for ticker, price, atr in [
            ("AAPL", 150, 3),
            ("MSFT", 250, 5),
            ("GOOG", 2500, 50),
            ("AMZN", 120, 2.5),
            ("META", 300, 6),
            ("TSLA", 200, 8)
        ]:
            position = risk_manager.calculate_position_size(ticker, price, atr)
            risk_manager.add_position(ticker, position)
        
        # Get initial portfolio risk
        initial_risk = risk_manager.get_portfolio_risk()
        
        # Force higher initial risk for testing
        risk_manager.max_risk_pct = 0.02  # Double the risk per position
        for ticker in list(risk_manager.positions.keys()):
            position = risk_manager.calculate_position_size(ticker, 
                                                          risk_manager.positions[ticker]['entry_price'], 
                                                          risk_manager.positions[ticker]['entry_price'] - risk_manager.positions[ticker]['stop_loss'])
            risk_manager.positions[ticker] = position
            
        # Verify risk is higher now
        higher_risk = risk_manager.get_portfolio_risk()
        assert higher_risk['total_risk_pct'] > initial_risk['total_risk_pct']
        
        # Now adjust positions to 3% max portfolio risk
        adjusted = risk_manager.adjust_position_sizes(max_portfolio_risk_pct=0.03)
        
        # Check that risk was reduced
        new_risk = risk_manager.get_portfolio_risk()
        assert new_risk['total_risk_pct'] <= 0.03
        
        # All tickers should still be present
        assert len(adjusted) == 6
        assert all(ticker in adjusted for ticker in ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA"])
    
    def test_trailing_stop_up_movement(self, risk_manager):
        """Test trailing stop moves up when price increases."""
        # Add a position
        position = risk_manager.calculate_position_size("AAPL", 100, 2)
        initial_stop = position['stop_loss']  # Should be 96 (100 - 2*2)
        risk_manager.add_position("AAPL", position)
        
        # Price moves up, stop should move up
        new_stop = risk_manager.calculate_trailing_stop("AAPL", 110, 2.0)
        assert new_stop > initial_stop
        
    def test_trailing_stop_down_movement(self):
        """Test trailing stop doesn't move down when price decreases."""
        # Create a risk manager
        risk_manager = RiskManager(account_size=100000, max_risk_pct=0.01, max_position_pct=0.05)
        
        # Add a position with a manually set stop loss
        position = risk_manager.calculate_position_size("AAPL", 100, 2)
        position['stop_loss'] = 90  # Manually set stop loss
        risk_manager.add_position("AAPL", position)
        
        # Price moves down, stop should not change
        new_stop = risk_manager.calculate_trailing_stop("AAPL", 95, 2.0)
        assert new_stop == 90  # Stop should remain the same
