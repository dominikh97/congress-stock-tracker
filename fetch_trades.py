```python
import requests

from database import init_database, insert_trade


API_URL = (
    "https://congressinfor-production.up.railway.app"
    "/trades/recent"
)


def fetch_trades(days=7):

    response = requests.get(
        API_URL,
        params={
            "days": days,
            "limit": 500,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("trades", [])


def main():

    print("Fetching congressional trades...")

    init_database()

    trades = fetch_trades(days=7)

    new_trades = 0

    for trade in trades:

        if insert_trade(trade):
            new_trades += 1

    print(f"Fetched: {len(trades)} trades")
    print(f"New trades: {new_trades}")


if __name__ == "__main__":
    main()
```
