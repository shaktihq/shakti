"""Shakti Admin — better than Django admin.

Usage::

    from shakti.admin import Admin
    from app.models.post import Post

    admin = Admin(db, auth, title="MyApp Admin")
    admin.register(Post, list_fields=["id","title","created_at"], search_fields=["title"])
    admin.init_app(app)

Then visit http://127.0.0.1:8000/admin
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_, select

from shakti.admin.helpers import activity_log, fmt, to_csv
from shakti.admin.registry import ModelAdmin
from shakti.auth.hashing import verify_password
from shakti.auth.models import User
from shakti.auth.tokens import create_access_token, decode_token
from shakti.exceptions import HTTPException
from shakti.http.request import Request
from shakti.http.response import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from shakti.orm.database import Database
from shakti.routing.router import Router

if TYPE_CHECKING:
    from shakti.application import Shakti
    from shakti.auth.auth import Auth

_COOKIE = "shakti_admin"


class Admin:
    """Admin panel manager."""

    def __init__(
        self,
        db: Database,
        auth: "Auth | None" = None,
        *,
        title: str = "Shakti Admin",
        prefix: str = "/admin",
        secret_key: str = "admin-secret-change-me",
    ) -> None:
        self.db = db
        self.auth = auth
        self.title = title
        self.prefix = prefix
        self.secret_key = auth.secret_key if auth else secret_key
        self._registry: dict[str, ModelAdmin] = {}

    def register(
        self,
        model: type,
        *,
        list_fields: list[str] | None = None,
        search_fields: list[str] | None = None,
        readonly_fields: list[str] | None = None,
        list_per_page: int = 25,
    ) -> None:
        ma = ModelAdmin(
            model=model,
            list_fields=list_fields or [],
            search_fields=search_fields or [],
            readonly_fields=readonly_fields or [],
            list_per_page=list_per_page,
        )
        self._registry[ma.slug] = ma

    def init_app(self, app: "Shakti") -> None:
        from shakti.http.response import RedirectResponse as _RR
        _prefix = self.prefix

        @app.get(_prefix)
        async def _admin_root_redirect() -> _RR:
            return _RR(f"{_prefix}/", status_code=302)

        app.include_router(self._build_router(), prefix=self.prefix)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _models_nav(self) -> list[tuple[str, str]]:
        return [(ma.name, ma.slug) for ma in self._registry.values()]

    def _get_admin_user(self, request: Request) -> dict | None:
        token = None
        raw = request.headers.get("cookie", "")
        for part in raw.split(";"):
            k, _, v = part.strip().partition("=")
            if k == _COOKIE:
                token = v
                break
        if not token:
            return None
        try:
            payload = decode_token(token, self.secret_key)
            if payload.get("type") != "admin":
                return None
            return payload
        except HTTPException:
            return None

    def _require_admin(self, request: Request) -> dict:
        user = self._get_admin_user(request)
        if not user:
            raise HTTPException(302, headers={"location": f"{self.prefix}/login"})
        return user

    def _admin_token(self, user: User) -> str:
        import jwt
        from datetime import datetime, timedelta, timezone
        payload = {
            "sub": str(user.id),
            "username": user.username,
            "type": "admin",
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=480),
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def _cast_form_value(self, raw: str, field_meta: dict) -> Any:
        if raw == "" or raw is None:
            return None
        ft = field_meta["type"]
        if ft == "number":
            return int(raw)
        if ft == "decimal":
            return float(raw)
        if ft == "checkbox":
            return raw.lower() in ("true", "1", "on", "yes")
        return raw

    # ------------------------------------------------------------------
    # Router
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _admin = self

        # Login GET
        @router.get("/login")
        async def login_page(request: Request) -> HTMLResponse:
            from shakti.admin import ui
            return HTMLResponse(ui.login_page(title=_admin.title))

        # Login POST
        @router.post("/login")
        async def login_post(request: Request) -> Response:
            from shakti.admin import ui
            form = await request.form()
            email = form.get("email", "")
            password = form.get("password", "")

            async with _admin.db.session() as session:
                from sqlalchemy import select as _select
                result = await session.execute(_select(User).where(User.email == email))
                user = result.scalar_one_or_none()

            if not user or not verify_password(password, user.hashed_password):
                return HTMLResponse(ui.login_page("Invalid email or password", _admin.title))
            if user.role not in ("admin", "superuser"):
                return HTMLResponse(ui.login_page("Admin access required", _admin.title))

            token = _admin._admin_token(user)
            activity_log.record(user.username, "login", "admin")
            response = RedirectResponse(f"{_admin.prefix}", status_code=302)
            response.set_cookie(_COOKIE, token, httponly=True, samesite="lax", max_age=60*480)
            return response

        # Logout
        @router.post("/logout")
        async def logout_post(request: Request) -> Response:
            response = RedirectResponse(f"{_admin.prefix}/login", status_code=302)
            response.delete_cookie(_COOKIE)
            return response

        # Dashboard
        @router.get("/")
        async def dashboard(request: Request) -> HTMLResponse:
            from shakti.admin import ui
            user = _admin._require_admin(request)
            stats = []
            async with _admin.db.session() as session:
                for ma in _admin._registry.values():
                    count = len((await session.execute(select(ma.model))).scalars().all())
                    stats.append({"name": ma.name, "slug": ma.slug, "count": count})
            return HTMLResponse(ui.dashboard(
                stats, activity_log.recent(20),
                _admin._models_nav(), _admin.title, prefix=_admin.prefix
            ))

        # Model list
        @router.get("/{model_slug}")
        async def model_list(request: Request, model_slug: str) -> HTMLResponse:
            from shakti.admin import ui
            user = _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404, f"Model '{model_slug}' not registered")

            search = request.query_params.get("search", "")
            page = max(1, int(request.query_params.get("page", "1")))
            flash = request.query_params.get("flash", "")

            async with _admin.db.session() as session:
                stmt = select(ma.model)
                if search and ma.search_fields:
                    from sqlalchemy import String
                    from sqlalchemy.orm import InstrumentedAttribute
                    conditions = []
                    for sf in ma.search_fields:
                        col = getattr(ma.model, sf, None)
                        if col is not None:
                            conditions.append(col.ilike(f"%{search}%"))
                    if conditions:
                        stmt = stmt.where(or_(*conditions))
                all_rows = (await session.execute(stmt)).scalars().all()
                total = len(all_rows)
                offset = (page - 1) * ma.list_per_page
                rows = all_rows[offset: offset + ma.list_per_page]

            return HTMLResponse(ui.model_list(
                ma, rows, total, page, ma.list_per_page,
                search, _admin._models_nav(), flash, _admin.title, prefix=_admin.prefix
            ))

        # New form
        @router.get("/{model_slug}/new")
        async def model_new_form(request: Request, model_slug: str) -> HTMLResponse:
            from shakti.admin import ui
            user = _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)
            return HTMLResponse(ui.model_form(ma, None, _admin._models_nav(), admin_title=_admin.title, prefix=_admin.prefix))

        # Create POST
        @router.post("/{model_slug}/new")
        async def model_create(request: Request, model_slug: str) -> Response:
            from shakti.admin import ui
            user_payload = _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)

            form = await request.form()
            fields = {f["name"]: f for f in ma.get_fields()}
            kwargs: dict[str, Any] = {}
            errors: list[str] = []

            for name, meta in fields.items():
                if meta["readonly"] or meta["primary_key"]:
                    continue
                raw = form.get(name)
                if meta["type"] == "checkbox":
                    raw = form.get(name, "false")
                try:
                    val = _admin._cast_form_value(raw, meta)
                    if val is None and not meta["nullable"]:
                        errors.append(f"{name} is required")
                    else:
                        kwargs[name] = val
                except (ValueError, TypeError) as e:
                    errors.append(f"{name}: {e}")

            if errors:
                return HTMLResponse(ui.model_form(ma, None, _admin._models_nav(), errors, _admin.title, prefix=_admin.prefix))

            async with _admin.db.session() as session:
                obj = ma.model(**kwargs)
                session.add(obj)
                await session.commit()
                await session.refresh(obj)

            activity_log.record(user_payload["username"], "created", ma.name, obj.id, str(kwargs))
            return RedirectResponse(f"{_admin.prefix}/{model_slug}?flash=Created+successfully", status_code=302)

        # Edit form
        @router.get("/{model_slug}/{id:int}")
        async def model_edit_form(request: Request, model_slug: str, id: int) -> HTMLResponse:
            from shakti.admin import ui
            _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)
            async with _admin.db.session() as session:
                obj = await session.get(ma.model, id)
            if not obj:
                raise HTTPException(404, f"{ma.name} #{id} not found")
            return HTMLResponse(ui.model_form(ma, obj, _admin._models_nav(), admin_title=_admin.title, prefix=_admin.prefix))

        # Update POST
        @router.post("/{model_slug}/{id:int}")
        async def model_update(request: Request, model_slug: str, id: int) -> Response:
            from shakti.admin import ui
            user_payload = _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)

            async with _admin.db.session() as session:
                obj = await session.get(ma.model, id)
                if not obj:
                    raise HTTPException(404)

                form = await request.form()
                fields = {f["name"]: f for f in ma.get_fields()}
                errors: list[str] = []
                changes: dict[str, Any] = {}

                for name, meta in fields.items():
                    if meta["readonly"] or meta["primary_key"]:
                        continue
                    raw = form.get(name)
                    if meta["type"] == "checkbox":
                        raw = form.get(name, "false")
                    try:
                        val = _admin._cast_form_value(raw, meta)
                        if val is None and not meta["nullable"]:
                            errors.append(f"{name} is required")
                        else:
                            setattr(obj, name, val)
                            changes[name] = val
                    except (ValueError, TypeError) as e:
                        errors.append(f"{name}: {e}")

                if errors:
                    return HTMLResponse(ui.model_form(ma, obj, _admin._models_nav(), errors, _admin.title, prefix=_admin.prefix))

                await session.commit()

            activity_log.record(user_payload["username"], "updated", ma.name, id, str(changes))
            return RedirectResponse(f"{_admin.prefix}/{model_slug}?flash=Saved+successfully", status_code=302)

        # Delete POST
        @router.post("/{model_slug}/{id:int}/delete")
        async def model_delete(request: Request, model_slug: str, id: int) -> Response:
            user_payload = _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)
            async with _admin.db.session() as session:
                obj = await session.get(ma.model, id)
                if not obj:
                    raise HTTPException(404)
                await session.delete(obj)
                await session.commit()
            activity_log.record(user_payload["username"], "deleted", ma.name, id)
            return RedirectResponse(f"{_admin.prefix}/{model_slug}?flash=Deleted+successfully", status_code=302)

        # Export CSV
        @router.get("/{model_slug}/export")
        async def model_export(request: Request, model_slug: str) -> PlainTextResponse:
            _admin._require_admin(request)
            ma = _admin._registry.get(model_slug)
            if not ma:
                raise HTTPException(404)
            async with _admin.db.session() as session:
                rows = (await session.execute(select(ma.model))).scalars().all()
            data_rows = [[getattr(r, f, "") for f in ma.list_fields] for r in rows]
            csv_content = to_csv(ma.list_fields, data_rows)
            return PlainTextResponse(
                csv_content,
                headers={"Content-Disposition": f'attachment; filename="{model_slug}.csv"'},
                media_type="text/csv",
            )

        return router
