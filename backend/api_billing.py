"""
Billing API — plan status, upgrade, and promo code endpoints.
Stripe integration wired up at checkout time; stubs return 501 until then.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

from .auth import decode_token
from .neon import get_conn

router = APIRouter(prefix="/billing", tags=["Billing"])
bearer = HTTPBearer()


def _current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return int(payload["sub"])


# ── Models ────────────────────────────────────────────────────────────────────

class UpgradeRequest(BaseModel):
    plan: str               # "pro" or "enterprise"
    billing: str            # "monthly" or "annual"
    extra_seats: int = 0
    stripe_payment_method_id: Optional[str] = None  # filled in when Stripe is wired


class PromoRequest(BaseModel):
    code: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_org_id(user_id: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT org_id FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "User not found")
    return row['org_id']


def _get_billing_status(org_id: int) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT plan, trial_ends_at, extra_seats, seat_limit,
               stripe_customer_id, stripe_subscription_id
        FROM orgs WHERE id = %s
    """, (org_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return {}
    now = datetime.now(timezone.utc)
    trial_ends = row['trial_ends_at']
    if trial_ends and hasattr(trial_ends, 'tzinfo') and trial_ends.tzinfo is None:
        trial_ends = trial_ends.replace(tzinfo=timezone.utc)
    trial_days_left = max(0, (trial_ends - now).days) if trial_ends else 0
    plan = row['plan']
    trial_active = (plan == 'trial' and trial_days_left > 0)
    return {
        "plan": plan,
        "trial_active": trial_active,
        "trial_days_left": trial_days_left,
        "trial_ends_at": trial_ends.isoformat() if trial_ends else None,
        "extra_seats": row['extra_seats'] or 0,
        "seat_limit": row['seat_limit'] or 3,
        "stripe_connected": bool(row['stripe_customer_id']),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/status")
def billing_status(user_id: int = Depends(_current_user_id)):
    org_id = _get_org_id(user_id)
    return _get_billing_status(org_id)


@router.post("/upgrade")
def upgrade(body: UpgradeRequest, user_id: int = Depends(_current_user_id)):
    """
    Stub — will call Stripe Checkout / Subscription API here.
    For now: if a stripe_payment_method_id is not provided, return a 501.
    """
    if not body.stripe_payment_method_id:
        raise HTTPException(501, "Stripe not yet integrated — provide stripe_payment_method_id")

    org_id = _get_org_id(user_id)
    if body.plan not in ("pro", "enterprise"):
        raise HTTPException(400, "plan must be 'pro' or 'enterprise'")

    # TODO: create Stripe customer + subscription, store IDs
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        UPDATE orgs SET plan = %s, extra_seats = %s
        WHERE id = %s
    """, (body.plan, body.extra_seats, org_id))
    conn.commit()
    conn.close()
    return {"success": True, "plan": body.plan}


@router.post("/apply-promo")
def apply_promo(body: PromoRequest, user_id: int = Depends(_current_user_id)):
    """Apply a promo code — extends trial or grants Pro access."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, discount_type, discount_value, max_uses, times_used, expires_at, active
        FROM promo_codes WHERE code = UPPER(%s)
    """, (body.code,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(400, "Invalid promo code")
    if not row['active']:
        conn.close()
        raise HTTPException(400, "This promo code is no longer active")
    if row['expires_at'] and row['expires_at'] < datetime.now(timezone.utc):
        conn.close()
        raise HTTPException(400, "This promo code has expired")
    if row['max_uses'] and row['times_used'] >= row['max_uses']:
        conn.close()
        raise HTTPException(400, "This promo code has reached its usage limit")

    org_id = _get_org_id(user_id)

    if row['discount_type'] == 'trial_days':
        # Extend trial by N days from today or current trial end, whichever is later
        cur.execute("""
            UPDATE orgs SET
                trial_ends_at = GREATEST(trial_ends_at, NOW()) + (%s || ' days')::INTERVAL
            WHERE id = %s
        """, (row['discount_value'], org_id))
    elif row['discount_type'] == 'free_pro':
        # Grant Pro access for N days
        cur.execute("""
            UPDATE orgs SET plan = 'pro',
                trial_ends_at = NOW() + (%s || ' days')::INTERVAL
            WHERE id = %s
        """, (row['discount_value'], org_id))

    cur.execute("UPDATE promo_codes SET times_used = times_used + 1 WHERE id = %s", (row['id'],))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Promo code applied successfully"}


@router.post("/contact-enterprise")
def contact_enterprise(user_id: int = Depends(_current_user_id)):
    """Stub — will send an email to sales team."""
    # TODO: send email to sales@truesignalapp.com via Resend
    return {"success": True, "message": "Thanks! Our team will reach out within 1 business day."}
