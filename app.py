import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st


DB_PATH = Path("data/trades.db")


st.set_page_config(
    page_title="Congress Stock Tracker",
    page_icon="📈",
    layout="wide",
)


@st.cache_data(ttl=300)
def load_trades():
    if not DB_PATH.exists():
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            """
            SELECT
                member,
                chamber,
                ticker,
                trade_type,
                amount,
                tx_date,
                disclosed,
                asset,
                link
            FROM trades
            ORDER BY disclosed DESC
            """,
            conn,
        )


# ---------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------

st.title("Congress Stock Tracker")
st.caption("Tracking publicly disclosed stock transactions by U.S. Congress members")


# ---------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------

df = load_trades()

if df.empty:
    st.warning(
        "No trades found. Run `python fetch_trades.py` to populate the database."
    )
    st.stop()


# ---------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------

st.sidebar.header("Filters")

members = sorted(df["member"].dropna().unique())

selected_members = st.sidebar.multiselect(
    "Politician",
    members,
)

chambers = sorted(df["chamber"].dropna().unique())

selected_chambers = st.sidebar.multiselect(
    "Chamber",
    chambers,
)

trade_types = sorted(df["trade_type"].dropna().unique())

selected_trade_types = st.sidebar.multiselect(
    "Transaction",
    trade_types,
)


# ---------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------

filtered = df.copy()

if selected_members:
    filtered = filtered[
        filtered["member"].isin(selected_members)
    ]

if selected_chambers:
    filtered = filtered[
        filtered["chamber"].isin(selected_chambers)
    ]

if selected_trade_types:
    filtered = filtered[
        filtered["trade_type"].isin(selected_trade_types)
    ]


# ---------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric(
    "Trades",
    len(filtered),
)

col2.metric(
    "Politicians",
    filtered["member"].nunique(),
)

col3.metric(
    "Stocks",
    filtered["ticker"].nunique(),
)


st.divider()


# ---------------------------------------------------------------------
# Trades table
# ---------------------------------------------------------------------

st.subheader("Latest disclosed trades")

display_df = filtered.copy()

display_df = display_df.rename(
    columns={
        "member": "Politician",
        "chamber": "Chamber",
        "ticker": "Ticker",
        "trade_type": "Transaction",
        "amount": "Amount",
        "tx_date": "Transaction Date",
        "disclosed": "Disclosed",
        "asset": "Asset",
        "link": "Filing",
    }
)

# Make filing links clickable
if "Filing" in display_df.columns:
    display_df["Filing"] = display_df["Filing"].apply(
        lambda x: f"[View filing]({x})" if pd.notna(x) and x else ""
    )

st.markdown(
    display_df.to_markdown(index=False),
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------
# Last update
# ---------------------------------------------------------------------

st.divider()

st.caption(
    f"Showing {len(filtered)} of {len(df)} stored trades."
)
