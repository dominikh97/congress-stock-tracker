import time
import requests

def fetch_trades(days=2):

    response = requests.get(
        API_URL,
        params={
            "days": days,
            "limit": 200
        },
        timeout=30
    )

    if response.status_code == 429:
        print("API rate limit reached. Waiting 60 seconds...")
        time.sleep(60)

        response = requests.get(
            API_URL,
            params={
                "days": days,
                "limit": 200
            },
            timeout=30
        )

    response.raise_for_status()

    return response.json().get("trades", [])
