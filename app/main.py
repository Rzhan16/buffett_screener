import streamlit as st
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Buffett Screener Dashboard", layout="wide")

# --- Sidebar ---
st.sidebar.title("Screener Controls")

# Date range selector
def_date = date.today()
def_start = def_date - timedelta(days=30)
date_range = st.sidebar.date_input(
    "Date Range",
    value=(def_start, def_date),
    min_value=date(2000, 1, 1),
    max_value=def_date
)

# Config selector
config_option = st.sidebar.selectbox(
    "Strategy Config",
    options=["long_term", "swing"],
    index=0
)

# --- Main ---
st.title("Today's Picks")

# Placeholder for picks DataTable
def get_mock_picks():
    return pd.DataFrame({
        'symbol': ['AAPL', 'MSFT', 'GOOG'],
        'score': [8, 7, 9],
        'SMA': [150, 200, 180],
        '$size': [10000, 8000, 12000]
    })

picks_df = get_mock_picks()
st.dataframe(picks_df, use_container_width=True)

# --- Price Chart (streaming) ---
st.subheader("Live Price Chart")
# Placeholder for real-time chart (to be replaced with Alpaca websocket integration)
st.line_chart(picks_df.set_index('symbol')['SMA'])

# --- Vectorbt Equity Curve ---
st.subheader("Equity Curve (Vectorbt)")
# Placeholder for equity curve image
st.image("reports/AAPL_2015-01-01_2020-12-31_bt.png", caption="Equity Curve", use_container_width=True)

# --- Auto-refresh every 30 seconds ---
st.experimental_rerun = lambda: None  # Patch for linter
if 'last_refresh' not in st.session_state or (pd.Timestamp.now() - st.session_state['last_refresh']).seconds > 30:
    st.session_state['last_refresh'] = pd.Timestamp.now()
    st.experimental_rerun() 