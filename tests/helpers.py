"""Test helpers for registering tenants and authenticating over HTTP."""

from httpx import AsyncClient


def signup_payload(email: str, company: str) -> dict:
    """A valid signup body (mirrors backend SignupRequest validation)."""
    return {
        "full_name": "Test Owner",
        "company_name": company,
        "email": email,
        "phone": "+10000000000",
        "password": "password123",
        "verify_password": "password123",
        "address": "1 Test St",
        "city": "Testville",
        "state": "TS",
        "country": "Testland",
        "postal_code": "00000",
    }


async def register_company(client: AsyncClient, email: str, company: str) -> dict:
    """Sign up a new Company (signer = Owner) and log in.

    Returns ``{company_id, user_id, access_token, refresh_token, headers}``.
    Each signup creates a distinct Company — ideal for tenant-isolation tests.
    """
    signup = await client.post(
        "/api/v1/auth/signup", json=signup_payload(email, company)
    )
    assert signup.status_code == 200, signup.text
    ids = signup.json()

    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    return {
        "company_id": ids["company_id"],
        "user_id": ids["user_id"],
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "headers": {"Authorization": f"Bearer {tokens['access_token']}"},
    }
