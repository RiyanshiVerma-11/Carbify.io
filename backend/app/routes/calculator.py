"""
backend/app/routes/calculator.py
─────────────────────────────────────────────────────────────
Carbon Calculator routes — log, retrieve, and inspect emissions data.

Endpoints
---------
GET  /api/calculator/constants  – Return emission factors.
POST /api/calculator/log        – Create or update a daily emissions log.
GET  /api/calculator/history    – Paginated history of logs.
GET  /api/calculator/latest     – Most recent log entry.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

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
    current_user: models.User = Depends(auth.get_current_user),
) -> dict:
    """Return the canonical emission-factor constants used by the calculator.

    The factors are sourced from ``settings.EMISSION_FACTORS`` and exposed
    so the frontend can perform matching client-side live-preview calculations.
    """
    return settings.EMISSION_FACTORS


def _update_existing_log(
    existing_log: models.EmissionsLog,
    log_in: schemas.EmissionsLogCreate,
    db: Session,
) -> models.EmissionsLog:
    """Apply new field values from *log_in* to *existing_log*, re-calculate
    total CO₂, commit, and return the refreshed ORM instance."""
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


@router.post("/log", response_model=schemas.EmissionsLogResponse)
@limiter.limit("20/minute")
def log_emissions(
    request: Request,
    log_in: schemas.EmissionsLogCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.EmissionsLog:
    """Create or update the emissions log for the authenticated user's target date.

    If a log already exists for that calendar day, the existing row is updated
    in-place (upsert pattern) to enforce single-log-per-day integrity.
    """
    target_date = log_in.logged_date or datetime.date.today()

    # Check if a log already exists for this user on this day
    existing_log = (
        db.query(models.EmissionsLog)
        .filter(
            models.EmissionsLog.user_id == current_user.id,
            models.EmissionsLog.logged_date == target_date,
        )
        .first()
    )

    if existing_log:
        return _update_existing_log(existing_log, log_in, db)

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
        logged_date=target_date,
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
    db: Session = Depends(get_db),
) -> list[models.EmissionsLog]:
    """Return the authenticated user's emissions log history, newest first.

    Supports cursor-style pagination via ``page`` and ``limit`` query params.
    """
    offset = (pagination.page - 1) * pagination.limit
    return (
        db.query(models.EmissionsLog)
        .filter(models.EmissionsLog.user_id == current_user.id)
        .order_by(models.EmissionsLog.logged_date.desc())
        .offset(offset)
        .limit(pagination.limit)
        .all()
    )


@router.get("/latest", response_model=schemas.EmissionsLogResponse)
@limiter.limit("30/minute")
def get_latest(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> models.EmissionsLog | schemas.EmissionsLogResponse:
    """Return the most recent emissions log for the authenticated user.

    If no log exists yet, a zeroed-out ``EmissionsLogResponse`` is returned so
    the frontend always receives a valid, typed response — no raw dict escape
    hatch. This preserves the Pydantic ``response_model`` contract.
    """
    latest = (
        db.query(models.EmissionsLog)
        .filter(models.EmissionsLog.user_id == current_user.id)
        .order_by(models.EmissionsLog.logged_date.desc())
        .first()
    )

    if not latest:
        # Return a zeroed-out default using the typed response schema —
        # avoids the unsafe `| dict` return type escape hatch.
        return schemas.EmissionsLogResponse(
            id=0,
            user_id=current_user.id,
            electricity_kwh=0.0,
            gas_kwh=0.0,
            petrol_car_km=0.0,
            diesel_car_km=0.0,
            electric_car_km=0.0,
            public_transit_km=0.0,
            flights_km=0.0,
            diet_type="vegetarian",
            waste_kg=0.0,
            recycling_rate=0.0,
            total_co2_kg=0.0,
            logged_date=datetime.date.today(),
            created_at=datetime.datetime.now(datetime.timezone.utc),
        )
    return latest
