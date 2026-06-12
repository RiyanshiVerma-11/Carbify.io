"""
backend/app/auth.py
─────────────────────────────────────────────────────────────
Authentication utilities — password hashing, JWT token
creation/verification, and the FastAPI dependency that resolves
a Bearer token to a live User ORM object.

JWT implementation uses PyJWT (actively maintained, CVE-free)
instead of the archived python-jose library.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from jwt import DecodeError, ExpiredSignatureError, InvalidTokenError

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app import models

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# ---------------------------------------------------------------------------
# Password utilities
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if *plain_password* matches the bcrypt *hashed_password*.

    Passes a SHA-256 pre-hash to bcrypt to prevent 72-character truncation.
    """
    try:
        pre_hashed = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return bcrypt.checkpw(
            pre_hashed.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Return a bcrypt hash of *password* using a freshly generated salt.

    Passes a SHA-256 pre-hash to bcrypt to prevent 72-character truncation.
    """
    pre_hashed = hashlib.sha256(password.encode("utf-8")).hexdigest()
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pre_hashed.encode("utf-8"), salt).decode("utf-8")


# ---------------------------------------------------------------------------
# JWT token utilities  (PyJWT ≥ 2.x API)
# ---------------------------------------------------------------------------


def create_access_token(
    data: dict[str, str],
    expires_delta: timedelta | None = None,
) -> str:
    """Encode *data* into a signed JWT with an expiry claim.

    Parameters
    ----------
    data:
        Payload dict.  A copy is made so the caller's dict is not mutated.
    expires_delta:
        Override the default token lifetime defined in settings.

    Returns
    -------
    str
        Compact, URL-safe JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire

    # PyJWT 2.x: jwt.encode() always returns str (not bytes).
    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, str]:
    """Decode and verify a JWT, returning the payload dict.

    Raises
    ------
    jwt.exceptions.InvalidTokenError (or subclass)
        On any verification failure (expired, bad signature, malformed).
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    """FastAPI dependency that validates the Bearer token and returns the
    authenticated User ORM object.

    HTTP 401 is raised for:
      • Missing / malformed token
      • Expired token
      • Token with no ``sub`` claim
      • ``sub`` value that does not map to a database user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (DecodeError, InvalidTokenError):
        raise credentials_exception

    user: models.User | None = (
        db.query(models.User)
        .filter(models.User.username == username)
        .first()
    )
    if user is None:
        raise credentials_exception
    return user


__all__ = [
    "oauth2_scheme",
    "verify_password",
    "get_password_hash",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
]
