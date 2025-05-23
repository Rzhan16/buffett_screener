#!/bin/bash
# Buffett Stock Screener Runner
# This script sets up the environment and runs the Buffett Stock Screener

# Print header
echo "================================"
echo "   STOCK SCREENER TOOLKIT"
echo "================================"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
fi

# Set the PYTHONPATH to include the project root
export PYTHONPATH=$(pwd):$PYTHONPATH
echo "Setting PYTHONPATH to include project root: $(pwd)"

# Function to run the live screener with parameters
run_live_screener() {
  UNIVERSE=${1:-"MOCK_AFFORDABLE"}
  BUYING_POWER=${2:-41000}
  MIN_F_SCORE=${3:-5}
  MIN_PRICE=${4:-1}
  MAX_PRICE=${5:-1000}
  
  echo "Running Buffett Screener with LIVE market data..."
  echo "Universe: $UNIVERSE"
  echo "Buying Power: $BUYING_POWER"
  echo "Min F-Score: $MIN_F_SCORE"
  echo "Price Range: $MIN_PRICE - $MAX_PRICE"
  
  python run_live_screener.py "$UNIVERSE" \
    --buying-power "$BUYING_POWER" \
    --min-fscore "$MIN_F_SCORE" \
    --min-price "$MIN_PRICE" \
    --max-price "$MAX_PRICE"
}

# Function to run the growth screener with parameters
run_growth_screener() {
  MAX_PRICE=${1:-20}
  MIN_PRICE=${2:-1}
  MIN_GROWTH=${3:-50}
  UNIVERSE=${4:-"ALL"}
  MAX_STOCKS=${5:-10}
  
  echo "Running Growth Stock Screener..."
  echo "Price Range: $MIN_PRICE - $MAX_PRICE"
  echo "Min Growth Score: $MIN_GROWTH/100"
  echo "Universe: $UNIVERSE"
  echo "Max Stocks: $MAX_STOCKS"
  
  python run_growth_screener.py \
    --max-price "$MAX_PRICE" \
    --min-price "$MIN_PRICE" \
    --min-growth "$MIN_GROWTH" \
    --universe "$UNIVERSE" \
    --max-stocks "$MAX_STOCKS"
}

# Function to run the value screener with parameters
run_value_screener() {
  MAX_PRICE=${1:-""}
  MIN_PRICE=${2:-""}
  MIN_BUFFETT=${3:-70}
  UNIVERSE=${4:-"SP500"}
  MAX_STOCKS=${5:-10}
  
  echo "Running Buffett Value Stock Screener..."
  
  # Handle optional price parameters
  PRICE_ARGS=""
  if [ ! -z "$MAX_PRICE" ]; then
    PRICE_ARGS="$PRICE_ARGS --max-price $MAX_PRICE"
  fi
  if [ ! -z "$MIN_PRICE" ]; then
    PRICE_ARGS="$PRICE_ARGS --min-price $MIN_PRICE"
  fi
  
  echo "Price Range: ${MIN_PRICE:-"No minimum"} - ${MAX_PRICE:-"No maximum"}"
  echo "Min Buffett Score: $MIN_BUFFETT/100"
  echo "Universe: $UNIVERSE"
  echo "Max Stocks: $MAX_STOCKS"
  
  python run_value_screener.py \
    $PRICE_ARGS \
    --min-buffett "$MIN_BUFFETT" \
    --universe "$UNIVERSE" \
    --max-stocks "$MAX_STOCKS"
}

# Check command line arguments
if [ "$1" == "--app" ] || [ "$1" == "-a" ]; then
  # Run the Streamlit app
  echo "Starting Buffett Screener web app..."
  streamlit run app/main.py
elif [ "$1" == "--mock" ] || [ "$1" == "-m" ]; then
  # Run with mock data
  echo "Running Buffett Screener with mock data..."
  python run_buffett_memo.py
elif [ "$1" == "--live" ] || [ "$1" == "-l" ]; then
  # Run with live data
  shift # Remove the --live argument
  run_live_screener "$@" # Pass all remaining arguments to the live screener
elif [ "$1" == "--growth" ] || [ "$1" == "-g" ]; then
  # Run growth screener
  shift # Remove the --growth argument
  run_growth_screener "$@" # Pass all remaining arguments to the growth screener
