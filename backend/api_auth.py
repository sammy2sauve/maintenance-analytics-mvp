"""
Auth endpoints -- /auth/signup, /auth/login, /auth/me
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from .auth import (
    init_users_table,
    get_user_by_email,
    create_user,
    create_user_shell,
    validate_invite_code,
    accept_invite_code,
    verify_password,
    create_token,
    decode_token,
    get_user_locations,
)

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer = HTTPBearer()

init_users_table()

# -- Schemas ------------------------------------------------------------------

class SignupRequest(BaseModel):
    name:        str
    email:       EmailStr
    password:    str
    org_name:    str = None
    invite_code: str = None

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class AuthResponse(BaseModel):
    token: str
    user:  dict

# -- Endpoints ----------------------------------------------------------------

@router.post("/signup", response_model=AuthResponse)
def signup(body: SignupRequest):
    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")
    if get_user_by_email(body.email):
        raise HTTPException(409, "An account with that email already exists")

    if body.invite_code:
        code_info = validate_invite_code(body.invite_code)
        if not code_info:
            raise HTTPException(400, "Invite code is invalid, expired, or already used")
        user = create_user_shell(body.name, body.email, body.password)
        accept_invite_code(body.invite_code, user["id"])
        db_user = get_user_by_email(body.email)
        user["org_id"] = db_user.get("org_id")
    else:
        user = create_user(body.name, body.email, body.password, org_name=body.org_name)

    token = create_token(user["id"], user["email"])
    locations = get_user_locations(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "org_id": user.get("org_id"),
            "locations": locations,
        },
    }


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest):
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_token(user["id"], user["email"])
    locations = get_user_locations(user["id"])
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "org_id": user.get("org_id"),
            "locations": locations,
        },
    }


@router.get("/me")
def me(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(401, "Invalid or expired token")
    user = get_user_by_email(payload["email"])
    if not user:
        raise HTTPException(401, "User not found")
    locations = get_user_locations(user["id"])
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "org_id": user.get("org_id"),
        "locations": locations,
    }
