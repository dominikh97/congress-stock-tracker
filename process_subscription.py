import json
import os
import re

TRADES_FILE = "data/trades.json"
ALERTS_FILE = "alerts.json"
MAX_MEMBERS = 20

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)


def load_json(path, default):

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def known_members():
    """The set of member names this tracker currently has data for.

    Doubles as the allow-list for subscription requests, so it can
    never drift out of sync with what the frontend's politician picker
    shows (both read data/trades.json).
    """

    trades = load_json(TRADES_FILE, [])

    return {t.get("member") for t in trades if t.get("member")}


def extract_payload(body):

    match = JSON_BLOCK_RE.search(body or "")

    if not match:
        return None

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def validate(payload, valid_members):

    if not isinstance(payload, dict):
        return None, (
            "Couldn't find a valid subscription block in this issue. "
            "Please use the Email Alerts tab on the site to subscribe."
        )

    email = str(payload.get("email", "")).strip()
    members = payload.get("members")

    if not EMAIL_RE.match(email):
        return None, f"'{email}' doesn't look like a valid email address."

    if not isinstance(members, list) or not members:
        return None, "No politicians were selected."

    if len(members) > MAX_MEMBERS:
        return None, f"Too many politicians selected (max {MAX_MEMBERS})."

    cleaned = []
    unknown = []

    for m in members:
        name = str(m).strip()

        if name in valid_members:
            cleaned.append(name)
        else:
            unknown.append(name)

    if unknown:
        return None, f"Unrecognized politician name(s): {', '.join(unknown)}."

    return {"email": email, "members": cleaned}, None


def write_output(key, value):
    """Write a (possibly multiline) value to GITHUB_OUTPUT safely."""

    output_file = os.environ.get("GITHUB_OUTPUT")

    if not output_file:
        return

    delimiter = "EOF_OUTPUT"

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def main():

    body = os.environ.get("ISSUE_BODY", "")

    valid_members = known_members()
    payload = extract_payload(body)

    result, error = validate(payload, valid_members)

    if error:
        print(f"Subscription rejected: {error}")
        write_output("status", "rejected")
        write_output("message", f"Sorry, I couldn't process this: {error}")
        write_output("changed", "false")
        return

    alerts = load_json(ALERTS_FILE, [])

    existing = {
        (
            a.get("member", "").strip().lower(),
            a.get("email", "").strip().lower()
        )
        for a in alerts
    }

    added = []

    for member in result["members"]:

        key = (member.strip().lower(), result["email"].strip().lower())

        if key in existing:
            continue

        alerts.append({"member": member, "email": result["email"]})
        existing.add(key)
        added.append(member)

    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2, ensure_ascii=False)
        f.write("\n")

    if added:
        message = (
            f"Subscribed {result['email']} to trade alerts for: "
            f"{', '.join(added)}. You'll get an email the next time "
            f"one of them files a new trade."
        )
    else:
        message = (
            f"{result['email']} was already subscribed to all "
            f"selected politicians - nothing to do."
        )

    print(message)
    write_output("status", "confirmed")
    write_output("message", message)
    write_output("changed", "true" if added else "false")


if __name__ == "__main__":
    main()
