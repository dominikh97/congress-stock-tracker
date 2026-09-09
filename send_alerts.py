import json
import os

from email_utils import load_smtp_config, send_email

NEW_TRADES_FILE = "data/new_trades.json"
ALERTS_CONFIG_FILE = "alerts.json"


def load_json(path, default):
    """Load a JSON file, falling back to a default if it's missing."""

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def matching_subscribers(trade, subscriptions):
    """Subscriptions whose member name matches this trade's filer."""

    member = (trade.get("member") or "").strip().lower()

    return [
        sub for sub in subscriptions
        if (sub.get("member") or "").strip().lower() == member
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


def main():

    new_trades = load_json(NEW_TRADES_FILE, [])
    subscriptions = load_json(ALERTS_CONFIG_FILE, [])

    if not new_trades:
        print("No newly seen trades, nothing to alert on.")
        return

    if not subscriptions:
        print("No entries in alerts.json, nothing to alert on.")
        return

    smtp_config = load_smtp_config()

    if smtp_config is None:
        print(
            "SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD are not set "
            "(see README) - skipping email alerts."
        )
        return

    # Group newly seen trades by (recipient, member) so someone who
    # gets multiple hits in one run gets a single email, not several.
    per_recipient = {}

    for trade in new_trades:
        for sub in matching_subscribers(trade, subscriptions):
            key = (sub["email"], trade.get("member"))
            per_recipient.setdefault(key, []).append(trade)

    for (email, member), trades in per_recipient.items():

        subject = f"Congress Stock Tracker: new trade filed by {member}"
        body = build_email_body(member, trades)

        try:
            send_email(smtp_config, email, subject, body)
            print(
                f"Sent alert to {email} for {member} "
                f"({len(trades)} trade(s))"
            )
        except Exception as exc:
            print(f"Failed to send alert to {email} for {member}: {exc}")


if __name__ == "__main__":
    main()
