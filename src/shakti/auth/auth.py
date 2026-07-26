"""Auth manager: JWT, RBAC, and API key authentication for Shakti.

Usage::

    from shakti.auth import Auth
    from shakti.auth.models import User

    auth = Auth(db, secret_key=config.require("auth.secret_key"))
    auth.init_app(app)

    # Protect a route — any authenticated user
    @app.get("/me")
    async def me(user: User = Depends(auth.get_current_user())):
        return user.to_dict()

    # Restrict to roles
    @app.delete("/admin/users/{id:int}")
    async def delete_user(id: int, user=Depends(auth.require_role("admin"))):
        ...

    # API key auth
    @app.get("/webhook")
    async def webhook(user=Depends(auth.get_api_key_user())):
        ...
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from shakti.auth.hashing import hash_password, verify_password
from shakti.auth.models import APIKey, User
from shakti.auth.tokens import create_access_token, create_refresh_token, decode_token
from shakti.exceptions import HTTPException
from shakti.http.request import Request
from shakti.orm.database import Database
from shakti.routing.router import Router

if TYPE_CHECKING:
    from shakti.application import Shakti


class Auth:
    """Authentication + authorisation manager."""

    def __init__(
        self,
        db: Database,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 30,
        refresh_token_expire_days: int = 7,
        prefix: str = "/auth",
    ) -> None:
        if not secret_key:
            raise ValueError("Auth: secret_key must not be empty")
        self.db = db
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_expire = access_token_expire_minutes
        self.refresh_expire = refresh_token_expire_days
        self.prefix = prefix

    # ------------------------------------------------------------------
    # App integration
    # ------------------------------------------------------------------
    def init_app(self, app: "Shakti") -> None:
        """Register auth routes and inject Auth into the DI container."""
        app.container.register_instance(Auth, self)
        app.include_router(self._build_router(), prefix=self.prefix)

    # ------------------------------------------------------------------
    # Internal token helpers
    # ------------------------------------------------------------------
    def _make_access_token(self, user: User) -> str:
        return create_access_token(
            {"sub": str(user.id), "role": user.role},
            self.secret_key,
            expire_minutes=self.access_expire,
            algorithm=self.algorithm,
        )

    def _make_refresh_token(self, user: User) -> str:
        return create_refresh_token(
            {"sub": str(user.id)},
            self.secret_key,
            expire_days=self.refresh_expire,
            algorithm=self.algorithm,
        )

    async def _verify_jwt(self, request: Request) -> User:
        """Extract Bearer token, verify, and return the User."""
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(401, "Missing or invalid Authorization header")
        token = auth_header[7:]
        payload = decode_token(token, self.secret_key, algorithm=self.algorithm)
        if payload.get("type") != "access":
            raise HTTPException(401, "Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid token payload")
        async with self.db.session() as session:
            user = await session.get(User, int(user_id))
        if user is None or not user.is_active:
            raise HTTPException(401, "User not found or inactive")
        return user

    # ------------------------------------------------------------------
    # Dependency factories  (call these inside Depends())
    # ------------------------------------------------------------------
    def get_current_user(self) -> Callable[[Request], Any]:
        """Returns a dependency that resolves the current JWT-authenticated user.

        Usage: ``user: User = Depends(auth.get_current_user())``
        """
        _auth = self

        async def _dep(request: Request) -> User:
            return await _auth._verify_jwt(request)

        return _dep

    def require_role(self, *roles: str) -> Callable[[Request], Any]:
        """Returns a dependency that enforces one of the given roles.

        Usage: ``user: User = Depends(auth.require_role("admin"))``
        """
        _auth = self

        async def _dep(request: Request) -> User:
            user = await _auth._verify_jwt(request)
            if user.role not in roles:
                raise HTTPException(
                    403, f"Required role: {' or '.join(roles)}. Got: {user.role}"
                )
            return user

        return _dep

    def get_api_key_user(self) -> Callable[[Request], Any]:
        """Returns a dependency that authenticates via the X-API-Key header.

        Usage: ``user: User = Depends(auth.get_api_key_user())``
        """
        _auth = self

        async def _dep(request: Request) -> User:
            raw_key = request.headers.get("x-api-key", "")
            if not raw_key:
                raise HTTPException(401, "Missing X-API-Key header")
            async with _auth.db.session() as session:
                result = await session.execute(
                    select(APIKey).where(APIKey.is_active == True)  # noqa: E712
                )
                for api_key in result.scalars():
                    if verify_password(raw_key, api_key.key_hash):
                        user = await session.get(User, api_key.user_id)
                        if user and user.is_active:
                            return user
            raise HTTPException(401, "Invalid or inactive API key")

        return _dep

    # ------------------------------------------------------------------
    # User management helpers
    # ------------------------------------------------------------------
    async def register_user(
        self,
        email: str,
        username: str,
        password: str,
        *,
        role: str = "user",
    ) -> User:
        """Create a new user. Raises 409 if email/username is taken."""
        async with self.db.session() as session:
            if (await session.execute(select(User).where(User.email == email))).scalar_one_or_none():
                raise HTTPException(409, "Email already registered")
            if (await session.execute(select(User).where(User.username == username))).scalar_one_or_none():
                raise HTTPException(409, "Username already taken")
            user = User(
                email=email,
                username=username,
                hashed_password=hash_password(password),
                role=role,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def create_api_key(self, user: User, name: str) -> tuple[str, APIKey]:
        """Generate a new API key. Returns (raw_key, APIKey).

        Store the raw_key securely — it is never retrievable again.
        """
        raw_key = secrets.token_hex(32)
        async with self.db.session() as session:
            api_key = APIKey(
                user_id=user.id,
                name=name,
                key_hash=hash_password(raw_key),
            )
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
        return raw_key, api_key

    async def revoke_api_key(self, api_key_id: int) -> None:
        """Deactivate an API key by ID."""
        async with self.db.session() as session:
            key = await session.get(APIKey, api_key_id)
            if key:
                key.is_active = False
                await session.commit()

    # ------------------------------------------------------------------
    # Auth router
    # ------------------------------------------------------------------
    def _build_router(self) -> Router:
        router = Router()
        _auth = self

        @router.post("/register")
        async def register(body: dict) -> dict:
            for field in ("email", "username", "password"):
                if field not in body:
                    raise HTTPException(422, f"Missing field: {field}")
            user = await _auth.register_user(
                email=body["email"],
                username=body["username"],
                password=body["password"],
                role=body.get("role", "user"),
            )
            return {"message": "User registered", "user": user.to_dict()}

        @router.post("/login")
        async def login(body: dict) -> dict:
            for field in ("email", "password"):
                if field not in body:
                    raise HTTPException(422, f"Missing field: {field}")
            async with _auth.db.session() as session:
                result = await session.execute(
                    select(User).where(User.email == body["email"])
                )
                user = result.scalar_one_or_none()
            if user is None or not verify_password(body["password"], user.hashed_password):
                raise HTTPException(401, "Invalid email or password")
            if not user.is_active:
                raise HTTPException(403, "Account is disabled")

            access_token = _auth._make_access_token(user)
            refresh_token = _auth._make_refresh_token(user)

            async with _auth.db.session() as session:
                db_user = await session.get(User, user.id)
                db_user.refresh_token = refresh_token
                await session.commit()

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "user": user.to_dict(),
            }

        @router.post("/refresh")
        async def refresh(body: dict) -> dict:
            token = body.get("refresh_token", "")
            if not token:
                raise HTTPException(422, "Missing refresh_token")
            payload = decode_token(token, _auth.secret_key, algorithm=_auth.algorithm)
            if payload.get("type") != "refresh":
                raise HTTPException(401, "Invalid token type")
            user_id = payload.get("sub")
            async with _auth.db.session() as session:
                user = await session.get(User, int(user_id))
            if user is None or user.refresh_token != token:
                raise HTTPException(401, "Refresh token revoked or invalid")
            if not user.is_active:
                raise HTTPException(403, "Account is disabled")

            new_access = _auth._make_access_token(user)
            new_refresh = _auth._make_refresh_token(user)

            async with _auth.db.session() as session:
                db_user = await session.get(User, user.id)
                db_user.refresh_token = new_refresh
                await session.commit()

            return {
                "access_token": new_access,
                "refresh_token": new_refresh,
                "token_type": "bearer",
            }

        @router.post("/logout")
        async def logout(request: Request) -> dict:
            user = await _auth._verify_jwt(request)
            async with _auth.db.session() as session:
                db_user = await session.get(User, user.id)
                db_user.refresh_token = None
                await session.commit()
            return {"message": "Logged out successfully"}

        @router.get("/me")
        async def me(request: Request) -> dict:
            user = await _auth._verify_jwt(request)
            return user.to_dict()

        return router

    def __repr__(self) -> str:
        return f"<Auth prefix={self.prefix!r} algorithm={self.algorithm!r}>"
