"""Auth flow over HTTP: signup, login, /user/me, refresh rotation, logout.

Two transports for the refresh token (audit H1): browser clients use the
httpOnly cookie (the SPA sends no body), non-browser clients (legacy Streamlit,
tests) pass it in the body. ``httpx`` persists Set-Cookie across requests, so
body-path tests clear the jar to isolate the body credential — a real cookie-
less API client (``requests`` without a Session) behaves the same way.
"""

from backend.config import settings
from tests.helpers import register_company, signup_payload

COOKIE = settings.REFRESH_COOKIE_NAME


async def test_signup_creates_company_and_rejects_duplicate(client):
    payload = signup_payload("owner@acme.com", "Acme")
    res = await client.post("/api/v1/auth/signup", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["company_id"] and body["user_id"]

    dup = await client.post("/api/v1/auth/signup", json=payload)
    assert dup.status_code == 400  # email already registered


async def test_login_and_me(client):
    acc = await register_company(client, "me@acme.com", "Acme")

    me = await client.get("/api/v1/user/me", headers=acc["headers"])
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "me@acme.com"
    assert me.json()["user"]["role"] == "owner"

    # No token → rejected by the bearer dependency.
    anon = await client.get("/api/v1/user/me")
    assert anon.status_code == 403


async def test_security_headers_present(client):
    """Baseline security response headers are set (audit H1)."""
    res = await client.get("/health")
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("referrer-policy") == "no-referrer"
    # HSTS only in production (dev default ENVIRONMENT) — absent here.
    assert "strict-transport-security" not in res.headers


async def test_login_wrong_password(client):
    await register_company(client, "pw@acme.com", "Acme")
    bad = await client.post(
        "/api/v1/auth/login", json={"email": "pw@acme.com", "password": "wrong"}
    )
    assert bad.status_code == 400


async def test_refresh_rotates_and_revokes_old(client):
    """Body path (non-browser client): rotation revokes the presented token."""
    acc = await register_company(client, "rot@acme.com", "Acme")
    rt1 = acc["refresh_token"]
    client.cookies.clear()  # isolate the body credential

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert first.status_code == 200
    rt2 = first.json()["refresh_token"]
    assert rt2 != rt1
    client.cookies.clear()

    # The rotated (old) token must no longer work.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert reuse.status_code == 401
    client.cookies.clear()
    # The new one works.
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})
    assert again.status_code == 200


async def test_logout_revokes_refresh(client):
    """Body path: logout revokes the presented refresh token."""
    acc = await register_company(client, "out@acme.com", "Acme")
    rt = acc["refresh_token"]
    client.cookies.clear()

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert out.status_code == 200

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert reuse.status_code == 401


async def test_login_sets_httponly_refresh_cookie(client):
    """Login delivers the refresh token as an httpOnly cookie (audit H1)."""
    await register_company(client, "cookie@acme.com", "Acme")
    client.cookies.clear()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "cookie@acme.com", "password": "password123"},
    )
    assert login.status_code == 200
    raw = login.headers.get("set-cookie", "").lower()
    assert COOKIE.lower() in raw
    assert "httponly" in raw
    assert f"path={settings.REFRESH_COOKIE_PATH}".lower() in raw
    # The browser holds the access token in memory; only the refresh is a cookie.
    assert client.cookies.get(COOKIE) is not None


async def test_refresh_via_cookie_no_body(client):
    """Browser path: /refresh works from the cookie with no request body."""
    await register_company(client, "ck-refresh@acme.com", "Acme")
    rt1 = client.cookies.get(COOKIE)
    assert rt1 is not None

    res = await client.post("/api/v1/auth/refresh")  # no body, cookie carries it
    assert res.status_code == 200
    assert res.json()["access_token"]
    rt2 = client.cookies.get(COOKIE)
    assert rt2 and rt2 != rt1  # rotated, new cookie set


async def test_logout_via_cookie_clears_and_revokes(client):
    """Browser path: /logout revokes from the cookie and expires it."""
    await register_company(client, "ck-logout@acme.com", "Acme")
    rt = client.cookies.get(COOKIE)
    assert rt is not None

    out = await client.post("/api/v1/auth/logout")  # no body
    assert out.status_code == 200
    # Cookie expired by the response (httpx drops a Max-Age=0 cookie).
    assert client.cookies.get(COOKIE) is None
    # And the underlying token is revoked (body path proves it server-side).
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert reuse.status_code == 401
