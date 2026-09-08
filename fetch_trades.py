from database import insert_trade
import requests


API_URL = (
    "https://congressinfor-production.up.railway.app"
    "/trades/recent"
)


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

    return response.json().get("trades", [])


def main():

    print("Fetching congressional trades...")

    trades = fetch_trades()

    print(f"Fetched {len(trades)} trades.")

    for trade in trades:
        insert_trade(trade)

    print("Database updated.")


if __name__ == "__main__":
    main()
