#!/bin/bash

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
  echo "Activating virtual environment..."
  source .venv/bin/activate
fi

# Install the package in development mode
echo "Installing package in development mode..."
pip install -e .

# Set the PYTHONPATH to include the project root
export PYTHONPATH=$(pwd):$PYTHONPATH
echo "Setting PYTHONPATH to include project root: $PYTHONPATH"

# Check if Streamlit is installed
if ! command -v streamlit &> /dev/null; then
  echo "Streamlit not found, installing..."
  pip install streamlit matplotlib
fi

# Run the Streamlit app
echo "Starting Buffett Screener..."
streamlit run app/main.py 