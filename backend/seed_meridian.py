"""
Seed MaintainX with Meridian Medical Center — Central Utility Plant.

Real equipment with real manufacturers and models. Generates 12 months
of realistic maintenance history (corrective + preventive work orders).

Run from repo root:
    python -m backend.seed_meridian

Takes ~12-15 minutes due to MaintainX rate limiting.
After completion run:
    python -m backend.adapter_maintainx
    PYTHONUTF8=1 python -m backend.pipeline
"""

import json
import random
import sqlite3
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .encryption import decrypt

DB_PATH = Path(__file__).parent.parent / "data" / "db" / "truesignal.db"
BASE_URL = "https://api.getmaintainx.com/v1"
random.seed(99)

# ── Asset definitions ──────────────────────────────────────────────────────────
# (serial_id, display_name, manufacturer, model, description)
ASSETS = [
    # Chillers
    ("MMC-CHIL-001", "Centrifugal Chiller #1",       "Trane",           "CVHE500",         "1,750-ton centrifugal chiller — primary cooling loop"),
    ("MMC-CHIL-002", "Centrifugal Chiller #2",       "Trane",           "CVHE500",         "1,750-ton centrifugal chiller — secondary cooling loop"),
    # Cooling Towers
    ("MMC-CTW-001",  "Cooling Tower #1",             "Baltimore Aircoil","FXV-375",         "Induced draft counterflow cooling tower — Chiller #1"),
    ("MMC-CTW-002",  "Cooling Tower #2",             "Baltimore Aircoil","FXV-375",         "Induced draft counterflow cooling tower — Chiller #2"),
    # Chilled Water Pumps
    ("MMC-CHWP-001", "Chilled Water Pump #1",        "Grundfos",        "TP 100-360/4",    "Primary chilled water circulation — 100 HP"),
    ("MMC-CHWP-002", "Chilled Water Pump #2",        "Grundfos",        "TP 100-360/4",    "Secondary chilled water circulation — 100 HP"),
    ("MMC-CHWP-003", "Chilled Water Pump #3",        "Grundfos",        "TP 100-360/4",    "Standby chilled water pump — 100 HP"),
    # Boilers
    ("MMC-BOIL-001", "Hot Water Boiler #1",          "Cleaver-Brooks",  "ClearFire-H 2000","2,000 MBH condensing hot water boiler — heating loop A"),
    ("MMC-BOIL-002", "Hot Water Boiler #2",          "Cleaver-Brooks",  "ClearFire-H 2000","2,000 MBH condensing hot water boiler — heating loop B"),
    # Hot Water Pumps
    ("MMC-HWP-001",  "Hot Water Pump #1",            "Armstrong",       "4300 Series",     "Heating hot water distribution — 40 HP"),
    ("MMC-HWP-002",  "Hot Water Pump #2",            "Armstrong",       "4300 Series",     "Heating hot water distribution — 40 HP standby"),
    # Air Handling Units
    ("MMC-AHU-001",  "Air Handling Unit #1",         "Carrier",         "39MN",            "OR suite supply air — 40,000 CFM"),
    ("MMC-AHU-002",  "Air Handling Unit #2",         "Carrier",         "39MN",            "ICU supply air — 35,000 CFM"),
    ("MMC-AHU-003",  "Air Handling Unit #3",         "Carrier",         "39MN",            "Patient wing supply air — 30,000 CFM"),
    ("MMC-AHU-004",  "Air Handling Unit #4",         "Trane",           "Climate Changer", "Administration wing — 20,000 CFM"),
    # Medical Air Compressors
    ("MMC-COMP-001", "Medical Air Compressor #1",    "Ingersoll Rand",  "R-Series 22kW",   "Medical grade compressed air — Zone A"),
    ("MMC-COMP-002", "Medical Air Compressor #2",    "Ingersoll Rand",  "R-Series 22kW",   "Medical grade compressed air — Zone B (standby)"),
    # VFDs
    ("MMC-VFD-001",  "Chiller #1 VFD",              "ABB",             "ACS880-01",       "Variable frequency drive — Chiller #1 compressor"),
    ("MMC-VFD-002",  "Chiller #2 VFD",              "ABB",             "ACS880-01",       "Variable frequency drive — Chiller #2 compressor"),
    ("MMC-VFD-003",  "Chilled Water Pump VFD #1",   "ABB",             "ACS880-01",       "Variable frequency drive — CHWP-001"),
    ("MMC-VFD-004",  "Chilled Water Pump VFD #2",   "Danfoss",         "FC302",           "Variable frequency drive — CHWP-002"),
    ("MMC-VFD-005",  "AHU Fan VFD #1",              "Danfoss",         "FC302",           "Variable frequency drive — AHU-001 supply fan"),
    ("MMC-VFD-006",  "AHU Fan VFD #2",              "Danfoss",         "FC302",           "Variable frequency drive — AHU-002 supply fan"),
    # Heat Exchangers
    ("MMC-HEX-001",  "Heat Exchanger #1",           "Alfa Laval",      "M10-BFG",         "Campus district steam-to-hot-water heat exchanger — Loop A"),
    ("MMC-HEX-002",  "Heat Exchanger #2",           "Alfa Laval",      "M10-BFG",         "Campus district steam-to-hot-water heat exchanger — Loop B"),
    # Exhaust Fans
    ("MMC-EXH-001",  "OR Exhaust Fan #1",           "Greenheck",       "BSQ-150",         "Operating room exhaust — negative pressure"),
    ("MMC-EXH-002",  "OR Exhaust Fan #2",           "Greenheck",       "BSQ-150",         "Operating room exhaust — backup"),
    ("MMC-EXH-003",  "Mechanical Room Exhaust Fan", "Greenheck",       "BSQ-150",         "Central plant mechanical room exhaust"),
    ("MMC-EXH-004",  "Boiler Flue Exhaust Fan",     "Greenheck",       "BSQ-150",         "Boiler room induced draft exhaust"),
]

