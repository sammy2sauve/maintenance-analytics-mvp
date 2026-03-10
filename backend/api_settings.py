"""
Settings endpoints — /settings/maintainx-key

The API key is encrypted before storage and NEVER returned to the frontend.
Frontend only ever receives {"connected": true/false}.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from .auth import decode_token, save_user_api_key, delete_user_api_key, has_api_key
from .adapter_maintainx import sync as mx_sync

router = APIRouter(prefix="/settings", tags=["Settings"])
bearer = HTTPBearer()


def _current_user_id(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> int:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    return int(payload["sub"])


class ApiKeyRequest(BaseModel):
    api_key: str


@router.post("/maintainx-key")
def save_key(body: ApiKeyRequest, user_id: int = Depends(_current_user_id)):
    if not body.api_key.strip():
        raise HTTPException(400, "API key cannot be empty")
    save_user_api_key(user_id, body.api_key.strip())
    return {"connected": True}


@router.get("/maintainx-key")
def key_status(user_id: int = Depends(_current_user_id)):
    return {"connected": has_api_key(user_id)}


@router.delete("/maintainx-key")
def remove_key(user_id: int = Depends(_current_user_id)):
    delete_user_api_key(user_id)
    return {"connected": False}


@router.post("/maintainx-sync")
def trigger_sync(user_id: int = Depends(_current_user_id)):
    if not has_api_key(user_id):
        raise HTTPException(400, "No MaintainX API key stored")
    inserted, updated = mx_sync()
    return {"inserted": inserted, "updated": updated}
