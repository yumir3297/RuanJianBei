from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.core.config import Settings
from app.core.deps import get_app_settings


router = APIRouter()


class LoginRequest(BaseModel):
    password: str


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"


def create_admin_token(secret: str) -> str:
    timestamp = str(int(time.time()))
    signature = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()[:32]
    payload = f"admin:{timestamp}:{signature}"
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")


def verify_admin_token(token: str, secret: str) -> bool:
    try:
        payload = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        parts = payload.split(":")
        if len(parts) != 3 or parts[0] != "admin":
            return False
        _prefix, timestamp, signature = parts
        expected = hmac.new(
            secret.encode("utf-8"),
            timestamp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:32]
        return hmac.compare_digest(signature, expected)
    except Exception:
        return False


def require_admin_token(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_app_settings),
) -> None:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误，请使用 Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_admin_token(token, settings.admin_token_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login", response_model=LoginResponse)
def admin_login(payload: LoginRequest, settings: Settings = Depends(get_app_settings)) -> LoginResponse:
    if not hmac.compare_digest(payload.password, settings.admin_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
        )
    token = create_admin_token(settings.admin_token_secret)
    return LoginResponse(token=token)
