"""
backend/app/routes/challenges.py
─────────────────────────────────────────────────────────────
Eco-Challenge routes — browse, join, and complete challenges.

Endpoints
---------
GET   /api/challenges/list           – Paginated challenge catalogue.
GET   /api/challenges/user           – Enrolled challenges for current user.
POST  /api/challenges/{id}/join      – Enrol in a challenge.
POST  /api/challenges/{id}/complete  – Mark an active challenge complete.
"""

from __future__ import annotations

import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app import auth, models, schemas
from backend.app.constants import DEFAULT_CHALLENGES
from backend.app.database import get_db
from backend.app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/challenges", tags=["Challenges"])


def seed_challenges(db: Session) -> None:
    """Insert default challenges into the database if they don't already exist.

    Uses a count-first optimisation: if the table already contains the
    expected number of challenges, all per-row existence checks are skipped,
    saving N individual SELECT queries on every warm startup.
    Seed data is sourced from ``backend.app.constants.DEFAULT_CHALLENGES``.

    Called once during application startup via the lifespan hook.
    """
    existing_count = db.query(models.Challenge).count()
    if existing_count >= len(DEFAULT_CHALLENGES):
        return  # Already seeded — skip all per-row checks

    existing_titles: set[str] = {
        row[0] for row in db.query(models.Challenge.title).all()
    }
    for dc in DEFAULT_CHALLENGES:
        if dc["title"] not in existing_titles:
            db.add(models.Challenge(**dc))
    db.commit()


@router.get("/list", response_model=list[schemas.ChallengeResponse])
@limiter.limit("30/minute")
def get_challenges(
    request: Request,
    pagination: schemas.PaginationQuery = Depends(),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> list[models.Challenge]:
    """Return the paginated list of all available eco-challenges."""
    offset = (pagination.page - 1) * pagination.limit
    return (
        db.query(models.Challenge)
        .order_by(models.Challenge.id)
        .offset(offset)
        .limit(pagination.limit)
        .all()
    )


@router.get("/user", response_model=list[schemas.UserChallengeResponse])
@limiter.limit("30/minute")
def get_user_challenges(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> list[models.UserChallenge]:
    """Return all challenges the authenticated user has joined."""
    return (
        db.query(models.UserChallenge)
        .filter(models.UserChallenge.user_id == current_user.id)
        .all()
    )


@router.post("/{id}/join", response_model=schemas.UserChallengeResponse)
@limiter.limit("5/minute")
def join_challenge(
    request: Request,
    id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.UserChallenge:
    """Enrol the authenticated user in a challenge.

    Re-activates a previously abandoned challenge instead of creating
    a duplicate enrolment row.
    """
    # Check if challenge exists
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found",
        )

    # Check if user already joined
    existing = (
        db.query(models.UserChallenge)
        .filter(
            models.UserChallenge.user_id == current_user.id,
            models.UserChallenge.challenge_id == id,
        )
        .first()
    )

    if existing:
        if existing.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already joined this active challenge!",
            )
        elif existing.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed this challenge!",
            )
        else:
            # Re-activate if abandoned
            existing.status = "active"
            existing.joined_date = datetime.date.today()
            existing.completed_date = None
            db.commit()
            db.refresh(existing)
            return existing

    logger.info(
        "User '%s' successfully joined challenge '%s' (ID: %d)",
        current_user.username,
        challenge.title,
        id,
    )
    uc = models.UserChallenge(
        user_id=current_user.id,
        challenge_id=id,
        status="active",
    )
    db.add(uc)
    db.commit()
    db.refresh(uc)
    return uc


@router.post("/{id}/complete", response_model=schemas.UserChallengeResponse)
@limiter.limit("5/minute")
def complete_challenge(
    request: Request,
    id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.UserChallenge:
    """Mark an active challenge as completed and award the user eco-points."""
    uc = (
        db.query(models.UserChallenge)
        .filter(
            models.UserChallenge.user_id == current_user.id,
            models.UserChallenge.challenge_id == id,
        )
        .first()
    )

    if not uc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't joined this challenge yet!",
        )

    if uc.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge already completed!",
        )

    uc.status = "completed"
    uc.completed_date = datetime.date.today()

    # Award points
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    current_user.add_points(challenge.points_reward)

    db.commit()
    logger.info(
        "User '%s' completed challenge '%s' (ID: %d), earned %d points, level is now %d",
        current_user.username,
        challenge.title,
        id,
        challenge.points_reward,
        current_user.level,
    )
    db.refresh(uc)
    db.refresh(current_user)
    return uc
