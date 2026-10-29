from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tour_session import TourIdentity

IDENTITY_COOKIE = "tour_identity"
CSRF_COOKIE = "tour_csrf"
IDENTITY_TTL_DAYS = 365


def _credential_digest(credential: str) -> str:
    return hashlib.sha256(credential.encode("utf-8")).hexdigest()


def _csrf_token(identity_id: str, secret: str) -> str:
    nonce = secrets.token_urlsafe(24)
    message = f"{identity_id}:{nonce}"
    signature = hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest()
    encoded = base64.urlsafe_b64encode(f"{message}:{signature}".encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def _valid_csrf(token: str, identity_id: str, secret: str) -> bool:
    try:
        padded = token + "=" * (-len(token) % 4)
        message = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        token_identity, nonce, signature = message.split(":", 2)
        if token_identity != identity_id or not nonce:
            return False
        expected = hmac.new(secret.encode("utf-8"), f"{token_identity}:{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except (ValueError, UnicodeError):
        return False


async def ensure_tour_identity(
    request: Request, response: Response, db: AsyncSession, secret: str,
) -> tuple[TourIdentity, str]:
    """Resolve the HttpOnly identity cookie or issue a new anonymous identity."""
    raw_credential = request.cookies.get(IDENTITY_COOKIE)
    identity = None
    if raw_credential:
        identity = await db.scalar(select(TourIdentity).where(
            TourIdentity.credential_digest == _credential_digest(raw_credential),
            TourIdentity.expires_at > datetime.now(UTC),
        ))

    secure = request.url.scheme.lower() == "https"
    if identity is None:
        raw_credential = secrets.token_urlsafe(48)
        identity = TourIdentity(
            id=secrets.token_urlsafe(18),
            credential_digest=_credential_digest(raw_credential),
            expires_at=datetime.now(UTC) + timedelta(days=IDENTITY_TTL_DAYS),
        )
        db.add(identity)
        await db.commit()
        await db.refresh(identity)
        response.set_cookie(
            IDENTITY_COOKIE, raw_credential, max_age=IDENTITY_TTL_DAYS * 24 * 60 * 60,
            httponly=True, secure=secure, samesite="lax", path="/api",
        )

    csrf = request.cookies.get(CSRF_COOKIE, "")
    if not _valid_csrf(csrf, identity.id, secret):
        csrf = _csrf_token(identity.id, secret)
        response.set_cookie(
            CSRF_COOKIE, csrf, max_age=IDENTITY_TTL_DAYS * 24 * 60 * 60,
            httponly=False, secure=secure, samesite="lax", path="/api",
        )
    return identity, csrf


def require_tour_write_protection(request: Request, identity: TourIdentity, secret: str) -> None:
    origin = request.headers.get("origin")
    host = request.headers.get("host", "")
    if not origin or not host:
        raise HTTPException(status_code=403, detail="请从当前景区页面发起操作")
    from urllib.parse import urlsplit

    parsed = urlsplit(origin)
    if parsed.scheme.lower() != request.url.scheme.lower() or parsed.netloc.lower() != host.lower():
        raise HTTPException(status_code=403, detail="跨来源请求已拒绝")

    cookie_token = request.cookies.get(CSRF_COOKIE, "")
    header_token = request.headers.get("x-csrf-token", "")
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
        or not _valid_csrf(cookie_token, identity.id, secret)
    ):
        raise HTTPException(status_code=403, detail="安全校验已失效，请刷新页面后重试")
