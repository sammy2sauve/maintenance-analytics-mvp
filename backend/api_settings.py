"""
Settings endpoints -- /settings/maintainx-key, /settings/status

The API key is encrypted before storage and NEVER returned to the frontend.
Frontend only ever receives {"connected": true/false}.

Multi-tenant: API key belongs to a LOCATION, not a user.
Frontend sends location_id to specify which location to configure.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import (
    decode_token,
    save_location_api_key,
    delete_location_api_key,
    location_has_api_key,
    user_can_access_location,
    get_user_locations,
    has_api_key,
    save_user_api_key,
    delete_user_api_key,
    get_user_role_in_org,
)
from .adapter_maintainx import sync as mx_sync, mark_implemented_suggestions
from .pipeline import run_pipeline

router = APIRouter(prefix="/settings", tags=["Settings"])
bearer = HTTPBearer()


def _current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return int(payload["sub"])


def _resolve_location(user_id: int, location_id: int = None) -> int:
    """Resolve and authorize a location_id for the current user."""
    locs = get_user_locations(user_id)
    if not locs:
        raise HTTPException(400, "No locations found for this user")
    if location_id is None:
        return locs[0]["id"]
    if not user_can_access_location(user_id, location_id):
        raise HTTPException(403, "You do not have access to this location")
    return location_id


def _require_not_viewer(user_id: int, loc_id: int):
    """Raise 403 if the user is a viewer."""
    locs = get_user_locations(user_id)
    for loc in locs:
        if loc["id"] == loc_id:
            role = get_user_role_in_org(user_id, loc["org_id"])
            if role == "viewer":
                raise HTTPException(403, "Viewers cannot modify settings")
            return


class ApiKeyRequest(BaseModel):
    api_key: str
    location_id: int = None


# -- Status endpoint ----------------------------------------------------------

@router.get("/status")
def settings_status(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    """Return connection status for a location. Used by frontend to show empty state."""
    loc_id = _resolve_location(user_id, location_id)
    return {
        "has_api_key": location_has_api_key(loc_id),
        "location_id": loc_id,
    }


# -- API key CRUD -------------------------------------------------------------

@router.post("/maintainx-key")
def save_key(body: ApiKeyRequest, user_id: int = Depends(_current_user_id)):
    if not body.api_key.strip():
        raise HTTPException(400, "API key cannot be empty")
    loc_id = _resolve_location(user_id, body.location_id)
    _require_not_viewer(user_id, loc_id)
    save_location_api_key(loc_id, body.api_key.strip())
    return {"connected": True, "location_id": loc_id}


@router.get("/maintainx-key")
def key_status(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    loc_id = _resolve_location(user_id, location_id)
    return {"connected": location_has_api_key(loc_id), "location_id": loc_id}


@router.delete("/maintainx-key")
def remove_key(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    loc_id = _resolve_location(user_id, location_id)
    _require_not_viewer(user_id, loc_id)
    delete_location_api_key(loc_id)
    return {"connected": False, "location_id": loc_id}


@router.post("/maintainx-sync")
def trigger_sync(
    location_id: int = Query(None),
    user_id: int = Depends(_current_user_id),
):
    loc_id = _resolve_location(user_id, location_id)
    _require_not_viewer(user_id, loc_id)
    if not location_has_api_key(loc_id):
        raise HTTPException(400, "No MaintainX API key stored for this location")
    inserted, updated = mx_sync(location_id=loc_id)
    pipeline_result = run_pipeline(verbose=False, location_id=loc_id)
    implemented = mark_implemented_suggestions(location_id=loc_id)
    return {
        "inserted": inserted,
        "updated": updated,
        "location_id": loc_id,
        "predictions_stored": pipeline_result.get("predictions_stored", 0),
        "insights_stored": pipeline_result.get("insights_stored", 0),
        "implemented": implemented,
    }
