"""
Tests for nightly job functionality.
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from datetime import datetime

from src.jobs.nightly_job import (
    load_config,
    get_top_stocks,
    generate_memo,
    post_to_slack,
    main
)

# Test data
MOCK_F_SCORES = pd.DataFrame({
    'score': [8, 7, 6, 9, 8, 7, 6, 5, 4, 3, 2, 1],
    'close': [100] * 12,
    'atr': [2] * 12
}, index=['AAPL', 'MSFT', 'GOOG', 'AMZN', 'META', 'TSLA', 
          'NVDA', 'AMD', 'INTC', 'IBM', 'ORCL', 'SAP'])

MOCK_SMA_DATA = pd.DataFrame({
    'close': [100] * 12,
    'sma_200': [90] * 6 + [110] * 6  # First 6 stocks above SMA, last 6 below
}, index=MOCK_F_SCORES.index)

MOCK_EXPLANATIONS = {
    'AAPL': 'Strong fundamentals and growth potential.',
    'MSFT': 'Solid cloud business and dividend growth.',
    'GOOG': 'Dominant in search and advertising.',
    'AMZN': 'E-commerce leader with AWS growth.',
    'META': 'Social media dominance and metaverse potential.'
}

@pytest.fixture
def mock_config():
    return {
        'strategy': 'long_term',
        'filters': {
            'f_score': 7,
            'sma_200': True
        }
    }

@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv('SLACK_URL', 'https://hooks.slack.com/test')

def test_load_config(tmp_path):
    """Test config loading."""
    # Create test config
    config_path = tmp_path / "test_config.yml"
    config_content = """
    strategy: test_strategy
    filters:
        f_score: 7
        sma_200: true
    """
    config_path.write_text(config_content)
    
    # Test loading
    config = load_config(str(config_path))
    assert config['strategy'] == 'test_strategy'
    assert config['filters']['f_score'] == 7
    assert config['filters']['sma_200'] is True

@patch('src.jobs.nightly_job.get_f_score')
@patch('src.jobs.nightly_job.get_sma')
def test_get_top_stocks(mock_get_sma, mock_get_f_score, mock_config):
    """Test stock filtering and ranking."""
    # Setup mocks
    mock_get_f_score.return_value = MOCK_F_SCORES
    mock_get_sma.return_value = MOCK_SMA_DATA
    
    # Get top stocks
    top_stocks = get_top_stocks(mock_config)
    
    # Verify results
    expected = {'AAPL', 'MSFT', 'AMZN', 'META', 'TSLA'}
    assert set(top_stocks.index) == expected
    assert all(score >= 7 for score in top_stocks['score'])
    assert all(symbol in expected for symbol in top_stocks.index)

def test_generate_memo():
    """Test memo generation."""
    # Create test data
    stocks = pd.DataFrame({
        'score': [8, 7, 9],
        'close': [100, 200, 300],
        'atr': [2, 3, 4]
    }, index=['AAPL', 'MSFT', 'GOOG'])
    
    explanations = {
        'AAPL': 'Test explanation 1',
        'MSFT': 'Test explanation 2',
        'GOOG': 'Test explanation 3'
    }
    
    # Generate memo
    memo = generate_memo(stocks, explanations)
    
    # Verify content
    assert 'Buffett Screener Results' in memo
    assert 'AAPL (F-score: 8)' in memo
    assert 'Test explanation 1' in memo
    assert 'MSFT (F-score: 7)' in memo
    assert 'Test explanation 2' in memo

@patch('requests.post')
def test_post_to_slack(mock_post, mock_env_vars):
    """Test Slack notification."""
    # Setup mock
    mock_post.return_value = MagicMock(status_code=200)
    
    # Test data
    summary = {
        'timestamp': datetime.now().isoformat(),
        'strategy': 'test',
        'stocks': {'AAPL': {'score': 8}},
        'positions': {'AAPL': 100}
    }
    
    # Post to Slack
    post_to_slack(summary, webhook_url=os.environ['SLACK_URL'])
    
    # Verify request
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert kwargs['json'] == summary
    assert kwargs['headers'] == {'Content-Type': 'application/json'}

@patch('src.jobs.nightly_job.get_f_score')
@patch('src.jobs.nightly_job.get_sma')
@patch('src.jobs.nightly_job.explain_with_fingpt')
@patch('src.jobs.nightly_job.submit_bracket')
@patch('src.jobs.nightly_job.post_to_slack')
def test_main_dry_run(
    mock_post_slack,
    mock_submit_bracket,
    mock_explain,
    mock_get_sma,
    mock_get_f_score,
    mock_config,
    tmp_path,
    mock_env_vars
):
    """Test main function in dry-run mode."""
    # Setup mocks
    mock_get_f_score.return_value = MOCK_F_SCORES
    mock_get_sma.return_value = MOCK_SMA_DATA
    mock_explain.side_effect = lambda x: MOCK_EXPLANATIONS.get(x, 'No explanation')
    
    # Create test config
    config_path = tmp_path / "test_config.yml"
    config_path.write_text("""
    strategy: test_strategy
    filters:
        f_score: 7
        sma_200: true
    """)
    
    # Run main in dry-run mode
    with patch('sys.argv', ['nightly_job.py', '--config', str(config_path), '--dry-run', '--verbose']):
        main()
    
    # Verify results
    assert not mock_submit_bracket.called  # No orders in dry-run
    assert mock_post_slack.called  # Slack notification sent
    
    # Verify memo was written
    memo_path = 'reports/buffett_memo.txt'
    assert os.path.exists(memo_path)
    with open(memo_path, 'r') as f:
        memo_content = f.read()
        assert 'Buffett Screener Results' in memo_content
        assert 'AAPL' in memo_content
        assert 'MSFT' in memo_content

@patch('src.jobs.nightly_job.get_f_score')
@patch('src.jobs.nightly_job.get_sma')
@patch('src.jobs.nightly_job.explain_with_fingpt')
@patch('src.jobs.nightly_job.submit_bracket')
@patch('src.jobs.nightly_job.post_to_slack')
def test_main_live(
    mock_post_slack,
    mock_submit_bracket,
    mock_explain,
    mock_get_sma,
    mock_get_f_score,
    mock_config,
    tmp_path,
    mock_env_vars
):
    """Test main function in live mode."""
    # Setup mocks
    mock_get_f_score.return_value = MOCK_F_SCORES
    mock_get_sma.return_value = MOCK_SMA_DATA
    mock_explain.side_effect = lambda x: MOCK_EXPLANATIONS.get(x, 'No explanation')
    
    # Create test config
    config_path = tmp_path / "test_config.yml"
    config_path.write_text("""
    strategy: test_strategy
    filters:
        f_score: 7
        sma_200: true
    """)
    
    # Run main in live mode
    with patch('sys.argv', ['nightly_job.py', '--config', str(config_path), '--live', '--verbose']):
        main()
    
    # Verify results
    assert mock_submit_bracket.called  # Orders submitted
    assert mock_post_slack.called  # Slack notification sent
    
    # Verify memo was written
    memo_path = 'reports/buffett_memo.txt'
    assert os.path.exists(memo_path)
    with open(memo_path, 'r') as f:
        memo_content = f.read()
        assert 'Buffett Screener Results' in memo_content
        assert 'AAPL' in memo_content
        assert 'MSFT' in memo_content

def test_get_top_stocks_empty(mock_config):
    """Test get_top_stocks returns empty DataFrame if no stocks pass filter."""
    with patch('src.jobs.nightly_job.get_f_score', return_value=pd.DataFrame({'score': [5, 6], 'close': [100, 100], 'atr': [2, 2]}, index=['AAA', 'BBB'])), \
         patch('src.jobs.nightly_job.get_sma', return_value=pd.DataFrame({'close': [100, 100], 'sma_200': [110, 110]}, index=['AAA', 'BBB'])):
        result = get_top_stocks(mock_config)
        assert result.empty

@patch('requests.post')
def test_post_to_slack_network_error(mock_post, mock_env_vars):
    """Test Slack notification handles network error gracefully."""
    mock_post.side_effect = Exception("Network error")
    summary = {
        'timestamp': datetime.now().isoformat(),
        'strategy': 'test',
        'stocks': {'AAPL': {'score': 8}},
        'positions': {'AAPL': 100}
    }
    # Should not raise
    post_to_slack(summary, webhook_url=os.environ['SLACK_URL'])
    mock_post.assert_called_once() 