# ── Work order templates ───────────────────────────────────────────────────────
# (title, type, priority, applies_to_prefixes)
CORRECTIVE = [
    # Chillers
    ("High head pressure alarm — chiller trip and restart",         "REACTIVE", "HIGH",   ["CHIL"]),
    ("Refrigerant leak detected — low suction pressure",            "REACTIVE", "HIGH",   ["CHIL"]),
    ("Chiller compressor surge — investigate and tune",             "REACTIVE", "MEDIUM", ["CHIL"]),
    ("Oil pressure differential alarm — oil filter replacement",    "REACTIVE", "MEDIUM", ["CHIL"]),
    ("Condenser water temperature high — chiller derated",          "REACTIVE", "MEDIUM", ["CHIL"]),
    # Cooling towers
    ("Cooling tower fan motor failure — bearing seized",            "REACTIVE", "HIGH",   ["CTW"]),
    ("Fill fouling — reduced heat rejection, clean required",       "REACTIVE", "MEDIUM", ["CTW"]),
    ("Drift eliminator damage — replace section",                   "REACTIVE", "LOW",    ["CTW"]),
    ("Basin heater failure — freeze risk in cold weather",          "REACTIVE", "HIGH",   ["CTW"]),
    # Pumps
    ("Pump mechanical seal leak — replacement required",            "REACTIVE", "HIGH",   ["CHWP", "HWP"]),
    ("Pump bearing noise — inspect and replace",                    "REACTIVE", "MEDIUM", ["CHWP", "HWP"]),
    ("Pump cavitation — low suction pressure investigation",        "REACTIVE", "MEDIUM", ["CHWP", "HWP"]),
    ("Pump coupling misalignment — vibration alarm",                "REACTIVE", "MEDIUM", ["CHWP", "HWP"]),
    # Boilers
    ("Boiler low water cutout — LWCO reset and inspection",         "REACTIVE", "HIGH",   ["BOIL"]),
    ("Ignition failure — burner lockout, inspect electrodes",       "REACTIVE", "HIGH",   ["BOIL"]),
    ("Boiler pressure relief valve weeping — replace PRV",          "REACTIVE", "MEDIUM", ["BOIL"]),
    ("Condensate trap failure — steam loss",                        "REACTIVE", "LOW",    ["BOIL"]),
    # AHUs
    ("Supply fan belt snapped — emergency replacement",             "REACTIVE", "HIGH",   ["AHU"]),
    ("Cooling coil fouled — restricted airflow and low delta-T",    "REACTIVE", "MEDIUM", ["AHU"]),
    ("Damper actuator failure — stuck in position",                 "REACTIVE", "MEDIUM", ["AHU"]),
    ("AHU filter differential pressure high — emergency swap",      "REACTIVE", "LOW",    ["AHU"]),
    ("Heating coil leak — dripping into unit",                      "REACTIVE", "HIGH",   ["AHU"]),
    # Compressors
    ("Medical air compressor high temperature shutdown",            "REACTIVE", "HIGH",   ["COMP"]),
    ("Compressor oil separator fouled — high oil carryover",        "REACTIVE", "MEDIUM", ["COMP"]),
    ("Inlet air filter clogged — low pressure alarm",               "REACTIVE", "MEDIUM", ["COMP"]),
    ("Compressor intake valve failure — low output pressure",       "REACTIVE", "HIGH",   ["COMP"]),
    # VFDs
    ("VFD overtemperature fault — cooling fan failure",             "REACTIVE", "HIGH",   ["VFD"]),
    ("VFD ground fault — investigate wiring",                       "REACTIVE", "HIGH",   ["VFD"]),
    ("VFD DC bus overvoltage — inspect and reset",                  "REACTIVE", "MEDIUM", ["VFD"]),
    # Heat exchangers
    ("HEX fouling — low delta-T, acid clean required",              "REACTIVE", "MEDIUM", ["HEX"]),
    ("HEX plate gasket failure — minor cross-contamination",        "REACTIVE", "HIGH",   ["HEX"]),
    # Exhaust fans
    ("Exhaust fan belt wear — replacement before failure",          "REACTIVE", "MEDIUM", ["EXH"]),
    ("Exhaust fan bearing noise — vibration above threshold",       "REACTIVE", "MEDIUM", ["EXH"]),
    ("Exhaust fan motor tripped — reset and inspect",               "REACTIVE", "HIGH",   ["EXH"]),
]

