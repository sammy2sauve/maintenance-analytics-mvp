"""
One-time probe script — fetches sample assets and work orders from MaintainX
and prints the raw response structure so we can build the adapter.

Run from repo root:
    python -m backend.probe_maintainx
"""

import json
import sqlite3
from pathlib import Path
import urllib.request
import urllib.error

from .encryption import decrypt

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
BASE_URL = "https://api.getmaintainx.com/v1"


def get_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT id, email, api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("No API key stored yet. Connect MaintainX in Settings first.")
    user_id, email, enc, salt, nonce = row
    key = decrypt(enc, salt, nonce)
    print(f"Using key for user: {email} (id={user_id})\n")
    return key


def fetch(path, api_key, params="limit=3"):
    url = f"{BASE_URL}/{path}?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}


def post(path, api_key, payload):
    url = f"{BASE_URL}/{path}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}


def probe():
    api_key = get_key()

    # Check for manufacturers/models endpoints
    print("=" * 60)
    print("GET /manufacturers")
    print("=" * 60)
    print(json.dumps(fetch("manufacturers", api_key, "limit=5"), indent=2))

    print("\n" + "=" * 60)
    print("GET /models")
    print("=" * 60)
    print(json.dumps(fetch("models", api_key, "limit=5"), indent=2))

    print("\n" + "=" * 60)
    print("TEST ASSET — manufacturer/model as objects")
    print("=" * 60)
    result = post("assets", api_key, {
        "name": "PROBE-OBJ-FIELDS",
        "serialNumber": "SN-PROBE-002",
        "manufacturer": {"name": "Trane"},
        "model": {"name": "CVHE500"},
    })
    print("POST response:", json.dumps(result, indent=2))

    if result and "id" in result:
        print("\nFULL RECORD:")
        print(json.dumps(fetch(f"assets/{result['id']}", api_key, ""), indent=2))


if __name__ == "__main__":
    probe()
