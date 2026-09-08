import json
import os
import requests

API_URL = "https://quantengines.com/api/v1/trades/recent/list"
DATA_FILE = "data/trades.json"


def fetch_trades(limit=100):
    """Fetch the most recent congressional trades."""

    print("Fetching congressional trades...")

    response = requests.get(
        API_URL,
        params={
            "limit": limit
        },
        timeout=30
    )

    print("Status code:", response.status_code)
    print("Response:")
    print(response.text[:5000])

    response.raise_for_status()

    data = response.json()

    print("Response type:", type(data))

    if isinstance(data, dict):
        print("Response keys:", data.keys())

    trades = data.get("trades", []) if isinstance(data, dict) else data

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
    """Use the API trade ID to identify a trade."""

    if trade.get("id") is not None:
        return str(trade["id"])

    # Fallback if an ID is not provided
    return json.dumps(
        trade,
        sort_keys=True,
        ensure_ascii=False
    )


def merge_trades(existing, new):
    """Merge existing and new trades and remove duplicates."""

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
