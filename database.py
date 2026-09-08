```python
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "trades.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_database():
    with get_connection() as conn:
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
                UNIQUE(
                    member,
                    ticker,
                    trade_type,
                    tx_date,
                    disclosed,
                    amount
                )
            )
        """)

        conn.commit()


def insert_trade(trade):
    with get_connection() as conn:
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
            trade.get("link"),
        ))

        conn.commit()

        return cursor.rowcount == 1


if __name__ == "__main__":
    init_database()
    print(f"Database initialized at: {DB_PATH}")
```
