"""Access-token revocation via per-user token_version (H2)."""

from backend.models.user import User
from backend.services import password_reset_service
from tests.helpers import register_company


async def test_logout_all_invalidates_access_token(client):
    acc = await register_company(client, "all@acme.com", "Acme")
    headers = acc["headers"]

    # The token works before sign-out-everywhere.
    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200

    out = await client.post("/api/v1/auth/logout-all", headers=headers)
    assert out.status_code == 200

    # The same (now stale-version) access token is rejected.
    after = await client.get("/api/v1/user/me", headers=headers)
    assert after.status_code == 401


async def test_token_version_bump_revokes_existing_token(client, db):
    acc = await register_company(client, "bump@acme.com", "Acme")
    headers = acc["headers"]
    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200

    # Simulate any token_version bump applied out-of-band.
    user = db.query(User).filter(User.id == acc["user_id"]).first()
    user.token_version += 1
    db.commit()

    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 401


async def test_password_reset_revokes_access_then_relogin(client, db):
    acc = await register_company(client, "reset@acme.com", "Acme")
    old_headers = acc["headers"]

    raw = password_reset_service.issue_reset_token(db, acc["user_id"])
    reset = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": raw, "new_password": "newpassword456"},
    )
    assert reset.status_code == 200

    # The pre-reset access token no longer verifies.
    assert (await client.get("/api/v1/user/me", headers=old_headers)).status_code == 401

    # The new password works and yields a usable token.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "reset@acme.com", "password": "newpassword456"},
    )
    assert login.status_code == 200
    new_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get("/api/v1/user/me", headers=new_headers)).status_code == 200


async def test_refresh_keeps_access_valid(client):
    """A normal refresh mints an access token that still verifies (the version
    matches — refresh must not look like a revocation)."""
    acc = await register_company(client, "refresh@acme.com", "Acme")
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": acc["refresh_token"]}
    )
    assert refreshed.status_code == 200
    headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert (await client.get("/api/v1/user/me", headers=headers)).status_code == 200
