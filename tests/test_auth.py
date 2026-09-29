from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings


def test_register_creates_user_and_account(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "Jamie Lee", "email": "jamie@example.com", "password": "Sufficient12!"},
    )

    assert response.status_code == 201
    assert len(response.json()["account_number"]) == 10
    assert "password" not in response.json()["user"]
    assert client.post(
        "/api/auth/register",
        json={"name": "Jamie Lee", "email": "jamie@example.com", "password": "Sufficient12!"},
    ).status_code == 409


def test_duplicate_email_is_case_insensitive(client):
    client.post(
        "/api/auth/register",
        json={"name": "Jamie Lee", "email": "jamie@example.com", "password": "Sufficient12!"},
    )
    response = client.post(
        "/api/auth/register",
        json={"name": "Another Name", "email": "JAMIE@example.com", "password": "Sufficient12!"},
    )
    assert response.status_code == 409


def test_login_and_generic_invalid_credentials(client):
    user = {"name": "Jamie Lee", "email": "jamie@example.com", "password": "Sufficient12!"}
    client.post("/api/auth/register", json=user)

    valid = client.post("/api/auth/login", json={"email": user["email"], "password": user["password"]})
    invalid = client.post("/api/auth/login", json={"email": user["email"], "password": "wrong-password"})
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})

    assert valid.status_code == 200
    assert valid.json()["token_type"] == "bearer"
    assert invalid.status_code == unknown.status_code == 401
    assert invalid.json() == unknown.json() == {"detail": "Invalid email or password"}


def test_protected_endpoint_rejects_missing_and_invalid_tokens(client):
    assert client.get("/api/accounts/me").status_code == 401
    response = client.get("/api/accounts/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_protected_endpoint_rejects_expired_token(client):
    expired_token = jwt.encode(
        {
            "sub": "1",
            "exp": datetime.now(UTC) - timedelta(minutes=1),
            "jti": "expired-test-token",
        },
        settings.secret_key,
        algorithm=settings.algorithm,
    )

    response = client.get("/api/accounts/me", headers={"Authorization": f"Bearer {expired_token}"})

    assert response.status_code == 401


def test_logout_revokes_current_token(client, register_user):
    user = register_user()
    assert client.get("/api/accounts/me", headers=user["headers"]).status_code == 200

    logout = client.post("/api/auth/logout", headers=user["headers"])
    account = client.get("/api/accounts/me", headers=user["headers"])

    assert logout.status_code == 200
    assert account.status_code == 401