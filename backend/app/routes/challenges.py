from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app import models, schemas, auth
from backend.app.limiter import limiter
import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/challenges", tags=["Challenges"])

DEFAULT_CHALLENGES = [
    {
        "title": "Eco Commuter",
        "description": "Commute using public transit, bike, or walking for 5 consecutive days.",
        "points_reward": 50,
        "co2_saving_estimate_kg": 10.0,
        "category": "transport",
        "duration_days": 7
    },
    {
        "title": "Unplugged Weekend",
        "description": "Power down non-essential electronics and appliances for 48 hours.",
        "points_reward": 30,
        "co2_saving_estimate_kg": 3.5,
        "category": "energy",
        "duration_days": 2
    },
    {
        "title": "Plant Power",
        "description": "Eat only plant-based/vegan meals for 3 consecutive days.",
        "points_reward": 40,
        "co2_saving_estimate_kg": 8.0,
        "category": "food",
        "duration_days": 3
    },
    {
        "title": "Zero-Waste Champ",
        "description": "Avoid all single-use plastics and recycle 100% of recyclable waste for 5 days.",
        "points_reward": 40,
        "co2_saving_estimate_kg": 5.0,
        "category": "waste",
        "duration_days": 5
    },
    {
        "title": "Eco Shower",
        "description": "Limit all showers to under 5 minutes for a full week.",
        "points_reward": 25,
        "co2_saving_estimate_kg": 2.5,
        "category": "energy",
        "duration_days": 7
    }
]

def seed_challenges(db: Session):
    for dc in DEFAULT_CHALLENGES:
        exists = db.query(models.Challenge).filter(models.Challenge.title == dc["title"]).first()
        if not exists:
            db.add(models.Challenge(**dc))
    db.commit()

@router.get("/list", response_model=list[schemas.ChallengeResponse])
@limiter.limit("30/minute")
def get_challenges(
    request: Request,
    pagination: schemas.PaginationQuery = Depends(),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
) -> list[models.Challenge]:
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
    db: Session = Depends(get_db)
) -> list[models.UserChallenge]:
    return db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id
    ).all()

@router.post("/{id}/join", response_model=schemas.UserChallengeResponse)
@limiter.limit("5/minute")
def join_challenge(
    request: Request,
    id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
) -> models.UserChallenge:
    # Check if challenge exists
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Challenge not found"
        )
    
    # Check if user already joined
    existing = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if existing:
        if existing.status == "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already joined this active challenge!"
            )
        elif existing.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed this challenge!"
            )
        else:
            # Re-activate it if abandoned
            existing.status = "active"
            existing.joined_date = datetime.date.today()
            existing.completed_date = None
            db.commit()
            db.refresh(existing)
            return existing
            
    logger.info(
        "User '%s' successfully joined challenge '%s' (ID: %d)",
        current_user.username, challenge.title, id,
    )
    uc = models.UserChallenge(
        user_id=current_user.id,
        challenge_id=id,
        status="active"
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
    db: Session = Depends(get_db)
) -> models.UserChallenge:
    uc = db.query(models.UserChallenge).filter(
        models.UserChallenge.user_id == current_user.id,
        models.UserChallenge.challenge_id == id
    ).first()
    
    if not uc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You haven't joined this challenge yet!"
        )
        
    if uc.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge already completed!"
        )
        
    uc.status = "completed"
    uc.completed_date = datetime.date.today()
    
    # Award points
    challenge = db.query(models.Challenge).filter(models.Challenge.id == id).first()
    current_user.add_points(challenge.points_reward)
        
    db.commit()
    logger.info(
        "User '%s' completed challenge '%s' (ID: %d), earned %d points, level is now %d",
        current_user.username, challenge.title, id,
        challenge.points_reward, current_user.level,
    )
    db.refresh(uc)
    db.refresh(current_user)
    return uc
