# Buffett Screener

A quantitative stock screening and automated trading system inspired by Warren Buffett's value investing principles.

![Buffett Screener](https://img.shields.io/badge/buffett-screener-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen)

## Overview

Buffett Screener combines fundamental analysis, technical indicators, and modern portfolio theory to identify high-quality value stocks with strong financials and favorable price action. The system implements a systematic approach to:

1. **Screen stocks** based on Piotroski F-Score and other quality metrics
2. **Validate strategies** with historical data backtesting
3. **Generate explanations** using FinGPT for selected stocks
4. **Manage risk** with sophisticated position sizing and portfolio constraints
5. **Automate trading** through broker APIs with proper risk controls

## Key Features

- **Fundamental Analysis**
  - Piotroski F-Score implementation
  - Comprehensive financial metrics (ROE, ROA, P/E, P/B, growth rates)
  - Industry comparison and relative strength

- **Technical Analysis**
  - SMA, RSI, ATR indicators
  - Price action trend following
  - Volatility-based position sizing

- **AI-Powered Insights**
  - FinGPT-2 explanations for stock picks
  - Natural language analysis of fundamentals
  - Semantic search for similar historical setups

- **Risk Management**
  - ATR-based position sizing
  - Portfolio-level risk constraints
  - Trailing stop loss implementation
  - Dynamic position adjustment

- **Strategy Validation**
  - Historical backtesting with proper metrics
  - Market condition analysis
  - Performance across different regimes

- **Execution & Monitoring**
  - Automated order execution
  - Streamlit dashboard for monitoring
  - Slack notifications for trades and alerts

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/buffett_screener.git
cd buffett_screener

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Create your configuration files in the `configs/` directory:

```yaml
# configs/long_term.yml
holding_days: 90
risk_pct: 0.005
mode: long

# configs/swing.yml
holding_days: 5
exit_rsi_gt: 70
trail_pct: 0.02
risk_pct: 0.01
mode: swing
```

## Usage

### Running the Nightly Job

```bash
# Dry run (no orders submitted)
python src/jobs/nightly_job.py --dry-run --verbose

# Live trading
python src/jobs/nightly_job.py --live --config configs/long_term.yml
```

### Backtesting

```bash
python src/validation/backtest.py
```

### Dashboard

```bash
streamlit run app/main.py
```

## Project Architecture

```
├── app/                  # Streamlit dashboard
├── configs/              # Strategy configuration files
├── src/
│   ├── backtest/         # Backtesting tools
│   ├── execution/        # Order execution
│   ├── jobs/             # Scheduled jobs
│   ├── llm/              # FinGPT integration
│   ├── risk/             # Position sizing and risk management
│   ├── scoring/          # F-score and other metrics
│   ├── technical/        # Technical indicators
│   └── validation/       # Strategy validation
├── tests/                # Unit and integration tests
└── reports/              # Generated reports and memos
```

## Technologies Used

- **Core**: Python, Pandas, NumPy
- **Data Sources**: yfinance, Alpaca, Financial Modeling Prep
- **ML/AI**: FinGPT-2, Transformers, embedding models
- **Visualization**: Streamlit, Matplotlib, vectorbt
- **Testing**: pytest, GitHub Actions
- **DevOps**: Docker, GitHub Actions

## Development

### Running Tests

```bash
# Run all tests
python -m pytest

# Run tests with coverage
python -m pytest --cov=src
```

### Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` for more information.

## Acknowledgements

- [Piotroski F-Score](https://www.jstor.org/stable/2353324)
- [FinGPT](https://github.com/AI4Finance-Foundation/FinGPT)
- [vectorbt](https://github.com/polakowo/vectorbt) 