import sqlite3
import requests
from pathlib import Path

API_URL = "https://congressinfor-production.up.railway.app/trades/recent"

DB_PATH = Path("data/trades.db")


def init_database():
    DB_PATH.parent.mkdir(exist_ok=True)

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member TEXT NOT NULL,
                chamber TEXT,
                ticker TEXT,
                trade_type TEXT,
                amount TEXT,
                tx_date TEXT,
                disclosed TEXT,
                asset TEXT,
                link TEXT,
                UNIQUE(member, ticker, trade_type, tx_date, disclosed, amount)
            )
        """)


def fetch_trades(days=7):
    response = requests.get(
        API_URL,
        params={
            "days": days,
            "limit": 500
        },
        timeout=30
    )

    response.raise_for_status()
    return response.json()["trades"]


def store_trades(trades):
    new_trades = 0

    with sqlite3.connect(DB_PATH) as conn:
        for trade in trades:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO trades (
                    member,
                    chamber,
                    ticker,
                    trade_type,
                    amount,
                    tx_date,
                    disclosed,
                    asset,
                    link
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.get("member"),
                trade.get("chamber"),
                trade.get("ticker"),
                trade.get("trade_type"),
                trade.get("amount"),
                trade.get("tx_date"),
                trade.get("disclosed"),
                trade.get("asset"),
                trade.get("link")
            ))

            if cursor.rowcount:
                new_trades += 1

    return new_trades


def main():
    print("Fetching congressional trades...")

    init_database()

    trades = fetch_trades(days=7)
    new_trades = store_trades(trades)

    print(f"Fetched: {len(trades)} trades")
    print(f"New trades: {new_trades}")


if __name__ == "__main__":
    main()
