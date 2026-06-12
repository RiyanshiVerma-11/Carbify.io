"""
backend/app/routes/habits.py
─────────────────────────────────────────────────────────────
Habits Tracker routes.

Default habit seed data is imported from ``backend.app.constants``
(``DEFAULT_HABITS``), keeping this route file focused exclusively
on HTTP concerns: request parsing, auth enforcement, DB interaction,
and response serialisation.

Endpoints
---------
GET   /api/habits/list     – Full habit catalogue with metadata.
POST  /api/habits/log      – Log a habit for today (once per day).
GET   /api/habits/history  – Paginated log history for current user.
POST  /api/habits/          – Create a custom habit.
PUT   /api/habits/{id}     – Update a habit.
DELETE /api/habits/{id}   – Delete a habit.
"""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app import models, schemas, auth
from backend.app.database import get_db
from backend.app.limiter import limiter
from backend.app.constants import DEFAULT_HABITS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/habits", tags=["Habits Tracker"])


def seed_habits(db: Session) -> None:
    """Insert default habits into the database if they don't already exist.

    Uses a count-first optimisation: if the table already contains the
    expected number of habits, the per-row existence checks are skipped
    entirely, saving N individual SELECT queries on every warm startup.
    Seed data is sourced from ``backend.app.constants.DEFAULT_HABITS``.

    Called once during application startup via the lifespan hook.
    """
    existing_count = db.query(models.Habit).count()
    if existing_count >= len(DEFAULT_HABITS):
        return  # Already seeded — skip all per-row checks

    existing_slugs: set[str] = {
        row[0] for row in db.query(models.Habit.slug).all()
    }
    for dh in DEFAULT_HABITS:
        if dh["slug"] not in existing_slugs:
            db.add(models.Habit(**dh))
    db.commit()


# ---------------------------------------------------------------------------
# List available habit types
# ---------------------------------------------------------------------------


@router.get("/list")
@limiter.limit("30/minute")
def list_available_habits(request: Request, db: Session = Depends(get_db)) -> dict:
    """Return the full habit catalogue with metadata."""
    habits = db.query(models.Habit).all()
    return {
        h.slug: {
            "name": h.name,
            "category": h.category,
            "points": h.points,
            "co2_saved": h.co2_saved,
        }
        for h in habits
    }


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
    • The habit key must exist in the database.
    • The same habit may only be logged once per calendar day.
    """
    habit_name = habit_in.habit_name
    habit = db.query(models.Habit).filter(models.Habit.slug == habit_name).first()
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown habit key: '{habit_name}'",
        )

    target_date = habit_in.logged_date or datetime.date.today()

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
            detail=f"You have already logged '{habit.name}' today!",
        )

    log = models.HabitsLog(
        user_id=current_user.id,
        habit_type=habit.category,
        habit_name=habit_name,
        co2_saved_kg=habit.co2_saved,
        points_earned=habit.points,
        logged_date=target_date,
    )
    db.add(log)

    # Update gamification counters in-memory before commit
    current_user.add_points(habit.points)

    db.commit()
    logger.info(
        "User '%s' logged habit '%s' — earned %d pts, now level %d.",
        current_user.username,
        habit_name,
        habit.points,
        current_user.level,
    )
    db.refresh(log)
    db.refresh(current_user)
    return log


# ---------------------------------------------------------------------------
# Dynamic Habit Management CRUD
# ---------------------------------------------------------------------------


@router.post("/", response_model=schemas.HabitResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_habit(
    request: Request,
    habit_in: schemas.HabitCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.Habit:
    """Create a new habit dynamically in the database."""
    existing = db.query(models.Habit).filter(models.Habit.slug == habit_in.slug).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Habit with slug '{habit_in.slug}' already exists.",
        )
    
    habit = models.Habit(
        slug=habit_in.slug,
        name=habit_in.name,
        category=habit_in.category,
        points=habit_in.points,
        co2_saved=habit_in.co2_saved,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return habit


@router.put("/{id}", response_model=schemas.HabitResponse)
@limiter.limit("10/minute")
def update_habit(
    request: Request,
    id: int,
    habit_in: schemas.HabitUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.Habit:
    """Update an existing habit in the database."""
    habit = db.query(models.Habit).filter(models.Habit.id == id).first()
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )
    
    if habit_in.name is not None:
        habit.name = habit_in.name
    if habit_in.category is not None:
        habit.category = habit_in.category
    if habit_in.points is not None:
        habit.points = habit_in.points
    if habit_in.co2_saved is not None:
        habit.co2_saved = habit_in.co2_saved
        
    db.commit()
    db.refresh(habit)
    return habit


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
def delete_habit(
    request: Request,
    id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a habit from the database."""
    habit = db.query(models.Habit).filter(models.Habit.id == id).first()
    if not habit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Habit not found",
        )

    db.delete(habit)
    db.commit()


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
