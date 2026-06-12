"""
backend/app/models.py
─────────────────────────────────────────────────────────────
SQLAlchemy ORM models for Carbifyio.

Tables
------
users            – User accounts with gamification counters.
emissions_logs   – Daily carbon calculator snapshots.
habits_logs      – Per-day habit check-off records.
habits           – Catalogue of available green habits.
challenges       – Catalogue of gamified eco-challenges.
user_challenges  – Many-to-many join tracking challenge enrollment.
cache_entries    – Database-backed key/value cache with TTL.
"""

from __future__ import annotations

import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Date,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base

POINTS_PER_LEVEL: int = 100
"""Number of eco-points required to advance one level."""


class User(Base):
    """Registered user account with gamification state (points, level)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    created_at = Column(DateTime, default=func.now())

    emissions_logs = relationship(
        "EmissionsLog", back_populates="user", cascade="all, delete-orphan"
    )
    habits_logs = relationship(
        "HabitsLog", back_populates="user", cascade="all, delete-orphan"
    )
    challenges = relationship(
        "UserChallenge", back_populates="user", cascade="all, delete-orphan"
    )

    def add_points(self, points: int) -> None:
        """Add *points* and promote the user's level if a threshold is crossed."""
        self.points += points
        new_level = (self.points // POINTS_PER_LEVEL) + 1
        if new_level > self.level:
            self.level = new_level


class EmissionsLog(Base):
    """Single-day carbon footprint snapshot for a user."""

    __tablename__ = "emissions_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    electricity_kwh = Column(Float, default=0.0)
    gas_kwh = Column(Float, default=0.0)

    petrol_car_km = Column(Float, default=0.0)
    diesel_car_km = Column(Float, default=0.0)
    electric_car_km = Column(Float, default=0.0)
    public_transit_km = Column(Float, default=0.0)
    flights_km = Column(Float, default=0.0)

    # Values are constrained by the DietType Literal in schemas.py
    diet_type = Column(String, default="vegetarian")
    waste_kg = Column(Float, default=0.0)
    recycling_rate = Column(Float, default=0.0)  # 0.0–1.0

    total_co2_kg = Column(Float, default=0.0)
    logged_date = Column(Date, default=datetime.date.today, index=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="emissions_logs")

    # Composite index on (user_id, logged_date) — dominant query pattern.
    # Covers: history queries, latest-log lookups, and date-range filters.
    # The individual user_id index above is kept for FK-integrity checks.
    __table_args__ = (
        Index("ix_emissions_logs_user_id_logged_date", "user_id", "logged_date"),
    )


class HabitsLog(Base):
    """Record of a single habit logged by a user on a given day."""

    __tablename__ = "habits_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    habit_type = Column(String, nullable=False)  # transport, energy, food, waste
    habit_name = Column(String, nullable=False)  # e.g. "walk_instead_of_drive"
    co2_saved_kg = Column(Float, default=0.0)
    points_earned = Column(Integer, default=0)
    logged_date = Column(Date, default=datetime.date.today, index=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship("User", back_populates="habits_logs")

    # Composite index on (user_id, logged_date) — used by the Youden's J-stat
    # CTE query in analytics.py and the duplicate-habit-per-day guard in habits.py.
    __table_args__ = (
        Index("ix_habits_logs_user_id_logged_date", "user_id", "logged_date"),
    )


class Habit(Base):
    """Catalogue entry for a sustainable daily habit."""

    __tablename__ = "habits"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # transport, energy, food, waste
    points = Column(Integer, nullable=False)
    co2_saved = Column(Float, nullable=False)


class Challenge(Base):
    """Catalogue entry for a multi-day eco-challenge."""

    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=False)
    points_reward = Column(Integer, nullable=False)
    co2_saving_estimate_kg = Column(Float, default=0.0)
    category = Column(String, nullable=False)  # transport, energy, food, waste
    duration_days = Column(Integer, default=7)

    user_challenges = relationship(
        "UserChallenge", back_populates="challenge", cascade="all, delete-orphan"
    )


class UserChallenge(Base):
    """Many-to-many join tracking a user's enrollment in a challenge."""

    __tablename__ = "user_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge_id = Column(
        Integer, ForeignKey("challenges.id"), nullable=False, index=True
    )
    status = Column(String, default="active")  # active, completed, abandoned
    joined_date = Column(Date, default=datetime.date.today)
    completed_date = Column(Date, nullable=True)

    user = relationship("User", back_populates="challenges")
    challenge = relationship("Challenge", back_populates="user_challenges")


class CacheEntry(Base):
    """Database-backed key/value cache entry with a TTL expiry timestamp."""

    __tablename__ = "cache_entries"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)  # JSON-encoded string
    expires_at = Column(DateTime, nullable=False)


__all__ = [
    "POINTS_PER_LEVEL",
    "User",
    "EmissionsLog",
    "HabitsLog",
    "Habit",
    "Challenge",
    "UserChallenge",
    "CacheEntry",
]
