import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from email_utils import load_smtp_config, send_email

TRADES_FILE = "data/trades.json"
ALERTS_FILE = "alerts.json"
PENDING_FILE = "pending_subscriptions.json"

MAX_MEMBERS = 20
TOKEN_EXPIRY_HOURS = 48
REPO_URL = "https://github.com/dominikh97/congress-stock-tracker"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.S)

SUBSCRIBE_PREFIX = "Subscribe request:"
CONFIRM_PREFIX = "Confirm subscription:"
UNSUBSCRIBE_PREFIX = "Unsubscribe request:"


# --- small helpers --------------------------------------------------

def load_json(path, default):

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def known_members():
    """Member names this tracker has data for - also the allow-list
    for subscription requests, so it never drifts from what the
    frontend's politician picker shows (both read data/trades.json).
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


def build_issue_url(title, body, labels):

    params = urlencode({"title": title, "body": body, "labels": labels})

    return f"{REPO_URL}/issues/new?{params}"


def write_output(key, value):
    """Write a (possibly multiline) value to GITHUB_OUTPUT safely."""

    output_file = os.environ.get("GITHUB_OUTPUT")

    if not output_file:
        return

    delimiter = "EOF_OUTPUT"

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"{key}<<{delimiter}\n{value}\n{delimiter}\n")


def finish(status, message, changed):
    """status 'done' closes the issue, 'error' leaves it open so the
    submitter can see what went wrong. 'changed' controls whether the
    workflow commits alerts.json / pending_subscriptions.json.
    """

    print(message)
    write_output("status", status)
    write_output("message", message)
    write_output("changed", "true" if changed else "false")


# --- step 1: "Subscribe request: <email>" ---------------------------

def validate_subscribe_payload(payload, valid_members):

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


def handle_subscribe(body):

    payload = extract_payload(body)
    result, error = validate_subscribe_payload(payload, known_members())

    if error:
        finish("error", f"Sorry, I couldn't process this: {error}", False)
        return

    smtp_config = load_smtp_config()

    if smtp_config is None:
        finish(
            "error",
            "This site's owner hasn't configured email sending yet "
            "(missing SMTP secrets), so I can't send a confirmation "
            "email. Please try again later.",
            False,
        )
        return

    token = secrets.token_urlsafe(24)

    # Replace any earlier pending request for the same email+member
    # set, so re-submitting doesn't pile up dead tokens.
    pending = [
        p for p in load_json(PENDING_FILE, [])
        if p.get("email", "").strip().lower() != result["email"].lower()
        or set(p.get("members", [])) != set(result["members"])
    ]

    pending.append({
        "token": token,
        "email": result["email"],
        "members": result["members"],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    })

    confirm_title = f"{CONFIRM_PREFIX} {token}"
    confirm_link = build_issue_url(
        confirm_title,
        "Confirming my Congress Stock Tracker alert subscription.",
        "confirm-subscription",
    )

    email_body = (
        "Someone (hopefully you) asked to subscribe this address to "
        "trade alerts for:\n\n"
        + "\n".join(f"- {m}" for m in result["members"])
        + "\n\nTo confirm, open this link and submit the pre-filled "
        f"GitHub issue (requires a free GitHub account):\n{confirm_link}"
        f"\n\nThis link expires in {TOKEN_EXPIRY_HOURS} hours. If you "
        "didn't request this, just ignore this email - nothing is "
        "activated until the link above is submitted."
    )

    try:
        send_email(
            smtp_config,
            result["email"],
            "Confirm your Congress Stock Tracker alert subscription",
            email_body,
        )
    except Exception as exc:
        finish("error", f"Couldn't send the confirmation email: {exc}", False)
        return

    save_json(PENDING_FILE, pending)

    finish(
        "done",
        f"Check {result['email']} for a confirmation email and click "
        f"the link inside to finish subscribing. It expires in "
        f"{TOKEN_EXPIRY_HOURS} hours.",
        True,
    )


# --- step 2: "Confirm subscription: <token>" -------------------------

def handle_confirm(title):

    token = title[len(CONFIRM_PREFIX):].strip()

    pending = load_json(PENDING_FILE, [])

    match = None
    remaining = []

    for p in pending:
        if match is None and p.get("token") == token:
            match = p
        else:
            remaining.append(p)

    if match is None:
        finish(
            "error",
            "This confirmation link is invalid or has already been "
            "used. Please subscribe again from the Email Alerts tab.",
            False,
        )
        return

    requested_at = datetime.fromisoformat(match["requested_at"])

    if datetime.now(timezone.utc) - requested_at > timedelta(hours=TOKEN_EXPIRY_HOURS):
        save_json(PENDING_FILE, remaining)
        finish(
            "error",
            "This confirmation link has expired. Please subscribe "
            "again from the Email Alerts tab.",
            True,
        )
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

    for member in match["members"]:

        key = (member.strip().lower(), match["email"].strip().lower())

        if key in existing:
            continue

        alerts.append({"member": member, "email": match["email"]})
        existing.add(key)
        added.append(member)

    save_json(ALERTS_FILE, alerts)
    save_json(PENDING_FILE, remaining)

    if added:
        message = (
            f"Confirmed! {match['email']} is now subscribed to trade "
            f"alerts for: {', '.join(added)}."
        )
    else:
        message = (
            f"{match['email']} was already subscribed to all of these "
            f"- nothing new to do."
        )

    finish("done", message, True)


# --- "Unsubscribe request: <email>" ----------------------------------

def handle_unsubscribe(body):

    payload = extract_payload(body)

    if not isinstance(payload, dict):
        finish(
            "error",
            "Couldn't find a valid unsubscribe block in this issue. "
            "Please use the Email Alerts tab on the site.",
            False,
        )
        return

    email = str(payload.get("email", "")).strip()
    members = payload.get("members")
    unsubscribe_all = bool(payload.get("all"))

    if not EMAIL_RE.match(email):
        finish("error", f"'{email}' doesn't look like a valid email address.", False)
        return

    if not unsubscribe_all and not (isinstance(members, list) and members):
        finish(
            "error",
            "Select at least one politician, or choose to unsubscribe "
            "from all.",
            False,
        )
        return

    alerts = load_json(ALERTS_FILE, [])
    email_lower = email.lower()

    if unsubscribe_all:
        kept = [
            a for a in alerts
            if a.get("email", "").strip().lower() != email_lower
        ]
    else:
        target_members = {str(m).strip().lower() for m in members}
        kept = [
            a for a in alerts
            if not (
                a.get("email", "").strip().lower() == email_lower
                and a.get("member", "").strip().lower() in target_members
            )
        ]

    removed_count = len(alerts) - len(kept)

    save_json(ALERTS_FILE, kept)

    # Also drop any not-yet-confirmed pending requests for this email,
    # so an unconfirmed link can't silently re-add what was just removed.
    pending = load_json(PENDING_FILE, [])
    remaining_pending = [
        p for p in pending
        if p.get("email", "").strip().lower() != email_lower
    ]
    pending_removed = len(pending) - len(remaining_pending)

    if pending_removed:
        save_json(PENDING_FILE, remaining_pending)

    if removed_count or pending_removed:
        message = f"Removed {removed_count} active subscription(s) for {email}."
        if pending_removed:
            message += " Also cancelled a pending (unconfirmed) request."
    else:
        message = f"No matching subscriptions found for {email} - nothing to do."

    finish("done", message, bool(removed_count or pending_removed))


# --- dispatch ----------------------------------------------------------

def main():

    title = os.environ.get("ISSUE_TITLE", "")
    body = os.environ.get("ISSUE_BODY", "")

    if title.startswith(SUBSCRIBE_PREFIX):
        handle_subscribe(body)
    elif title.startswith(CONFIRM_PREFIX):
        handle_confirm(title)
    elif title.startswith(UNSUBSCRIBE_PREFIX):
        handle_unsubscribe(body)
    else:
        finish("error", "Unrecognized request type.", False)


if __name__ == "__main__":
    main()
