"""
Alert rules API — /alerts/rules

Saves per-user alert thresholds and fires email alerts after each sync.

Conditions supported:
  any_critical          — any asset reaches CRITICAL risk level
  critical_count        — CRITICAL asset count >= threshold
  high_count            — HIGH asset count >= threshold
  risk_score            — any asset failure_probability >= threshold
  savings_opportunity   — total estimated savings >= threshold
  no_wo_days            — any asset has no WO in last N days
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import decode_token, get_user_locations, user_can_access_location
from .neon import get_conn
from .email_service import send_alert_email

router = APIRouter(prefix="/alerts", tags=["Alerts"])
bearer = HTTPBearer()


def _current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return int(payload["sub"])


def _resolve_location(user_id: int, location_id: int = None) -> int:
    locs = get_user_locations(user_id)
    if not locs:
        raise HTTPException(400, "No locations found for this user")
    if location_id is None:
        return locs[0]["id"]
    if not user_can_access_location(user_id, location_id):
        raise HTTPException(403, "Access denied")
    return location_id


# ── Models ────────────────────────────────────────────────────────────────────

class AlertRuleIn(BaseModel):
    rule_key:  str
    threshold: Optional[float] = None
    channel:   str = "Email"
    frequency: str = "Immediately"
    enabled:   bool = True


class AlertRuleBatch(BaseModel):
    rules:       List[AlertRuleIn]
    location_id: Optional[int] = None


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.get("/rules")
def get_rules(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    loc_id = _resolve_location(user_id, location_id)
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT rule_key, threshold, channel, frequency, enabled, last_fired_at
        FROM alert_rules
        WHERE user_id = %s AND location_id = %s
        ORDER BY id
        """,
        (user_id, loc_id),
    )
    rows = cur.fetchall()
    conn.close()
    return {
        "location_id": loc_id,
        "rules": [dict(r) for r in rows],
    }


@router.post("/rules")
def save_rules(body: AlertRuleBatch, user_id: int = Depends(_current_user_id)):
    loc_id = _resolve_location(user_id, body.location_id)
    conn = get_conn()
    cur = conn.cursor()
    for rule in body.rules:
        cur.execute(
            """
            INSERT INTO alert_rules (user_id, location_id, rule_key, threshold, channel, frequency, enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, location_id, rule_key) DO UPDATE SET
                threshold = EXCLUDED.threshold,
                channel   = EXCLUDED.channel,
                frequency = EXCLUDED.frequency,
                enabled   = EXCLUDED.enabled
            """,
            (user_id, loc_id, rule.rule_key, rule.threshold,
             rule.channel, rule.frequency, rule.enabled),
        )
    conn.commit()
    conn.close()
    return {"saved": len(body.rules), "location_id": loc_id}


# ── Alert evaluation engine ───────────────────────────────────────────────────

def _within_cooldown(last_fired_at, frequency: str) -> bool:
    """Return True if the rule is still within its cooldown window."""
    if last_fired_at is None:
        return False
    if isinstance(last_fired_at, str):
        last_fired_at = datetime.fromisoformat(last_fired_at)
    now = datetime.now(timezone.utc)
    if last_fired_at.tzinfo is None:
        last_fired_at = last_fired_at.replace(tzinfo=timezone.utc)
    if frequency == "Daily digest":
        return (now - last_fired_at) < timedelta(hours=24)
    if frequency == "Weekly digest":
        return (now - last_fired_at) < timedelta(days=7)
    return False  # "Immediately" → never in cooldown


