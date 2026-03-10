"""
Delete all assets (and their work orders) from MaintainX.
Run from repo root: python -m backend.delete_mx_assets
"""
import json, time, sqlite3, urllib.request, urllib.error
from pathlib import Path
from .encryption import decrypt

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
BASE_URL = "https://api.getmaintainx.com/v1"

def get_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1").fetchone()
    conn.close()
    return decrypt(row[0], row[1], row[2])

def req(method, path, api_key, payload=None):
    url = f"{BASE_URL}/{path}"
    data = json.dumps(payload).encode() if payload else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if data: headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        time.sleep(0.5)
        with urllib.request.urlopen(r) as resp:
            body = resp.read()
            return json.loads(body) if body.strip() else {"ok": True}
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()[:80]}

def fetch_all(resource_key, path, api_key):
    results, cursor = [], None
    while True:
        params = f"limit=100&cursor={cursor}" if cursor else "limit=100"
        data = req("GET", f"{path}?{params}", api_key)
        if not data or "error" in data: break
        results.extend(data.get(resource_key, []))
        cursor = data.get("nextCursor")
        if not cursor: break
    return results

def run():
    api_key = get_key()

    print("Fetching all assets...")
    assets = fetch_all("assets", "assets", api_key)
    print(f"Found {len(assets)} assets to delete.")

    deleted = failed = 0
    for a in assets:
        result = req("DELETE", f"assets/{a['id']}", api_key)
        if result and "error" not in result:
            deleted += 1
        else:
            # Some APIs return empty body on success
            if isinstance(result, dict) and result.get("error") == 404:
                deleted += 1  # already gone
            else:
                print(f"  Could not delete {a['id']} ({a.get('name')}): {result}")
                failed += 1
        if deleted % 10 == 0 and deleted > 0:
            print(f"  {deleted} deleted...")

    print(f"\nDone. Deleted: {deleted}, Failed: {failed}")

if __name__ == "__main__":
    run()
