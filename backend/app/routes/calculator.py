from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import datetime

from backend.app.database import get_db
from backend.app import models, schemas, auth
from backend.app.limiter import limiter
from backend.app.utils.calculations import calculate_co2_from_log
from backend.app.config import settings

router = APIRouter(prefix="/calculator", tags=["Carbon Calculator"])


@router.get("/constants")
@limiter.limit("30/minute")
def get_constants(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user)
) -> dict:
    return settings.EMISSION_FACTORS


@router.post("/log", response_model=schemas.EmissionsLogResponse)
@limiter.limit("20/minute")
def log_emissions(
    request: Request,
    log_in: schemas.EmissionsLogCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
) -> models.EmissionsLog:
    target_date = log_in.logged_date or datetime.date.today()
    
    # Check if a log already exists for this user on this day
    existing_log = db.query(models.EmissionsLog).filter(
        models.EmissionsLog.user_id == current_user.id,
        models.EmissionsLog.logged_date == target_date
    ).first()
    
    if existing_log:
        existing_log.electricity_kwh = log_in.electricity_kwh
        existing_log.gas_kwh = log_in.gas_kwh
        existing_log.petrol_car_km = log_in.petrol_car_km
        existing_log.diesel_car_km = log_in.diesel_car_km
        existing_log.electric_car_km = log_in.electric_car_km
        existing_log.public_transit_km = log_in.public_transit_km
        existing_log.flights_km = log_in.flights_km
        existing_log.diet_type = log_in.diet_type
        existing_log.waste_kg = log_in.waste_kg
        existing_log.recycling_rate = log_in.recycling_rate
        existing_log.total_co2_kg = calculate_co2_from_log(existing_log)
        db.commit()
        db.refresh(existing_log)
        return existing_log
    else:
        new_log = models.EmissionsLog(
            user_id=current_user.id,
            electricity_kwh=log_in.electricity_kwh,
            gas_kwh=log_in.gas_kwh,
            petrol_car_km=log_in.petrol_car_km,
            diesel_car_km=log_in.diesel_car_km,
            electric_car_km=log_in.electric_car_km,
            public_transit_km=log_in.public_transit_km,
            flights_km=log_in.flights_km,
            diet_type=log_in.diet_type,
            waste_kg=log_in.waste_kg,
            recycling_rate=log_in.recycling_rate,
            logged_date=target_date
        )
        new_log.total_co2_kg = calculate_co2_from_log(new_log)
        db.add(new_log)
        db.commit()
        db.refresh(new_log)
        return new_log

@router.get("/history", response_model=list[schemas.EmissionsLogResponse])
@limiter.limit("30/minute")
def get_history(
    request: Request,
    pagination: schemas.PaginationQuery = Depends(),
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
) -> list[models.EmissionsLog]:
    offset = (pagination.page - 1) * pagination.limit
    return db.query(models.EmissionsLog).filter(
        models.EmissionsLog.user_id == current_user.id
    ).order_by(models.EmissionsLog.logged_date.desc()).offset(offset).limit(pagination.limit).all()

@router.get("/latest", response_model=schemas.EmissionsLogResponse)
@limiter.limit("30/minute")
def get_latest(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
) -> models.EmissionsLog | dict:
    latest = db.query(models.EmissionsLog).filter(
        models.EmissionsLog.user_id == current_user.id
    ).order_by(models.EmissionsLog.logged_date.desc()).first()
    
    if not latest:
        # Return empty log default values
        return {
            "id": 0,
            "user_id": current_user.id,
            "electricity_kwh": 0.0,
            "gas_kwh": 0.0,
            "petrol_car_km": 0.0,
            "diesel_car_km": 0.0,
            "electric_car_km": 0.0,
            "public_transit_km": 0.0,
            "flights_km": 0.0,
            "diet_type": "vegetarian",
            "waste_kg": 0.0,
            "recycling_rate": 0.0,
            "total_co2_kg": 0.0,
            "logged_date": datetime.date.today(),
            "created_at": datetime.datetime.now(datetime.timezone.utc)
        }
    return latest
