import json
import os
import time
import requests

API_URL = "https://congressinfor-production.up.railway.app/trades/recent"


def fetch_trades(days=2, limit=10):

    params = {
        "days": days,
        "limit": limit
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30
    )

    if response.status_code == 429:
        print("API rate limit reached. Waiting 60 seconds...")
        time.sleep(60)

        response = requests.get(
            API_URL,
            params=params,
            timeout=30
        )

    response.raise_for_status()

    return response.json().get("trades", [])


def main():

    print("Fetching congressional trades...")

    trades = fetch_trades()

    print(f"Fetched {len(trades)} trades")

    os.makedirs("data", exist_ok=True)

    with open("data/trades.json", "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, ensure_ascii=False)

    print("Saved trades to data/trades.json")


if __name__ == "__main__":
    main()
