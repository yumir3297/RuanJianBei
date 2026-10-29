from __future__ import annotations

import asyncio
from http.cookies import SimpleCookie

from fastapi import HTTPException, Response
from starlette.requests import Request

from app.tests.async_db import open_test_session


def _request(*, cookie: str = "", origin: str | None = "http://testserver", headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    values = [(b"host", b"testserver")]
    if origin is not None:
        values.append((b"origin", origin.encode()))
    if cookie:
        values.append((b"cookie", cookie.encode()))
    values.extend(headers or [])
    return Request({"type": "http", "method": "GET", "scheme": "http", "path": "/api/tour-sessions/bootstrap",
                    "raw_path": b"/api/tour-sessions/bootstrap", "query_string": b"", "headers": values,
                    "server": ("testserver", 80), "client": ("testclient", 1234), "http_version": "1.1"})


def test_identity_cookie_is_random_http_only_and_reuses_digest_record():
    async def scenario():
        from app.models.tour_session import TourIdentity
        from app.services.tour_session_identity import ensure_tour_identity
        engine, db = await open_test_session()
        try:
            first_response = Response()
            identity, token = await ensure_tour_identity(_request(), first_response, db, "test-secret")
            cookies = SimpleCookie()
            cookies.load("\n".join(first_response.headers.getlist("set-cookie")))
            raw_credential = cookies["tour_identity"].value
            assert cookies["tour_identity"]["httponly"] is True
            assert raw_credential not in identity.credential_digest
            assert token
            assert await db.get(TourIdentity, identity.id) is identity

            repeat_request = _request(cookie=f"tour_identity={raw_credential}")
            second_response = Response()
            reused, _ = await ensure_tour_identity(repeat_request, second_response, db, "test-secret")
            assert reused.id == identity.id
        finally:
            await db.close()
            await engine.dispose()
    asyncio.run(scenario())


def test_csrf_requires_matching_signed_cookie_header_and_same_origin():
    from app.services.tour_session_identity import _csrf_token, require_tour_write_protection

    class Identity:
        id = "identity-id"

    csrf = _csrf_token("identity-id", "test-secret")
    allowed = _request(cookie=f"tour_csrf={csrf}", headers=[(b"x-csrf-token", csrf.encode())])
    require_tour_write_protection(allowed, Identity(), "test-secret")

    for request in (
        _request(cookie=f"tour_csrf={csrf}", origin="http://attacker.test", headers=[(b"x-csrf-token", csrf.encode())]),
        _request(cookie=f"tour_csrf={csrf}", headers=[(b"x-csrf-token", b"different")]),
        _request(cookie=f"tour_csrf={csrf}", origin=None, headers=[(b"x-csrf-token", csrf.encode())]),
    ):
        try:
            require_tour_write_protection(request, Identity(), "test-secret")
        except HTTPException as error:
            assert error.status_code == 403
        else:
            raise AssertionError("cross-origin or invalid CSRF request must be rejected")
