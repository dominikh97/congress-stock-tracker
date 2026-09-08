import json
import os
import requests

API_URL = "https://congressinfor-production.up.railway.app/trades/recent"
DATA_FILE = "data/trades.json"


def fetch_trades(days=7, limit=10):
    """Fetch recent congressional trades from the API."""

    print("Fetching congressional trades...")

    response = requests.get(
        API_URL,
        params={
            "days": days,
            "limit": limit
        },
        timeout=30
    )

    response.raise_for_status()

    trades = response.json().get("trades", [])

    print(f"Fetched {len(trades)} trades")

    return trades


def load_existing_trades():
    """Load existing trades if the file already exists."""

    if not os.path.exists(DATA_FILE):
        print("No existing trades.json found.")
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        trades = json.load(f)

    print(f"Loaded {len(trades)} existing trades")

    return trades


def get_trade_id(trade):
    """Create a unique identifier for each trade."""

    if trade.get("id") is not None:
        return str(trade["id"])

    return json.dumps(
        trade,
        sort_keys=True,
        ensure_ascii=False
    )


def merge_trades(existing, new):
    """Merge existing and new trades while removing duplicates."""

    combined = existing + new
    unique_trades = {}

    for trade in combined:
        trade_id = get_trade_id(trade)
        unique_trades[trade_id] = trade

    merged = list(unique_trades.values())

    print(f"Total unique trades: {len(merged)}")

    return merged


def save_trades(trades):
    """Save trades to trades.json."""

    os.makedirs("data", exist_ok=True)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            trades,
            f,
            indent=2,
            ensure_ascii=False
        )

    print(f"Saved {len(trades)} trades to {DATA_FILE}")


def main():

    new_trades = fetch_trades()

    existing_trades = load_existing_trades()

    all_trades = merge_trades(
        existing_trades,
        new_trades
    )

    save_trades(all_trades)


if __name__ == "__main__":
    main()
