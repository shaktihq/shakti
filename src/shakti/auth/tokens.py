"""JWT access and refresh token creation / verification."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from shakti.exceptions import HTTPException


def create_access_token(
    payload: dict[str, Any],
    secret: str,
    *,
    expire_minutes: int = 30,
    algorithm: str = "HS256",
) -> str:
    data = {
        **payload,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes),
    }
    return jwt.encode(data, secret, algorithm=algorithm)


def create_refresh_token(
    payload: dict[str, Any],
    secret: str,
    *,
    expire_days: int = 7,
    algorithm: str = "HS256",
) -> str:
    data = {
        **payload,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=expire_days),
    }
    return jwt.encode(data, secret, algorithm=algorithm)


def decode_token(
    token: str,
    secret: str,
    *,
    algorithm: str = "HS256",
) -> dict[str, Any]:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token has expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(401, f"Invalid token: {exc}")
