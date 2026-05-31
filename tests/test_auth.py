"""Auth flow over HTTP: signup, login, /user/me, refresh rotation, logout."""

from tests.helpers import register_company, signup_payload


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


async def test_login_wrong_password(client):
    await register_company(client, "pw@acme.com", "Acme")
    bad = await client.post(
        "/api/v1/auth/login", json={"email": "pw@acme.com", "password": "wrong"}
    )
    assert bad.status_code == 400


async def test_refresh_rotates_and_revokes_old(client):
    acc = await register_company(client, "rot@acme.com", "Acme")
    rt1 = acc["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert first.status_code == 200
    rt2 = first.json()["refresh_token"]
    assert rt2 != rt1

    # The rotated (old) token must no longer work.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt1})
    assert reuse.status_code == 401
    # The new one works.
    again = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt2})
    assert again.status_code == 200


async def test_logout_revokes_refresh(client):
    acc = await register_company(client, "out@acme.com", "Acme")
    rt = acc["refresh_token"]

    out = await client.post("/api/v1/auth/logout", json={"refresh_token": rt})
    assert out.status_code == 200

    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": rt})
    assert reuse.status_code == 401