elif [ "$1" == "--value" ] || [ "$1" == "-v" ]; then
  # Run value screener
  shift # Remove the --value argument
  run_value_screener "$@" # Pass all remaining arguments to the value screener
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
  # Show detailed help
  echo "Stock Screener Toolkit - Value investing and growth stock tools"
  echo ""
  echo "Usage: ./run_buffett_screener.sh [OPTION] [PARAMETERS]"
  echo ""
  echo "Options:"
  echo "  --app, -a                   Run the Streamlit web app"
  echo "  --mock, -m                  Run with mock data (fast)"
  echo "  --live, -l [PARAMETERS]     Run with live market data (slower, more accurate)"
  echo "  --growth, -g [PARAMETERS]   Run the growth stock screener (find small-cap growth stocks under $20)"
  echo "  --value, -v [PARAMETERS]    Run the Buffett value stock screener (find stocks with strong moats and financials)"
  echo "  --help, -h                  Show this help message"
  echo ""
  echo "Value Screener Parameters (in order):"
  echo "  1. UNIVERSE     Stock universe to screen (default: MOCK_AFFORDABLE)"
  echo "                  Options: SP500, NASDAQ, RUSSELL2000, ALL, MOCK_AFFORDABLE"
  echo "  2. BUYING_POWER Account buying power in dollars (default: 41000)"
  echo "  3. MIN_F_SCORE  Minimum F-Score 1-9 (default: 5)"
  echo "  4. MIN_PRICE    Minimum stock price (default: 1)"
  echo "  5. MAX_PRICE    Maximum stock price (default: 1000)"
  echo ""
  echo "Growth Screener Parameters (in order):"
  echo "  1. MAX_PRICE    Maximum stock price (default: 20)"
  echo "  2. MIN_PRICE    Minimum stock price (default: 1)"
  echo "  3. MIN_GROWTH   Minimum growth score 0-100 (default: 50)"
  echo "  4. UNIVERSE     Stock universe (default: ALL)"
  echo "  5. MAX_STOCKS   Maximum number of stocks to return (default: 10)"
  echo ""
  echo "Buffett Value Screener Parameters (in order):"
  echo "  1. MAX_PRICE    Maximum stock price (optional)"
  echo "  2. MIN_PRICE    Minimum stock price (optional)"
  echo "  3. MIN_BUFFETT  Minimum Buffett score 0-100 (default: 70)"
  echo "  4. UNIVERSE     Stock universe (default: SP500)"
  echo "  5. MAX_STOCKS   Maximum number of stocks to return (default: 10)"
  echo ""
  echo "Examples:"
  echo "  ./run_buffett_screener.sh --app"
  echo "  ./run_buffett_screener.sh --mock"
  echo "  ./run_buffett_screener.sh --live SP500 100000 7 100 500"
  echo "  ./run_buffett_screener.sh --growth 20 1 50 ALL 10"
  echo "  ./run_buffett_screener.sh --value 300 50 75 SP500 5"
else
  # Show usage information
  echo "Usage: ./run_buffett_screener.sh [OPTION]"
  echo ""
  echo "Options:"
  echo "  --app, -a     Run the Streamlit web app"
  echo "  --mock, -m    Run with mock data (fast)"
  echo "  --live, -l    Run with live market data (slower, more accurate)"
  echo "  --growth, -g  Find high-potential growth stocks under $20 (NBIS, RXRX style)"
  echo "  --value, -v   Find Buffett-style value stocks with strong moats and financials"
  echo "  --help, -h    Show detailed help and parameters"
  echo ""
  echo "Examples:"
  echo "  ./run_buffett_screener.sh --app"
  echo "  ./run_buffett_screener.sh --live SP500"
  echo "  ./run_buffett_screener.sh --growth"
  echo "  ./run_buffett_screener.sh --value"
fi

# Provide next step instructions
if [ "$1" == "--live" ] || [ "$1" == "-l" ] || [ "$1" == "--mock" ] || [ "$1" == "-m" ]; then
  echo ""
  echo "Memo generated and saved to buffett_memo.md"
  echo "To view the memo, use one of these commands:"
  echo "  cat buffett_memo.md"
  echo "  open buffett_memo.md     (on macOS)"
elif [ "$1" == "--growth" ] || [ "$1" == "-g" ]; then
  echo ""
  echo "Growth stock recommendations saved to growth_stocks.md"
  echo "To view the recommendations, use one of these commands:"
  echo "  cat growth_stocks.md"
  echo "  open growth_stocks.md     (on macOS)"
elif [ "$1" == "--value" ] || [ "$1" == "-v" ]; then
  echo ""
  echo "Value stock recommendations saved to value_stocks.md"
  echo "To view the recommendations, use one of these commands:"
  echo "  cat value_stocks.md"
  echo "  open value_stocks.md     (on macOS)"
fi 