PREVENTIVE = [
    ("Monthly PM — filter inspection and replacement",              "PREVENTIVE", "LOW",    None),
    ("Monthly PM — lubrication and belt tension check",             "PREVENTIVE", "LOW",    None),
    ("Monthly PM — operational check and log readings",             "PREVENTIVE", "LOW",    None),
    ("Quarterly PM — vibration analysis and alignment check",       "PREVENTIVE", "LOW",    None),
    ("Quarterly PM — electrical connections and controls check",    "PREVENTIVE", "LOW",    None),
    ("Semi-annual PM — coil cleaning and inspection",               "PREVENTIVE", "MEDIUM", ["CHIL", "AHU", "CTW"]),
    ("Semi-annual PM — refrigerant charge verification",            "PREVENTIVE", "MEDIUM", ["CHIL"]),
    ("Semi-annual PM — cooling tower water treatment and basin clean","PREVENTIVE","LOW",   ["CTW"]),
    ("Annual PM — full overhaul and performance test",              "PREVENTIVE", "MEDIUM", None),
    ("Annual PM — boiler combustion analysis and tune",             "PREVENTIVE", "MEDIUM", ["BOIL"]),
    ("Annual PM — chiller performance curve verification",          "PREVENTIVE", "MEDIUM", ["CHIL"]),
    ("Annual PM — VFD parameter backup and inspection",             "PREVENTIVE", "LOW",    ["VFD"]),
    ("Weekly boiler blowdown — mud drum and surface",               "PREVENTIVE", "LOW",    ["BOIL"]),
    ("Monthly medical air quality test — dew point and purity",     "PREVENTIVE", "MEDIUM", ["COMP"]),
    ("Quarterly HEX inspection — plate condition and gaskets",      "PREVENTIVE", "LOW",    ["HEX"]),
]

TECHNICIANS = ["M. Rodriguez", "T. Kim", "L. Jackson", "P. Okonkwo", "S. Brennan"]


# ── API helpers ────────────────────────────────────────────────────────────────

