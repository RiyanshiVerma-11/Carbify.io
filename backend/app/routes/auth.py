"""
backend/app/routes/auth.py
─────────────────────────────────────────────────────────────
Authentication routes — register, login, and "me".

Registration optimisation
─────────────────────────
Instead of two pre-flight SELECT queries to check for duplicate
username/email, we let the database enforce its own UNIQUE
constraints and catch the resulting IntegrityError.  This:
  • Cuts the register path from 3 DB round-trips to 1.
  • Eliminates a TOCTOU (time-of-check / time-of-use) race
    condition that existed with the old approach.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app import auth, models
from backend.app.schemas import Token, UserCreate, UserResponse
from backend.app.database import get_db
from backend.app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
def register(
    request: Request,
    user_in: UserCreate,
    db: Session = Depends(get_db),
) -> models.User:
    """Create a new user account.

    The UNIQUE constraints on ``username`` and ``email`` columns are
    relied upon to detect duplicates — a single INSERT attempt is made
    and any IntegrityError is translated to a clear 400 response.
    """
    hashed_pwd = auth.get_password_hash(user_in.password)
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pwd,
    )
    db.add(new_user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # Introspect the constraint message to give a specific error.
        err_str = str(exc.orig).lower()
        if "username" in err_str:
            detail = "Username already registered"
        elif "email" in err_str:
            detail = "Email already registered"
        else:
            detail = "An account with those credentials already exists"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        ) from exc

    db.refresh(new_user)
    logger.info("New user registered: '%s'", new_user.username)
    return new_user


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> dict:
    """Authenticate with username + password and return a JWT Bearer token."""
    user: models.User | None = (
        db.query(models.User).filter(models.User.username == form_data.username).first()
    )
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


# ---------------------------------------------------------------------------
# Me
# ---------------------------------------------------------------------------


@router.get("/me", response_model=UserResponse)
@limiter.limit("15/minute")
def get_me(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
) -> models.User:
    """Return the profile of the currently authenticated user."""
    return current_user
