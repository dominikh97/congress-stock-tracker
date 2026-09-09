import json
import os
import requests

# Free, keyless, no-rate-limit JSON feed. Committed daily to a public MIT
# repo that aggregates House Clerk PTRs, Senate eFD filings and OGE
# executive filings (kadoa-org/congress-trading-monitor). Served over
# GitHub's raw CDN, so there's nothing to sign up for and nothing to break.
API_URL = "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data/trades.json"
DATA_FILE = "data/trades.json"


def normalize_trade_type(raw_type):
    """Collapse the source's STOCK Act wording into Buy/Sell/<raw>."""

    label = (raw_type or "").strip()

    if label.startswith("Purchase"):
        return "Buy"

    if label.startswith("Sale"):
        return "Sell"

    return label


def normalize_trade(record):
    """Map a kadoa-org trade record onto this project's trade schema."""

    return {
        "id": record.get("id"),
        "member": record.get("filer_name"),
        "chamber": record.get("chamber"),
        "ticker": record.get("ticker"),
        "trade_type": normalize_trade_type(record.get("transaction_type")),
        "amount": record.get("amount_range_label"),
        "tx_date": record.get("transaction_date"),
        "disclosed": record.get("filing_date"),
        "asset": record.get("asset_name"),
        "link": record.get("doc_url"),
    }


def fetch_trades():
    """Fetch the latest congressional trades feed and normalize it."""

    print("Fetching congressional trades...")

    response = requests.get(API_URL, timeout=30)

    print("Status code:", response.status_code)

    response.raise_for_status()

    records = response.json()

    # Congress-only: the feed also carries OGE executive-branch filings,
    # which fall outside this tracker's scope and lack a chamber value.
    congress_records = [
        r for r in records if r.get("chamber") in ("house", "senate")
    ]

    trades = [normalize_trade(r) for r in congress_records]

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
    """Use the source's own stable trade ID."""

    return str(trade.get("id", ""))


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
