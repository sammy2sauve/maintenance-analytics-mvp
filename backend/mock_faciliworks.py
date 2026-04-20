"""
Mock FaciliWorks Web API server for local testing.

Mimics the FaciliWorks REST API format so the real adapter can be tested
end-to-end without a live FaciliWorks account.

Run:
    uvicorn backend.mock_faciliworks:app --port 8001 --reload

Then in Settings UI:
    Base URL: http://localhost:8001
    API Key:  any-non-empty-string

Endpoints:
    GET /v1/assets   -> paginated assets (FaciliWorks format)
    GET /v1/cm       -> paginated corrective maintenance WOs
    GET /v1/pm       -> paginated preventive maintenance WOs
"""

import json
import random
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Header, HTTPException, Query, Request

app = FastAPI(title="Mock FaciliWorks API", version="9.2.12")
random.seed(42)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _auth(x_api_key: str = Header(None)):
    if not x_api_key:
        raise HTTPException(401, "Missing X-API-KEY header")


def _epoch(days_ago: int, jitter_hours: int = 0) -> int:
    """Return epoch seconds for N days ago with optional hour jitter."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago, hours=jitter_hours)
    return int(dt.timestamp())


def _paginate(items: list, load_options_raw: str) -> dict:
    """Apply skip/take from loadOptions JSON query param."""
    try:
        opts = json.loads(load_options_raw) if load_options_raw else {}
    except Exception:
        opts = {}
    skip = int(opts.get("skip", 0))
    take = int(opts.get("take", 100))
    page = items[skip: skip + take]
    return {"data": page, "totalCount": len(items)}


# ── Asset definitions (Meridian Medical Center) ───────────────────────────────

ASSET_DEFS = [
    # (equipmentID, description, manufacturer, modelNo)
    ("MMC-CHIL-001", "Centrifugal Chiller #1",       "Trane",            "CVHE500"),
    ("MMC-CHIL-002", "Centrifugal Chiller #2",       "Trane",            "CVHE500"),
    ("MMC-CTW-001",  "Cooling Tower #1",             "Baltimore Aircoil","FXV-375"),
    ("MMC-CTW-002",  "Cooling Tower #2",             "Baltimore Aircoil","FXV-375"),
    ("MMC-CHWP-001", "Chilled Water Pump #1",        "Grundfos",         "TP 100-360/4"),
    ("MMC-CHWP-002", "Chilled Water Pump #2",        "Grundfos",         "TP 100-360/4"),
    ("MMC-CHWP-003", "Chilled Water Pump #3",        "Grundfos",         "TP 100-360/4"),
    ("MMC-BOIL-001", "Hot Water Boiler #1",          "Cleaver-Brooks",   "ClearFire-H 2000"),
    ("MMC-BOIL-002", "Hot Water Boiler #2",          "Cleaver-Brooks",   "ClearFire-H 2000"),
    ("MMC-HWP-001",  "Hot Water Pump #1",            "Armstrong",        "4300 Series"),
    ("MMC-HWP-002",  "Hot Water Pump #2",            "Armstrong",        "4300 Series"),
    ("MMC-AHU-001",  "Air Handling Unit #1",         "Carrier",          "39MN"),
    ("MMC-AHU-002",  "Air Handling Unit #2",         "Carrier",          "39MN"),
    ("MMC-AHU-003",  "Air Handling Unit #3",         "Carrier",          "39MN"),
    ("MMC-AHU-004",  "Air Handling Unit #4",         "Trane",            "Climate Changer"),
    ("MMC-COMP-001", "Medical Air Compressor #1",    "Ingersoll Rand",   "R-Series 22kW"),
    ("MMC-COMP-002", "Medical Air Compressor #2",    "Ingersoll Rand",   "R-Series 22kW"),
    ("MMC-VFD-001",  "Chiller #1 VFD",              "ABB",              "ACS880-01"),
    ("MMC-VFD-002",  "Chiller #2 VFD",              "ABB",              "ACS880-01"),
    ("MMC-VFD-003",  "Chilled Water Pump VFD #1",   "ABB",              "ACS880-01"),
    ("MMC-VFD-004",  "Chilled Water Pump VFD #2",   "Danfoss",          "FC302"),
    ("MMC-VFD-005",  "AHU Fan VFD #1",              "Danfoss",          "FC302"),
    ("MMC-VFD-006",  "AHU Fan VFD #2",              "Danfoss",          "FC302"),
    ("MMC-HEX-001",  "Heat Exchanger #1",           "Alfa Laval",       "M10-BFG"),
    ("MMC-HEX-002",  "Heat Exchanger #2",           "Alfa Laval",       "M10-BFG"),
    ("MMC-EXH-001",  "OR Exhaust Fan #1",           "Greenheck",        "BSQ-150"),
    ("MMC-EXH-002",  "OR Exhaust Fan #2",           "Greenheck",        "BSQ-150"),
    ("MMC-EXH-003",  "Mechanical Room Exhaust Fan", "Greenheck",        "BSQ-150"),
    ("MMC-EXH-004",  "Boiler Flue Exhaust Fan",     "Greenheck",        "BSQ-150"),
]

# Build asset list once at startup
ASSETS = [
    {
        "equipmentMasterID": idx + 1,
        "equipmentID":       eid,
        "description":       desc,
        "manufacturer":      {"lookupValue": mfr},
        "modelNo":           model,
        "status":            {"comboBoxText": "Active"},
        "location":          {"locationName": "Meridian Medical Center"},
    }
    for idx, (eid, desc, mfr, model) in enumerate(ASSET_DEFS)
]

# equipmentID -> equipmentMasterID lookup
_ID_MAP = {a["equipmentID"]: a["equipmentMasterID"] for a in ASSETS}


# ── CM work order generation ──────────────────────────────────────────────────

CM_TEMPLATES = [
    # (title, prefix_list, priority, est_hours)
    ("High head pressure alarm — chiller trip",             ["CHIL"],              "High",   3.0),
    ("Refrigerant leak — low suction pressure",             ["CHIL"],              "High",   5.0),
    ("Chiller compressor surge investigation",              ["CHIL"],              "Medium", 2.5),
    ("Oil pressure differential alarm — filter change",     ["CHIL"],              "Medium", 2.0),
    ("Cooling tower fan motor failure — bearing seized",    ["CTW"],               "High",   4.0),
    ("Basin heater failure — freeze risk",                  ["CTW"],               "High",   2.0),
    ("Fill fouling — heat rejection reduced",               ["CTW"],               "Medium", 3.0),
    ("Pump mechanical seal leak",                           ["CHWP", "HWP"],       "High",   3.5),
    ("Pump bearing noise — inspect and replace",            ["CHWP", "HWP"],       "Medium", 2.0),
    ("Pump cavitation — low suction pressure",              ["CHWP", "HWP"],       "Medium", 1.5),
    ("Boiler low water cutout — LWCO reset",                ["BOIL"],              "High",   2.0),
    ("Ignition failure — burner lockout",                   ["BOIL"],              "High",   3.0),
    ("Boiler PRV weeping — replacement",                    ["BOIL"],              "Medium", 1.5),
    ("AHU supply fan belt failure",                         ["AHU"],               "High",   1.5),
    ("AHU coil freeze-stat trip",                           ["AHU"],               "High",   2.0),
    ("AHU filter pressure drop — emergency change",         ["AHU"],               "Low",    1.0),
    ("Compressor high temperature alarm",                   ["COMP"],              "High",   2.5),
    ("VFD fault — overcurrent trip",                        ["VFD"],               "High",   2.0),
    ("VFD cooling fan failure",                             ["VFD"],               "Medium", 1.0),
    ("Heat exchanger plate fouling — cleaning",             ["HEX"],               "Medium", 4.0),
    ("Exhaust fan motor overload trip",                     ["EXH"],               "High",   1.5),
]


def _asset_matches(eid: str, prefixes: list) -> bool:
    return any(f"MMC-{p}-" in eid for p in prefixes)


def _build_cms() -> list:
    records = []
    wo_num = 1001
    for asset in ASSETS:
        eid = asset["equipmentID"]
        mid = asset["equipmentMasterID"]
        applicable = [t for t in CM_TEMPLATES if _asset_matches(eid, t[1])]
        if not applicable:
            applicable = CM_TEMPLATES[-3:]  # fallback for any asset

        # Generate 6–14 CMs spread over last 365 days
        count = random.randint(6, 14)
        for i in range(count):
            tmpl = random.choice(applicable)
            days_ago_due  = random.randint(5, 365)
            days_ago_done = days_ago_due - random.randint(0, 3)
            days_ago_created = days_ago_due + random.randint(1, 5)
            completed = days_ago_done > 0 and random.random() > 0.15

            records.append({
                "maintenanceKey": wo_num,
                "woNumber":       f"CM-{wo_num}",
                "asset": {
                    "equipmentMasterID": mid,
                    "equipmentID":       eid,
                },
                "status":   {"comboBoxText": "Complete" if completed else "Open"},
                "priority": {"comboBoxText": tmpl[2]},
                "createdDate":    _epoch(days_ago_created),
                "dueDate":        _epoch(days_ago_due),
                "doneDate":       _epoch(days_ago_done) if completed else None,
                "startDate":      _epoch(days_ago_due + 1),
                "estimatedHours": tmpl[3],
                "actualHours":    round(tmpl[3] * random.uniform(0.7, 1.3), 1) if completed else None,
                "description":    tmpl[0],
            })
            wo_num += 1

    return records


# ── PM work order generation ──────────────────────────────────────────────────

PM_TEMPLATES = [
    # (taskID, title, prefix_list, interval_days, est_hours)
    ("PM-CHIL-MONTHLY",   "Chiller monthly inspection — oil, refrigerant, controls",   ["CHIL"],        30,  3.0),
    ("PM-CHIL-QUARTERLY", "Chiller quarterly service — tubes, bearings, full check",   ["CHIL"],        90,  6.0),
    ("PM-CTW-MONTHLY",    "Cooling tower monthly — water treatment, fill inspection",  ["CTW"],         30,  2.0),
    ("PM-CTW-SEASONAL",   "Cooling tower seasonal — basin clean, fan/motor service",   ["CTW"],         180, 8.0),
    ("PM-PUMP-MONTHLY",   "Pump monthly check — seals, alignment, vibration",          ["CHWP", "HWP"], 30,  1.5),
    ("PM-PUMP-ANNUAL",    "Pump annual service — impeller, bearings, full overhaul",   ["CHWP", "HWP"], 365, 6.0),
    ("PM-BOIL-MONTHLY",   "Boiler monthly — burner, controls, water quality",          ["BOIL"],        30,  2.5),
    ("PM-BOIL-ANNUAL",    "Boiler annual inspection — heat exchanger, safety valves",  ["BOIL"],        365, 8.0),
    ("PM-AHU-MONTHLY",    "AHU monthly — filter check, belt tension, coil inspection", ["AHU"],         30,  1.5),
    ("PM-AHU-QUARTERLY",  "AHU quarterly — deep clean coils, drain pans, dampers",     ["AHU"],         90,  3.0),
    ("PM-COMP-MONTHLY",   "Compressor monthly — oil, filters, pressure check",         ["COMP"],        30,  2.0),
    ("PM-VFD-QUARTERLY",  "VFD quarterly — cleaning, connections, parameter check",    ["VFD"],         90,  1.0),
    ("PM-HEX-SEMI",       "Heat exchanger semi-annual — plate inspection and clean",   ["HEX"],         180, 5.0),
    ("PM-EXH-MONTHLY",    "Exhaust fan monthly — belt, bearings, damper",              ["EXH"],         30,  1.0),
    ("PM-EXH-ANNUAL",     "Exhaust fan annual — motor relubrication, full service",    ["EXH"],         365, 2.5),
]


def _build_pms() -> list:
    records = []
    wo_num = 5001
    for asset in ASSETS:
        eid = asset["equipmentID"]
        mid = asset["equipmentMasterID"]
        applicable = [t for t in PM_TEMPLATES if _asset_matches(eid, t[2])]
        if not applicable:
            applicable = [PM_TEMPLATES[0]]

        for tmpl in applicable:
            interval = tmpl[3]
            # How many occurrences fit in 365 days?
            count = max(1, 365 // interval)
            for i in range(count):
                days_ago_due = interval * (count - i) - random.randint(0, 5)
                completed = random.random() > 0.12  # ~88% PM compliance

                records.append({
                    "maintenanceKey": wo_num,
                    "woNumber":       f"PM-{wo_num}",
                    "task":           {"taskID": tmpl[0]},
                    "asset": {
                        "equipmentMasterID": mid,
                        "equipmentID":       eid,
                    },
                    "status":   {"comboBoxText": "Complete" if completed else "Open"},
                    "priority": {"comboBoxText": "Low"},
                    "createdDate":    _epoch(days_ago_due + 7),
                    "dueDate":        _epoch(days_ago_due),
                    "doneDate":       _epoch(max(0, days_ago_due - random.randint(0, 3))) if completed else None,
                    "startDate":      _epoch(days_ago_due + 1),
                    "estimatedHours": tmpl[4],
                    "actualHours":    round(tmpl[4] * random.uniform(0.8, 1.2), 1) if completed else None,
                    "description":    tmpl[1],
                })
                wo_num += 1

    return records


# Build once at import time (deterministic because random.seed(42))
_ALL_ASSETS = ASSETS
_ALL_CMS    = _build_cms()
_ALL_PMS    = _build_pms()

print(f"[mock-fw] Ready: {len(_ALL_ASSETS)} assets | {len(_ALL_CMS)} CMs | {len(_ALL_PMS)} PMs")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/v1/assets")
def get_assets(
    loadOptions: str = Query(default="{}"),
    x_api_key: str = Header(None),
):
    _auth(x_api_key)
    return _paginate(_ALL_ASSETS, loadOptions)


@app.get("/v1/cm")
def get_cm(
    loadOptions: str = Query(default="{}"),
    x_api_key: str = Header(None),
):
    _auth(x_api_key)
    return _paginate(_ALL_CMS, loadOptions)


@app.get("/v1/pm")
def get_pm(
    loadOptions: str = Query(default="{}"),
    x_api_key: str = Header(None),
):
    _auth(x_api_key)
    return _paginate(_ALL_PMS, loadOptions)


@app.get("/v1/assets/{equipment_master_id}/history")
def get_asset_history(
    equipment_master_id: int,
    loadOptions: str = Query(default="{}"),
    x_api_key: str = Header(None),
):
    _auth(x_api_key)
    cms = [r for r in _ALL_CMS if r["asset"]["equipmentMasterID"] == equipment_master_id]
    pms = [r for r in _ALL_PMS if r["asset"]["equipmentMasterID"] == equipment_master_id]
    history = [{"type": "CM", **r} for r in cms] + [{"type": "PM", **r} for r in pms]
    history.sort(key=lambda r: r.get("dueDate") or 0, reverse=True)
    return _paginate(history, loadOptions)


@app.post("/v1/cm")
async def create_cm(
    request: Request,
    x_api_key: str = Header(None),
):
    _auth(x_api_key)
    body = await request.json()
    new_key = max((r["maintenanceKey"] for r in _ALL_CMS), default=2000) + 1
    wo = {
        "maintenanceKey": new_key,
        "woNumber": f"CM-{new_key}",
        "status": {"comboBoxText": "Open"},
        **body,
    }
    _ALL_CMS.append(wo)
    return wo


@app.get("/health")
def health():
    return {
        "status": "ok",
        "assets": len(_ALL_ASSETS),
        "cms":    len(_ALL_CMS),
        "pms":    len(_ALL_PMS),
    }
