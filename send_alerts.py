import json
import os
import requests

NEW_TRADES_FILE = "data/new_trades.json"


def load_json(path, default):
    """Load a JSON file, falling back to a default if it's missing."""

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_subscriptions():
    """Pull confirmed subscriptions from the Cloudflare Worker.

    Returns None (meaning "skip, nothing configured") when the Worker
    URL or API key aren't set, so a fresh checkout without secrets
    doesn't fail the daily fetch job.
    """

    worker_url = os.environ.get("ALERTS_WORKER_URL", "").rstrip("/")
    api_key = os.environ.get("SUBSCRIPTIONS_API_KEY")

    if not worker_url or not api_key:
        print(
            "ALERTS_WORKER_URL / SUBSCRIPTIONS_API_KEY not set - "
            "skipping email alerts."
        )
        return None

    response = requests.get(
        f"{worker_url}/alert-recipients",
        headers={"X-Api-Key": api_key},
        timeout=15,
    )
    response.raise_for_status()

    return response.json()


def matching_emails(trade, subscriptions):
    """Subscriber emails whose member list includes this trade's filer."""

    member = (trade.get("member") or "").strip().lower()

    return [
        sub["email"] for sub in subscriptions
        if member in {m.strip().lower() for m in sub.get("members", [])}
    ]


def build_email_body(member, trades):

    lines = [f"New trade filing(s) for {member}:", ""]

    for t in trades:
        symbol = t.get("ticker") or t.get("company") or "Unknown asset"

        lines.append(
            f"- {t.get('trade_type')} {symbol} ({t.get('amount')}) "
            f"— transacted {t.get('tx_date')}, "
            f"disclosed {t.get('disclosed')}"
        )

        if t.get("link"):
            lines.append(f"  Filing: {t['link']}")

    return "\n".join(lines)


def send_email(api_key, from_email, to_address, subject, body):

    response = requests.post(
        "https://api.sendgrid.com/v3/mail/send",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "personalizations": [{"to": [{"email": to_address}]}],
            "from": {"email": from_email, "name": "Congress Stock Tracker"},
            "subject": subject,
            "content": [{"type": "text/plain", "value": body}],
        },
        timeout=15,
    )
    response.raise_for_status()


def main():

    new_trades = load_json(NEW_TRADES_FILE, [])

    if not new_trades:
        print("No newly seen trades, nothing to alert on.")
        return

    subscriptions = fetch_subscriptions()

    if subscriptions is None:
        return

    if not subscriptions:
        print("No confirmed subscriptions, nothing to alert on.")
        return

    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("FROM_EMAIL")

    if not (sendgrid_key and from_email):
        print(
            "SENDGRID_API_KEY / FROM_EMAIL not set - skipping email alerts."
        )
        return

    # Group newly seen trades by (recipient, member) so someone who
    # gets multiple hits in one run gets a single email, not several.
    per_recipient = {}

    for trade in new_trades:
        for email in matching_emails(trade, subscriptions):
            key = (email, trade.get("member"))
            per_recipient.setdefault(key, []).append(trade)

    for (email, member), trades in per_recipient.items():

        subject = f"Congress Stock Tracker: new trade filed by {member}"
        body = build_email_body(member, trades)

        try:
            send_email(sendgrid_key, from_email, email, subject, body)
            print(
                f"Sent alert to {email} for {member} "
                f"({len(trades)} trade(s))"
            )
        except Exception as exc:
            print(f"Failed to send alert to {email} for {member}: {exc}")


if __name__ == "__main__":
    main()
