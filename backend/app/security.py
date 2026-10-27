"""Password hashing (argon2) + JWT issue/verify (python-jose)."""
from datetime import datetime, timedelta, timezone
from typing import Any

import argon2
from jose import JWTError, jwt

from app.config import settings

_ph = argon2.PasswordHasher(time_cost=3, memory_cost=19456, parallelism=4)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    import argon2.exceptions as argon2_exc
    try:
        return _ph.verify(hashed, plain)
    except (argon2_exc.VerifyMismatchError, argon2_exc.InvalidHashError):
        return False


def create_tokens(sub: str, role: str, uid: int) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    access_exp = now + timedelta(minutes=settings.access_token_minutes)
    refresh_exp = now + timedelta(days=settings.refresh_token_days)
    access = jwt.encode(
        {"sub": sub, "role": role, "uid": uid, "type": "access", "exp": access_exp},
        settings.jwt_secret, algorithm=settings.jwt_algorithm)
    refresh = jwt.encode(
        {"sub": sub, "role": role, "uid": uid, "type": "refresh", "exp": refresh_exp},
        settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return access, refresh


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != expected_type:
        raise JWTError("wrong token type")
    return payload


def token_payload(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
