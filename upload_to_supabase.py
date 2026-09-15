import json
import os
from datetime import datetime, timezone

import requests

TRADES_FILE = "data/trades.json"
NEW_TRADES_FILE = "data/new_trades.json"

# Supabase's free tier auto-pauses a project after ~7 days with no API
# activity. This script's only real job is to make sure that never
# happens - it writes a single heartbeat row every time the daily
# fetch runs, well under a week apart. It does not try to mirror
# data/trades.json into Supabase; that would depend on a table schema
# this script has no way to verify still matches what's actually
# there.


def load_json(path, default):

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_heartbeat():
    """Upsert a single status row into Supabase. Never raises - a
    failure here (missing secrets, schema drift, network issue) must
    not be able to affect the trades fetch/commit it runs alongside.
    """

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        print(
            "SUPABASE_URL / SUPABASE_KEY not set - skipping Supabase "
            "heartbeat."
        )
        return

    trades = load_json(TRADES_FILE, [])
    new_trades = load_json(NEW_TRADES_FILE, [])

    payload = {
        "id": 1,
        "last_run_at": datetime.now(timezone.utc).isoformat(),
        "trades_count": len(trades),
        "new_trades_count": len(new_trades),
    }

    try:
        response = requests.post(
            f"{supabase_url}/rest/v1/sync_status",
            headers={
                "apikey": supabase_key,
                "Authorization": f"Bearer {supabase_key}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates",
            },
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        print(f"Supabase heartbeat updated: {payload}")
    except Exception as exc:
        print(f"Supabase heartbeat failed, continuing anyway: {exc}")


if __name__ == "__main__":
    upload_heartbeat()