def _evaluate_condition(rule_key: str, threshold, cur) -> tuple[bool, str, str, str]:
    """
    Evaluate a single condition against current DB state.
    Returns (triggered, title, description, severity).
    """
    if rule_key == "any_critical":
        cur.execute(
            """
            SELECT asset_id FROM asset_failure_predictions
            WHERE risk_level = 'CRITICAL'
              AND (prediction_date, asset_id) IN (
                  SELECT MAX(prediction_date), asset_id
                  FROM asset_failure_predictions GROUP BY asset_id
              )
            LIMIT 5
            """
        )
        rows = cur.fetchall()
        if rows:
            ids = ", ".join(r["asset_id"] for r in rows)
            return (True,
                    "CRITICAL asset detected",
                    f"Asset(s) at CRITICAL risk: {ids}",
                    "critical")
        return (False, "", "", "")

    if rule_key == "critical_count":
        cur.execute(
            """
            SELECT COUNT(*) AS cnt FROM asset_failure_predictions
            WHERE risk_level = 'CRITICAL'
              AND (prediction_date, asset_id) IN (
                  SELECT MAX(prediction_date), asset_id
                  FROM asset_failure_predictions GROUP BY asset_id
              )
            """
        )
        cnt = cur.fetchone()["cnt"]
        thr = int(threshold or 1)
        if cnt >= thr:
            return (True,
                    f"{cnt} CRITICAL assets",
                    f"{cnt} assets are at CRITICAL risk (threshold: {thr})",
                    "critical")
        return (False, "", "", "")

    if rule_key == "high_count":
        cur.execute(
            """
            SELECT COUNT(*) AS cnt FROM asset_failure_predictions
            WHERE risk_level IN ('CRITICAL','HIGH')
              AND (prediction_date, asset_id) IN (
                  SELECT MAX(prediction_date), asset_id
                  FROM asset_failure_predictions GROUP BY asset_id
              )
            """
        )
        cnt = cur.fetchone()["cnt"]
        thr = int(threshold or 5)
        if cnt >= thr:
            return (True,
                    f"{cnt} high-risk assets",
                    f"{cnt} assets are HIGH or CRITICAL risk (threshold: {thr})",
                    "high")
        return (False, "", "", "")

    if rule_key == "risk_score":
        thr = float(threshold or 0.7)
        cur.execute(
            """
            SELECT asset_id, failure_probability FROM asset_failure_predictions
            WHERE failure_probability >= %s
              AND (prediction_date, asset_id) IN (
                  SELECT MAX(prediction_date), asset_id
                  FROM asset_failure_predictions GROUP BY asset_id
              )
            ORDER BY failure_probability DESC LIMIT 3
            """,
            (thr,),
        )
        rows = cur.fetchall()
        if rows:
            top = rows[0]
            return (True,
                    f"High risk score: {top['asset_id']}",
                    f"{top['asset_id']} risk score {top['failure_probability']:.0%} exceeds threshold {thr:.0%}",
                    "high")
        return (False, "", "", "")

    if rule_key == "savings_opportunity":
        thr = float(threshold or 10000)
        cur.execute(
            "SELECT COALESCE(SUM(estimated_cost_savings), 0) AS total FROM pm_optimization_suggestions WHERE status = 'pending'"
        )
        total = cur.fetchone()["total"]
        if total >= thr:
            return (True,
                    f"${total:,.0f} savings opportunity",
                    f"Total PM optimization savings opportunity ${total:,.0f} exceeds threshold ${thr:,.0f}",
                    "medium")
        return (False, "", "", "")

    if rule_key == "no_wo_days":
        thr = int(threshold or 90)
        cur.execute(
            """
            SELECT DISTINCT asset_id FROM asset_failure_predictions
            WHERE (prediction_date, asset_id) IN (
                SELECT MAX(prediction_date), asset_id
                FROM asset_failure_predictions GROUP BY asset_id
            )
            AND asset_id NOT IN (
                SELECT DISTINCT asset_id FROM work_orders
                WHERE creation_date >= CURRENT_DATE - INTERVAL '%s days'
            )
            LIMIT 5
            """ % thr
        )
        rows = cur.fetchall()
        if rows:
            ids = ", ".join(r["asset_id"] for r in rows)
            return (True,
                    f"Assets with no WO in {thr}+ days",
                    f"Assets with no work order in {thr} days: {ids}",
                    "medium")
        return (False, "", "", "")

    return (False, "", "", "")


def check_and_fire_alerts(location_id: int) -> int:
    """
    Evaluate all enabled alert rules for every user at this location.
    Sends email for each triggered rule (respecting cooldowns).
    Returns total emails sent.
    """
    conn = get_conn()
    cur = conn.cursor()

    # Load all enabled rules for this location
    cur.execute(
        """
        SELECT ar.id, ar.user_id, ar.rule_key, ar.threshold, ar.channel,
               ar.frequency, ar.last_fired_at,
               u.email, u.name
        FROM alert_rules ar
        JOIN users u ON u.id = ar.user_id
        WHERE ar.location_id = %s AND ar.enabled = TRUE
        """,
        (location_id,),
    )
    rules = cur.fetchall()

    if not rules:
        conn.close()
        return 0

    # Group triggered alerts per user so we send one digest email per user
    user_alerts: dict[int, dict] = {}  # user_id -> {email, name, alerts:[]}

    for rule in rules:
        if _within_cooldown(rule["last_fired_at"], rule["frequency"]):
            continue

        triggered, title, description, severity = _evaluate_condition(
            rule["rule_key"], rule["threshold"], cur
        )

        if not triggered:
            continue

        uid = rule["user_id"]
        if uid not in user_alerts:
            user_alerts[uid] = {
                "email": rule["email"],
                "name":  rule["name"],
                "rule_ids": [],
                "alerts": [],
            }
        user_alerts[uid]["alerts"].append({
            "title":       title,
            "description": description,
            "severity":    severity,
        })
        user_alerts[uid]["rule_ids"].append(rule["id"])

    emails_sent = 0
    now_ts = datetime.now(timezone.utc)

    for uid, data in user_alerts.items():
        if not data["alerts"]:
            continue
        sent = send_alert_email(data["email"], data["name"], data["alerts"])
        if sent:
            emails_sent += 1
            # Update last_fired_at for all rules that triggered for this user
            for rule_id in data["rule_ids"]:
                cur.execute(
                    "UPDATE alert_rules SET last_fired_at = %s WHERE id = %s",
                    (now_ts, rule_id),
                )

    conn.commit()
    conn.close()
    print(f"[alerts] Checked {len(rules)} rules → {emails_sent} emails sent")
    return emails_sent


# ── Manual check endpoint (admin / testing) ───────────────────────────────────

@router.post("/check")
def manual_check(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    """Manually trigger alert evaluation for a location. Useful for testing."""
    loc_id = _resolve_location(user_id, location_id)
    sent = check_and_fire_alerts(loc_id)
    return {"emails_sent": sent, "location_id": loc_id}
