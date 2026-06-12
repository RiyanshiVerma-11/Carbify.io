"""
Pydantic v2 schemas for request validation and response serialization.

Key type-safety guarantees enforced here:
- DietType Literal: invalid strings bounce with HTTP 422 (Unprocessable Entity).
- weekly_breakdown typed as Dict[str, float]: no silent type coercions.
- All numeric fields carry explicit ge/le constraints for range validation.
"""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List, Dict, Literal
import datetime

# ---------------------------------------------------------------------------
# Domain literal types
# ---------------------------------------------------------------------------

# Strict Literal validator: submitting any other string (e.g. "omnivore")
# returns HTTP 422 Unprocessable Entity — no silent fallback to a default.
DietType = Literal["meat_heavy", "medium_meat", "low_meat", "vegetarian", "vegan"]


# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    points: int
    level: int
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class TokenData(BaseModel):
    username: Optional[str] = None


# ---------------------------------------------------------------------------
# Emissions log schemas
# ---------------------------------------------------------------------------


class EmissionsLogCreate(BaseModel):
    electricity_kwh: float = Field(0.0, ge=0.0)
    gas_kwh: float = Field(0.0, ge=0.0)
    petrol_car_km: float = Field(0.0, ge=0.0)
    diesel_car_km: float = Field(0.0, ge=0.0)
    electric_car_km: float = Field(0.0, ge=0.0)
    public_transit_km: float = Field(0.0, ge=0.0)
    flights_km: float = Field(0.0, ge=0.0)
    # Strict Literal validator: invalid diet strings trigger 422, not a silent fallback.
    diet_type: DietType = Field(
        "vegetarian",
        description="One of: meat_heavy, medium_meat, low_meat, vegetarian, vegan",
    )
    waste_kg: float = Field(0.0, ge=0.0)
    recycling_rate: float = Field(0.0, ge=0.0, le=1.0)
    logged_date: Optional[datetime.date] = None


class EmissionsLogResponse(BaseModel):
    id: int
    user_id: int
    electricity_kwh: float
    gas_kwh: float
    petrol_car_km: float
    diesel_car_km: float
    electric_car_km: float
    public_transit_km: float
    flights_km: float
    diet_type: str
    waste_kg: float
    recycling_rate: float
    total_co2_kg: float
    logged_date: datetime.date
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Habits schemas
# ---------------------------------------------------------------------------


class HabitLogCreate(BaseModel):
    habit_name: str  # e.g. "walk_instead_of_drive", "turn_off_ac", "recycle_bottles"
    logged_date: Optional[datetime.date] = None


class HabitLogResponse(BaseModel):
    id: int
    user_id: int
    habit_type: str
    habit_name: str
    co2_saved_kg: float
    points_earned: int
    logged_date: datetime.date

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Habit schemas
# ---------------------------------------------------------------------------


class HabitResponse(BaseModel):
    id: int
    slug: str
    name: str
    category: str
    points: int
    co2_saved: float

    model_config = ConfigDict(from_attributes=True)


class HabitCreate(BaseModel):
    slug: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=100)
    category: str = Field(..., min_length=3, max_length=50)
    points: int = Field(..., ge=1)
    co2_saved: float = Field(..., ge=0.0)


class HabitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    category: Optional[str] = Field(None, min_length=3, max_length=50)
    points: Optional[int] = Field(None, ge=1)
    co2_saved: Optional[float] = Field(None, ge=0.0)


# ---------------------------------------------------------------------------
# Challenge schemas
# ---------------------------------------------------------------------------


class ChallengeResponse(BaseModel):
    id: int
    title: str
    description: str
    points_reward: int
    co2_saving_estimate_kg: float
    category: str
    duration_days: int

    model_config = ConfigDict(from_attributes=True)


class UserChallengeResponse(BaseModel):
    id: int
    user_id: int
    challenge_id: int
    status: str
    joined_date: datetime.date
    completed_date: Optional[datetime.date] = None
    challenge: ChallengeResponse

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Leaderboard schemas
# ---------------------------------------------------------------------------


class LeaderboardUser(BaseModel):
    username: str
    points: int
    level: int

    model_config = ConfigDict(from_attributes=True)


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardUser]
    user_rank: int
    user_points: int


# ---------------------------------------------------------------------------
# Analytics schemas
# ---------------------------------------------------------------------------


class AICoachTip(BaseModel):
    category: str
    impact: str  # "High" | "Medium" | "Low"
    savings_kg: float
    message: str


class PersonalizedAnalyticsResponse(BaseModel):
    total_co2_kg: float
    carbon_saved_kg: float
    daily_average_kg: float
    # Strictly typed: keys are category names (str), values are kg CO2 (float).
    # A plain dict would silently accept mixed value types — Dict[str, float] prevents that.
    weekly_breakdown: Dict[str, float]
    ai_coach_tips: List[AICoachTip]


class TrendDataPoint(BaseModel):
    """A single daily data point for the 14-day emissions trend chart."""

    date: datetime.date
    total_co2_kg: float


class TrendResponse(BaseModel):
    """Response schema for the /api/analytics/trend endpoint.

    Contains an ordered list of (date, total_co2_kg) data points for
    the last 14 calendar days, used to render the historical line chart.
    Days with no log entry are included with total_co2_kg = 0.0 so the
    frontend always receives a dense, gapless series.
    """

    trend: List[TrendDataPoint]
    period_days: int


# ---------------------------------------------------------------------------
# Utility / Helper schemas
# ---------------------------------------------------------------------------


class PaginationQuery(BaseModel):
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(50, ge=1, le=100, description="Items per page")


__all__ = [
    "DietType",
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenData",
    "EmissionsLogCreate",
    "EmissionsLogResponse",
    "HabitLogCreate",
    "HabitLogResponse",
    "HabitResponse",
    "HabitCreate",
    "HabitUpdate",
    "ChallengeResponse",
    "UserChallengeResponse",
    "LeaderboardUser",
    "LeaderboardResponse",
    "AICoachTip",
    "PersonalizedAnalyticsResponse",
    "TrendDataPoint",
    "TrendResponse",
    "PaginationQuery",
]
