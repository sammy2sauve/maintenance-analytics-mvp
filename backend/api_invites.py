"""
Invite codes, team management, and seat limits.
Router prefix: /invites
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import (
    decode_token,
    get_user_locations,
    get_user_role_in_org,
    create_invite_code,
    validate_invite_code,
    accept_invite_code,
    get_org_members,
    get_org_seat_usage,
    get_invite_codes,
    revoke_invite_code,
    remove_org_member,
)

router = APIRouter(prefix="/invites", tags=["Invites"])
bearer = HTTPBearer()


def _current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return int(payload["sub"])


def _get_user_org(user_id: int):
    """Return (org_id, location_id, role) for the user's first location."""
    locs = get_user_locations(user_id)
    if not locs:
        raise HTTPException(400, "No org found for this user")
    loc = locs[0]
    role = get_user_role_in_org(user_id, loc["org_id"])
    return loc["org_id"], loc["id"], role


class GenerateCodeRequest(BaseModel):
    role: str = "viewer"
    expires_days: int = 7


@router.post("/generate")
def generate_invite(body: GenerateCodeRequest, user_id: int = Depends(_current_user_id)):
    org_id, location_id, role = _get_user_org(user_id)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can generate invite codes")
    if role == "admin" and body.role != "viewer":
        raise HTTPException(403, "Admins can only generate viewer invite codes")
    if body.role not in ("owner", "admin", "viewer"):
        raise HTTPException(400, f"Invalid role: {body.role}")
    try:
        code = create_invite_code(org_id, location_id, user_id, body.role, body.expires_days)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return {"code": code, "role": body.role, "expires_days": body.expires_days}


@router.get("/team")
def get_team(user_id: int = Depends(_current_user_id)):
    org_id, _, role = _get_user_org(user_id)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can view team")
    members = get_org_members(org_id)
    seat_usage = get_org_seat_usage(org_id)
    return {"members": members, "seat_usage": seat_usage}


@router.get("/validate/{code}")
def validate_code_public(code: str):
    """Public endpoint — no auth required."""
    info = validate_invite_code(code)
    if not info:
        raise HTTPException(404, "Invite code is invalid, expired, or already used")
    return {
        "org_name": info["org_name"],
        "role": info["role"],
        "tier": info["tier"],
    }


@router.get("")
def list_invite_codes(user_id: int = Depends(_current_user_id)):
    org_id, _, role = _get_user_org(user_id)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can view invite codes")
    return get_invite_codes(org_id)


@router.delete("/team/{user_id_to_remove}")
def remove_member(user_id_to_remove: int, user_id: int = Depends(_current_user_id)):
    org_id, _, role = _get_user_org(user_id)
    if role != "owner":
        raise HTTPException(403, "Only owners can remove members")
    try:
        remove_org_member(user_id_to_remove, org_id, user_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"removed": True}


@router.delete("/{code}")
def revoke_code(code: str, user_id: int = Depends(_current_user_id)):
    org_id, _, role = _get_user_org(user_id)
    if role not in ("owner", "admin"):
        raise HTTPException(403, "Only owners and admins can revoke invite codes")
    deleted = revoke_invite_code(code, org_id)
    if not deleted:
        raise HTTPException(404, "Code not found or already used")
    return {"revoked": True}
