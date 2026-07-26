"""Phase 3: Authentication tests."""

from __future__ import annotations

import asyncio

import pytest
import pytest_asyncio

from shakti import Depends, Shakti
from shakti.auth import Auth, User
from shakti.auth.hashing import hash_password, verify_password
from shakti.auth.tokens import create_access_token, create_refresh_token, decode_token
from shakti.exceptions import HTTPException
from shakti.orm import Base, Database
from shakti.testing import TestClient


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_all(Base)
    yield database
    await database._engine.dispose()


@pytest.fixture(scope="module")
def auth(db):
    return Auth(db, secret_key="test-secret-key-phase3", access_token_expire_minutes=60)


@pytest.fixture(scope="module")
def app(db, auth):
    application = Shakti(debug=True)
    db.init_app(application)
    auth.init_app(application)

    @application.get("/protected")
    async def protected(user: User = Depends(auth.get_current_user())):
        return user.to_dict()

    @application.get("/admin-only")
    async def admin_only(user: User = Depends(auth.require_role("admin"))):
        return {"admin": True, "user": user.username}

    @application.get("/api-key-route")
    async def api_key_route(user: User = Depends(auth.get_api_key_user())):
        return {"via_api_key": True, "user": user.username}

    return application


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Hashing tests
# ---------------------------------------------------------------------------

def test_hash_and_verify():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_hash_is_unique():
    assert hash_password("same") != hash_password("same")


# ---------------------------------------------------------------------------
# Token tests
# ---------------------------------------------------------------------------

def test_access_token_round_trip():
    token = create_access_token({"sub": "1", "role": "user"}, "secret")
    payload = decode_token(token, "secret")
    assert payload["sub"] == "1"
    assert payload["type"] == "access"


def test_refresh_token_type():
    token = create_refresh_token({"sub": "1"}, "secret")
    payload = decode_token(token, "secret")
    assert payload["type"] == "refresh"


def test_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc:
        decode_token("not.a.token", "secret")
    assert exc.value.status_code == 401


def test_wrong_secret_raises_401():
    token = create_access_token({"sub": "1"}, "secret-a")
    with pytest.raises(HTTPException):
        decode_token(token, "secret-b")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def test_register(client):
    r = client.post("/auth/register", json={
        "email": "legend@shakti.dev",
        "username": "legend",
        "password": "strongpass123",
    })
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "legend@shakti.dev"
    assert r.json()["user"]["role"] == "user"


def test_register_duplicate_email(client):
    r = client.post("/auth/register", json={
        "email": "legend@shakti.dev",
        "username": "legend2",
        "password": "pass",
    })
    assert r.status_code == 409


def test_register_duplicate_username(client):
    r = client.post("/auth/register", json={
        "email": "other@shakti.dev",
        "username": "legend",
        "password": "pass",
    })
    assert r.status_code == 409


def test_register_missing_field(client):
    r = client.post("/auth/register", json={"email": "x@x.com"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success(client):
    r = client.post("/auth/login", json={
        "email": "legend@shakti.dev",
        "password": "strongpass123",
    })
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    r = client.post("/auth/login", json={
        "email": "legend@shakti.dev",
        "password": "wrong",
    })
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/auth/login", json={
        "email": "nobody@x.dev",
        "password": "pass",
    })
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Protected routes
# ---------------------------------------------------------------------------

def _get_tokens(client):
    r = client.post("/auth/login", json={
        "email": "legend@shakti.dev",
        "password": "strongpass123",
    })
    return r.json()["access_token"], r.json()["refresh_token"]


def test_protected_with_valid_token(client):
    access, _ = _get_tokens(client)
    r = client.get("/protected", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["username"] == "legend"


def test_protected_without_token(client):
    r = client.get("/protected")
    assert r.status_code == 401


def test_protected_with_garbage_token(client):
    r = client.get("/protected", headers={"Authorization": "Bearer garbage"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# /auth/me
# ---------------------------------------------------------------------------

def test_me_endpoint(client):
    access, _ = _get_tokens(client)
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["email"] == "legend@shakti.dev"


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def test_refresh_token(client):
    _, refresh = _get_tokens(client)
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_refresh_with_access_token_fails(client):
    access, _ = _get_tokens(client)
    r = client.post("/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def test_logout(client):
    access, _ = _get_tokens(client)
    r = client.post("/auth/logout", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200
    assert r.json()["message"] == "Logged out successfully"


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------

def test_admin_route_denied_for_user(client):
    access, _ = _get_tokens(client)
    r = client.get("/admin-only", headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 403


def test_admin_route_allowed_for_admin(client, auth, db):
    async def _make_admin():
        await auth.register_user(
            email="admin@shakti.dev",
            username="admin",
            password="adminpass",
            role="admin",
        )
    asyncio.run(_make_admin())

    r = client.post("/auth/login", json={
        "email": "admin@shakti.dev",
        "password": "adminpass",
    })
    access = r.json()["access_token"]
    r2 = client.get("/admin-only", headers={"Authorization": f"Bearer {access}"})
    assert r2.status_code == 200
    assert r2.json()["admin"] is True


# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------

def test_api_key_auth(client, auth):
    async def _setup():
        user = await auth.register_user(
            email="api@shakti.dev",
            username="apiuser",
            password="pass",
        )
        raw_key, _ = await auth.create_api_key(user, "test-key")
        return raw_key
    raw_key = asyncio.run(_setup())

    r = client.get("/api-key-route", headers={"X-API-Key": raw_key})
    assert r.status_code == 200
    assert r.json()["via_api_key"] is True
    assert r.json()["user"] == "apiuser"


def test_invalid_api_key(client):
    r = client.get("/api-key-route", headers={"X-API-Key": "invalid-key"})
    assert r.status_code == 401


def test_missing_api_key(client):
    r = client.get("/api-key-route")
    assert r.status_code == 401
