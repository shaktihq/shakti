"""Admin panel tests."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
import pytest_asyncio

from shakti import Shakti
from shakti.admin import Admin
from shakti.admin.helpers import to_csv
from shakti.auth import Auth
from shakti.auth.models import User
from shakti.orm import Base, Database
from shakti.orm.repository import Repository
from shakti.testing import TestClient


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="module")
async def db():
    database = Database("sqlite+aiosqlite:///:memory:")
    await database.create_all(Base)
    yield database
    await database._engine.dispose()


@pytest.fixture(scope="module")
def auth(db):
    return Auth(db, secret_key="admin-test-secret")


@pytest.fixture(scope="module")
def admin_panel(db, auth):
    return Admin(db, auth, title="Test Admin")


@pytest.fixture(scope="module")
def app(db, auth, admin_panel):
    application = Shakti(debug=True)
    db.init_app(application)
    auth.init_app(application)
    admin_panel.register(
        User,
        list_fields=["id", "email", "username", "role", "is_active"],
        search_fields=["email", "username"],
    )
    admin_panel.init_app(application)
    return application


@pytest.fixture(scope="module")
def client(app):
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def admin_user(auth):
    async def _create():
        return await auth.register_user(
            email="admin@test.dev",
            username="adminuser",
            password="adminpass",
            role="admin",
        )
    return asyncio.run(_create())


def _login(client, admin_user) -> dict:
    """Log in and return response with session cookie."""
    r = client.post("/admin/login", data={
        "email": "admin@test.dev",
        "password": "adminpass",
    })
    return r


# ---------------------------------------------------------------------------

def test_login_page(client):
    r = client.get("/admin/login")
    assert r.status_code == 200
    assert b"Sign In" in r.content


def test_unauthenticated_redirects(client):
    r = client.get("/admin/")
    assert r.status_code == 302
    assert "/admin/login" in r.headers.get("location", "")


def test_login_wrong_password(client, admin_user):
    r = client.post("/admin/login", data={
        "email": "admin@test.dev",
        "password": "wrong",
    })
    assert r.status_code == 200
    assert b"Invalid" in r.content


def test_login_success(client, admin_user):
    r = _login(client, admin_user)
    assert r.status_code in (302, 307)
    assert "shakti_admin" in r.headers.get("set-cookie", "")


def test_dashboard_authenticated(client, admin_user):
    login_r = _login(client, admin_user)
    cookie_header = login_r.headers.get("set-cookie", "")
    token = ""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("shakti_admin="):
            token = part[len("shakti_admin="):]
            break

    r = client.get("/admin/", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"Dashboard" in r.content


def _get_token(client, admin_user) -> str:
    r = _login(client, admin_user)
    cookie_header = r.headers.get("set-cookie", "")
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("shakti_admin="):
            return part[len("shakti_admin="):]
    return ""


def test_model_list(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get("/admin/users", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"User" in r.content
    assert b"adminuser" in r.content


def test_model_search(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get("/admin/users?search=admin", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"adminuser" in r.content


def test_model_new_form(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get("/admin/users/new", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"New User" in r.content


def test_model_edit_form(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get(f"/admin/users/{admin_user.id}", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"Edit User" in r.content
    assert b"admin@test.dev" in r.content


def test_model_404_unknown(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get("/admin/unknownmodel", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 404


def test_export_csv(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get("/admin/users/export", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"email" in r.content
    assert b"admin@test.dev" in r.content


def test_admin_requires_secret_key_without_auth(db):
    """Regression: Admin must not fall back to a hardcoded public secret
    key when auth= isn't given — that would let anyone forge an admin
    session cookie for a deployment that only passed Admin(db)."""
    with pytest.raises(ValueError, match="secret_key"):
        Admin(db)


def test_admin_accepts_explicit_secret_key_without_auth(db):
    admin = Admin(db, secret_key="a-real-secret")
    assert admin.secret_key == "a-real-secret"


def test_csv_export_neutralizes_formula_injection():
    """Regression: a cell value starting with =, +, -, or @ must be
    prefixed with a single quote so spreadsheet apps don't execute it
    as a formula (CWE-1236) when an admin opens an exported CSV."""
    csv_text = to_csv(
        ["name"],
        [
            ['=HYPERLINK("http://evil.example","click")'],
            ["+1+1"],
            ["-1+1"],
            ["@SUM(1,1)"],
            ["a normal value"],
        ],
    )
    lines = csv_text.strip().splitlines()[1:]  # skip header
    assert lines[0].startswith("\"'=HYPERLINK")
    assert lines[1].startswith("'+")
    assert lines[2].startswith("'-")
    assert lines[3].startswith("\"'@")
    assert lines[4] == "a normal value"


def test_non_admin_cannot_login(client, auth):
    async def _create():
        return await auth.register_user(
            email="plain@test.dev",
            username="plainuser",
            password="pass",
            role="user",
        )
    asyncio.run(_create())
    r = client.post("/admin/login", data={
        "email": "plain@test.dev",
        "password": "pass",
    })
    assert r.status_code == 200
    assert b"Admin access required" in r.content


# ---------------------------------------------------------------------------
# XSS regression tests
#
# The admin UI builds HTML by string interpolation (no autoescaping template
# engine), so anything sourced from the database or a request must be
# HTML-escaped or a regular (non-admin) app user can plant script that runs
# in the admin's authenticated browser session. See shakti/admin/helpers.py
# `esc()` and its call sites in shakti/admin/ui.py.
# ---------------------------------------------------------------------------

_XSS_PAYLOAD = "<script>alert(1)</script>"


_xss_user_counter = {"n": 0}


def _xss_user(auth):
    _xss_user_counter["n"] += 1
    n = _xss_user_counter["n"]
    email = f"xss{n}@test.dev"
    # username must be unique per user but must still *contain* the raw
    # payload so the escaping assertions have something to find.
    username = f"{_XSS_PAYLOAD}{n}"

    async def _create():
        return await auth.register_user(
            email=email,
            username=username,
            password="pass",
            role="user",
        )
    return asyncio.run(_create())


def test_model_list_escapes_stored_field_values(client, admin_user, auth):
    xss_user = _xss_user(auth)
    token = _get_token(client, admin_user)
    r = client.get("/admin/users", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert _XSS_PAYLOAD.encode() not in r.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in r.content


def test_model_edit_form_escapes_stored_field_values(client, admin_user, auth):
    xss_user = _xss_user(auth)
    token = _get_token(client, admin_user)
    r = client.get(f"/admin/users/{xss_user.id}", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert _XSS_PAYLOAD.encode() not in r.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in r.content


def test_model_list_search_is_reflected_safely(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get(
        "/admin/users",
        query={"search": _XSS_PAYLOAD},
        headers={"cookie": f"shakti_admin={token}"},
    )
    assert r.status_code == 200
    assert _XSS_PAYLOAD.encode() not in r.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in r.content


def test_flash_message_is_reflected_safely(client, admin_user):
    token = _get_token(client, admin_user)
    r = client.get(
        "/admin/users",
        query={"flash": _XSS_PAYLOAD},
        headers={"cookie": f"shakti_admin={token}"},
    )
    assert r.status_code == 200
    assert _XSS_PAYLOAD.encode() not in r.content
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in r.content


def test_dashboard_activity_log_escapes_field_values():
    """The activity log's `username`/`detail` columns must not render a
    malicious username or edit-detail unescaped on the dashboard.

    Exercises shakti.admin.ui.dashboard() directly (rather than through a
    live edit) since it only needs to prove the template escapes activity
    log data — not exercise the full HTTP/DB round trip.
    """
    from shakti.admin.helpers import ActivityEntry
    from shakti.admin.ui import dashboard as render_dashboard

    entry = ActivityEntry(
        timestamp=datetime.now(UTC),
        username=_XSS_PAYLOAD,
        action="updated",
        model="User",
        record_id=1,
        detail=f"{{'username': '{_XSS_PAYLOAD}'}}",
    )
    html = render_dashboard(stats=[], activity=[entry], models_slugs=[], title="Test Admin")
    assert _XSS_PAYLOAD not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


# ---------------------------------------------------------------------------
# Server-managed (TimestampMixin) field regression tests
#
# get_fields() previously presented created_at/updated_at as required,
# hand-editable fields with no admin UI conversion for datetime input —
# submitting the edit form always failed, either with a SQLite TypeError
# (raw "YYYY-MM-DDTHH:MM" string passed to a DateTime column) or a
# "created_at is required" validation error if the fields were omitted.
# ---------------------------------------------------------------------------

def test_server_managed_timestamp_fields_are_readonly():
    from shakti.admin.registry import ModelAdmin

    ma = ModelAdmin(model=User)
    fields = {f["name"]: f for f in ma.get_fields()}
    assert fields["created_at"]["readonly"] is True
    assert fields["updated_at"]["readonly"] is True
    assert fields["email"]["readonly"] is False


def test_editing_a_user_via_admin_form_actually_succeeds(client, admin_user, auth):
    async def _create():
        return await auth.register_user(
            email="editme@test.dev", username="editme", password="pass", role="user",
        )
    target = asyncio.run(_create())

    token = _get_token(client, admin_user)
    r = client.post(
        f"/admin/users/{target.id}",
        data={"email": target.email, "username": "renamed", "role": "user", "is_active": "true"},
        headers={"cookie": f"shakti_admin={token}"},
    )
    assert r.status_code in (302, 307), r.text

    r = client.get(f"/admin/users/{target.id}", headers={"cookie": f"shakti_admin={token}"})
    assert r.status_code == 200
    assert b"renamed" in r.content


def test_datetime_field_without_server_default_is_parsed_correctly():
    """A developer-defined datetime column (no server_default) is still
    admin-editable — _cast_form_value must convert the datetime-local
    string into a real datetime, not pass it through as raw text."""
    admin = Admin.__new__(Admin)  # no db/auth needed for this pure method
    meta = {"type": "datetime"}
    result = admin._cast_form_value("2024-06-15T14:30", meta)
    assert result == datetime(2024, 6, 15, 14, 30, tzinfo=UTC)