def get_key():
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT api_key_enc, api_key_salt, api_key_nonce FROM users WHERE api_key_enc IS NOT NULL LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        raise SystemExit("No API key stored.")
    return decrypt(row[0], row[1], row[2])


def _request(method, path, api_key, payload=None, retries=4):
    url = f"{BASE_URL}/{path}"
    data = json.dumps(payload).encode() if payload else None
    headers = {"Authorization": f"Bearer {api_key}"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(retries):
        try:
            time.sleep(0.5)
            with urllib.request.urlopen(req) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if e.code == 429:
                wait = 15 * (attempt + 1)
                print(f"    Rate limited — waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"    ERROR {e.code}: {body[:100]}")
                return None
    return None


def rdt(days_min, days_max):
    """Random past datetime string."""
    days = random.randint(days_min, days_max)
    dt = datetime.now(timezone.utc) - timedelta(days=days, hours=random.randint(0, 8))
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def prefix(serial_id):
    return serial_id.split("-")[1]  # MMC-CHIL-001 -> CHIL


# ── Seed ──────────────────────────────────────────────────────────────────────

def seed():
    api_key = get_key()
    print(f"Seeding Meridian Medical Center — {len(ASSETS)} assets\n")

    # Step 1: Create assets
    asset_map = {}  # serial_id -> MX id
    print(f"Creating {len(ASSETS)} assets...")
    for serial_id, name, manufacturer, model, description in ASSETS:
        result = _request("POST", "assets", api_key, {
            "name": name,
            "description": f"{manufacturer} {model} | {description}",
            "serialNumber": serial_id,
        })
        if result and "id" in result:
            asset_map[serial_id] = result["id"]
            print(f"  + {name} ({manufacturer} {model})")
        else:
            print(f"  FAILED: {name}")

    print(f"\n{len(asset_map)}/{len(ASSETS)} assets created.")

    # Step 2: Create work orders — 12 months of history
    print(f"\nCreating work orders (12 months of history)...")
    wo_count = 0

    for serial_id, name, manufacturer, model, _ in ASSETS:
        mx_id = asset_map.get(serial_id)
        if not mx_id:
            continue
        pfx = prefix(serial_id)
        tech = random.choice(TECHNICIANS)

        # Corrective WOs applicable to this asset
        applicable_corrective = [
            t for t in CORRECTIVE
            if t[3] is None or any(pfx == p for p in t[3])
        ]
        # High-criticality assets get more corrective WOs
        high_crit = pfx in ("CHIL", "COMP", "BOIL", "AHU")
        n_corrective = random.randint(3, 6) if high_crit else random.randint(1, 3)

        for _ in range(n_corrective):
            tmpl = random.choice(applicable_corrective)
            title, wo_type, priority, _ = tmpl
            due = rdt(7, 365)
            result = _request("POST", "workorders", api_key, {
                "title": f"{title} — {name}",
                "type": wo_type,
                "priority": priority,
                "assetId": mx_id,
                "dueDate": due,
                "description": f"Asset: {serial_id} | {manufacturer} {model} | Tech: {tech}",
            })
            if result and "id" in result:
                wo_count += 1

        # Preventive WOs
        applicable_prev = [
            t for t in PREVENTIVE
            if t[3] is None or any(pfx == p for p in t[3])
        ]
        n_prev = random.randint(5, 9)
        for _ in range(n_prev):
            tmpl = random.choice(applicable_prev)
            title, wo_type, priority, _ = tmpl
            due = rdt(0, 365)
            result = _request("POST", "workorders", api_key, {
                "title": f"{title} — {name}",
                "type": wo_type,
                "priority": priority,
                "assetId": mx_id,
                "dueDate": due,
                "description": f"Asset: {serial_id} | {manufacturer} {model} | Tech: {tech}",
            })
            if result and "id" in result:
                wo_count += 1

        print(f"  {name}: done")

    print(f"\nSeed complete — {len(asset_map)} assets, {wo_count} work orders.")
    print("\nNext steps:")
    print("  1. python -m backend.adapter_maintainx")
    print("  2. PYTHONUTF8=1 python -m backend.pipeline")


if __name__ == "__main__":
    seed()
