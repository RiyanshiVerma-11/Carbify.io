"""backend/app/models.py
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
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base

POINTS_PER_LEVEL: int = 100
"""Number of eco-points required to advance one level."""


class User(Base):
    """Registered user account with gamification state (points, level)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0)
    level: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    emissions_logs: Mapped[list[EmissionsLog]] = relationship(
        "EmissionsLog", back_populates="user", cascade="all, delete-orphan",
    )
    habits_logs: Mapped[list[HabitsLog]] = relationship("HabitsLog", back_populates="user", cascade="all, delete-orphan")
    challenges: Mapped[list[UserChallenge]] = relationship("UserChallenge", back_populates="user", cascade="all, delete-orphan")

    def add_points(self, points: int) -> None:
        """Add *points* and promote the user's level if a threshold is crossed."""
        self.points += points
        new_level = (self.points // POINTS_PER_LEVEL) + 1
        self.level = max(self.level, new_level)


class EmissionsLog(Base):
    """Single-day carbon footprint snapshot for a user."""

    __tablename__ = "emissions_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    electricity_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    gas_kwh: Mapped[float] = mapped_column(Float, default=0.0)

    petrol_car_km: Mapped[float] = mapped_column(Float, default=0.0)
    diesel_car_km: Mapped[float] = mapped_column(Float, default=0.0)
    electric_car_km: Mapped[float] = mapped_column(Float, default=0.0)
    public_transit_km: Mapped[float] = mapped_column(Float, default=0.0)
    flights_km: Mapped[float] = mapped_column(Float, default=0.0)

    # Values are constrained by the DietType Literal in schemas.py
    diet_type: Mapped[str] = mapped_column(String, default="vegetarian")
    waste_kg: Mapped[float] = mapped_column(Float, default=0.0)
    recycling_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0–1.0

    total_co2_kg: Mapped[float] = mapped_column(Float, default=0.0)
    logged_date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[User] = relationship("User", back_populates="emissions_logs")

    # Composite index on (user_id, logged_date) — dominant query pattern.
    # Covers: history queries, latest-log lookups, and date-range filters.
    # The individual user_id index above is kept for FK-integrity checks.
    __table_args__ = (Index("ix_emissions_logs_user_id_logged_date", "user_id", "logged_date"),)


class HabitsLog(Base):
    """Record of a single habit logged by a user on a given day."""

    __tablename__ = "habits_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    habit_type: Mapped[str] = mapped_column(String, nullable=False)  # transport, energy, food, waste
    habit_name: Mapped[str] = mapped_column(String, nullable=False)  # e.g. "walk_instead_of_drive"
    co2_saved_kg: Mapped[float] = mapped_column(Float, default=0.0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    logged_date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now())

    user: Mapped[User] = relationship("User", back_populates="habits_logs")

    # Composite index on (user_id, logged_date) — used by the Youden's J-stat
    # CTE query in analytics.py and the duplicate-habit-per-day guard in habits.py.
    __table_args__ = (Index("ix_habits_logs_user_id_logged_date", "user_id", "logged_date"),)


class Habit(Base):
    """Catalogue entry for a sustainable daily habit."""

    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)  # transport, energy, food, waste
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    co2_saved: Mapped[float] = mapped_column(Float, nullable=False)


class Challenge(Base):
    """Catalogue entry for a multi-day eco-challenge."""

    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String, nullable=False)
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False)
    co2_saving_estimate_kg: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String, nullable=False)  # transport, energy, food, waste
    duration_days: Mapped[int] = mapped_column(Integer, default=7)

    user_challenges: Mapped[list[UserChallenge]] = relationship(
        "UserChallenge", back_populates="challenge", cascade="all, delete-orphan",
    )


class UserChallenge(Base):
    """Many-to-many join tracking a user's enrollment in a challenge."""

    __tablename__ = "user_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    challenge_id: Mapped[int] = mapped_column(Integer, ForeignKey("challenges.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, default="active")  # active, completed, abandoned
    joined_date: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    completed_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)

    user: Mapped[User] = relationship("User", back_populates="challenges")
    challenge: Mapped[Challenge] = relationship("Challenge", back_populates="user_challenges")


class CacheEntry(Base):
    """Database-backed key/value cache entry with a TTL expiry timestamp."""

    __tablename__ = "cache_entries"

    key: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False)  # JSON-encoded string
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)


__all__ = [
    "POINTS_PER_LEVEL",
    "CacheEntry",
    "Challenge",
    "EmissionsLog",
    "Habit",
    "HabitsLog",
    "User",
    "UserChallenge",
]
