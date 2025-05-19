"""
Tests for risk management modules.
"""
import pytest
from src.risk.position import position_size, MAX_RISK_PCT, KELLY_CAP


def test_position_size_calculation():
    """Test basic position size calculation."""
    # Test with explicit stop loss
    # Entry = 100, Stop = 95, Risk = 1% of 10000 = 100
    # Risk per share = 5, so shares = 100/5 = 20
    # But with kelly_cap = 0.05, max shares = 10000*0.05/100 = 5
    result = position_size(entry=100, stop=95, equity=10000, risk_pct=0.01)
    assert result == 5
    
    # Test with ATR-based stop loss
    # Entry = 100, ATR = 2.5, Stop = 100 - 2*2.5 = 95
    # Risk per share = 5, so shares = 100/5 = 20
    # But with kelly_cap = 0.05, max shares = 10000*0.05/100 = 5
    result = position_size(entry=100, equity=10000, atr=2.5, risk_pct=0.01)
    assert result == 5
    
    # Test with higher kelly cap to allow full position size
    result = position_size(entry=100, stop=95, equity=10000, risk_pct=0.01, kelly_cap=0.2)
    assert result == 20


def test_position_size_with_kelly_cap():
    """Test position size with Kelly cap applied."""
    # Entry = 10, Stop = 9, Risk = 1% of 10000 = 100
    # Risk per share = 1, so shares = 100/1 = 100
    # Kelly cap = 5% of 10000 = 500, max shares = 500/10 = 50
    # Should return 50 (capped)
    result = position_size(entry=10, stop=9, equity=10000, risk_pct=0.01, kelly_cap=0.05)
    assert result == 50
    
    # With higher kelly cap, should return uncapped value
    result = position_size(entry=10, stop=9, equity=10000, risk_pct=0.01, kelly_cap=0.2)
    assert result == 100


def test_position_size_rounding():
    """Test that position size is properly rounded down."""
    # Entry = 100, Stop = 97, Risk = 1% of 10000 = 100
    # Risk per share = 3, so shares = 100/3 = 33.33...
    # But with kelly_cap = 0.05, max shares = 10000*0.05/100 = 5
    result = position_size(entry=100, stop=97, equity=10000, risk_pct=0.01)
    assert result == 5
    
    # With higher kelly cap to allow full position size
    result = position_size(entry=100, stop=97, equity=10000, risk_pct=0.01, kelly_cap=0.5)
    assert result == 33


def test_position_size_with_defaults():
    """Test position size calculation with default parameters."""
    # Using memory bank defaults: MAX_RISK_PCT=0.01, KELLY_CAP=0.05
    result = position_size(entry=100, stop=95, equity=10000)
    assert result == 5
    
    # Should match explicit parameters
    explicit = position_size(entry=100, stop=95, equity=10000, 
                            risk_pct=MAX_RISK_PCT, kelly_cap=KELLY_CAP)
    assert result == explicit


def test_invalid_inputs():
    """Test error handling for invalid inputs."""
    # Test negative entry price
    with pytest.raises(ValueError):
        position_size(entry=-100, stop=95, equity=10000)
    
    # Test zero entry price
    with pytest.raises(ValueError):
        position_size(entry=0, stop=95, equity=10000)
    
    # Test negative equity
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=-10000)
    
    # Test zero equity
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=0)
    
    # Test negative risk percentage
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=10000, risk_pct=-0.01)
    
    # Test zero risk percentage
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=10000, risk_pct=0)
    
    # Test negative kelly cap
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=10000, kelly_cap=-0.05)
    
    # Test zero kelly cap
    with pytest.raises(ValueError):
        position_size(entry=100, stop=95, equity=10000, kelly_cap=0)
    
    # Test stop greater than entry
    with pytest.raises(ValueError):
        position_size(entry=100, stop=105, equity=10000)
    
    # Test stop equal to entry
    with pytest.raises(ValueError):
        position_size(entry=100, stop=100, equity=10000)
    
    # Test missing stop and ATR
    with pytest.raises(ValueError):
        position_size(entry=100, equity=10000) 