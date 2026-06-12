"""
backend/app/routes/habits.py
─────────────────────────────────────────────────────────────
Habits Tracker routes.

HABIT_METRICS is now imported from backend.app.constants —
it is no longer duplicated here.  This keeps the route file
focused on HTTP concerns only (parsing, auth, DB, responses).
"""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app import models, schemas, auth
from backend.app.constants import HABIT_METRICS
from backend.app.database import get_db
from backend.app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/habits", tags=["Habits Tracker"])


# ---------------------------------------------------------------------------
# List available habit types
# ---------------------------------------------------------------------------


@router.get("/list")
@limiter.limit("30/minute")
def list_available_habits(request: Request) -> dict:
    """Return the full habit catalogue with metadata."""
    return HABIT_METRICS


# ---------------------------------------------------------------------------
# Log a habit for today
# ---------------------------------------------------------------------------


@router.post("/log", response_model=schemas.HabitLogResponse)
@limiter.limit("20/minute")
def log_habit(
    request: Request,
    habit_in: schemas.HabitLogCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.HabitsLog:
    """
    Record a single habit log entry for the authenticated user.

    Business rules
    ──────────────
    • The habit key must exist in HABIT_METRICS.
    • The same habit may only be logged once per calendar day.
    """
    habit_name = habit_in.habit_name
    if habit_name not in HABIT_METRICS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown habit key: '{habit_name}'",
        )

    target_date = habit_in.logged_date or datetime.date.today()
    metric = HABIT_METRICS[habit_name]

    # Duplicate-per-day guard
    existing = (
        db.query(models.HabitsLog)
        .filter(
            models.HabitsLog.user_id == current_user.id,
            models.HabitsLog.habit_name == habit_name,
            models.HabitsLog.logged_date == target_date,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You have already logged '{metric['name']}' today!",
        )

    log = models.HabitsLog(
        user_id=current_user.id,
        habit_type=metric["category"],
        habit_name=habit_name,
        co2_saved_kg=metric["co2_saved"],
        points_earned=metric["points"],
        logged_date=target_date,
    )
    db.add(log)

    # Update gamification counters in-memory before commit
    current_user.add_points(metric["points"])

    db.commit()
    logger.info(
        "User '%s' logged habit '%s' — earned %d pts, now level %d.",
        current_user.username,
        habit_name,
        metric["points"],
        current_user.level,
    )
    db.refresh(log)
    db.refresh(current_user)
    return log


# ---------------------------------------------------------------------------
# Habit log history
# ---------------------------------------------------------------------------


@router.get("/history", response_model=list[schemas.HabitLogResponse])
@limiter.limit("30/minute")
def get_habit_history(
    request: Request,
    pagination: schemas.PaginationQuery = Depends(),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> list[models.HabitsLog]:
    """Return all habit log entries for the authenticated user, newest first."""
    offset = (pagination.page - 1) * pagination.limit
    return (
        db.query(models.HabitsLog)
        .filter(models.HabitsLog.user_id == current_user.id)
        .order_by(models.HabitsLog.logged_date.desc())
        .offset(offset)
        .limit(pagination.limit)
        .all()
    )
