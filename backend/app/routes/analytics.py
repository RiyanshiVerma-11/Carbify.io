"""backend/app/routes/analytics.py
─────────────────────────────────────────────────────────────
Analytics, AI-Coach insights, and Leaderboard routes.

Endpoints
---------
GET  /api/analytics             – Personalised dashboard analytics.
GET  /api/analytics/trend       – 14-day historical CO₂ trend series.
GET  /api/analytics/leaderboard – Global eco-leaderboard (top 10).

Internal helpers
────────────────
db_cache_get / db_cache_set      – Database-backed key/value cache.
calculate_optimal_inactivity_threshold – Youden's J-statistic optimiser.
"""

import datetime
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import Integer, func
import sqlalchemy.exc
from sqlalchemy.orm import Session, aliased

from backend.app import auth, models
from backend.app.constants import (
    DEFAULT_INACTIVITY_THRESHOLD_DAYS,
    LEADERBOARD_CACHE_TTL_SECONDS,
    YOUDEN_CACHE_TTL_SECONDS,
)
from backend.app.database import get_db
from backend.app.limiter import limiter
from backend.app.schemas import (
    AICoachTip,
    LeaderboardResponse,
    LeaderboardUser,
    PersonalizedAnalyticsResponse,
    TrendDataPoint,
    TrendResponse,
)
from backend.app.utils.calculations import calculate_co2_breakdown_from_log

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics & Insights"])


# ---------------------------------------------------------------------------
# Database-backed cache helpers
# ---------------------------------------------------------------------------


def db_cache_get(db: Session, key: str) -> Any:
    """Return the cached value for *key*, or ``None`` if missing/expired."""
    try:
        now_utc = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        entry = (
            db.query(models.CacheEntry)
            .filter(
                models.CacheEntry.key == key,
                models.CacheEntry.expires_at > now_utc,
            )
            .first()
        )
        if entry:
            return json.loads(entry.value)
    except (sqlalchemy.exc.SQLAlchemyError, json.JSONDecodeError) as exc:
        logger.error("Error reading DB cache key '%s': %s", key, exc)
    return None


def db_cache_set(db: Session, key: str, value: Any, ttl_seconds: int) -> None:
    """Upsert a cache entry with a TTL-based expiry timestamp."""
    try:
        now_utc = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
        expires_at = now_utc + datetime.timedelta(seconds=ttl_seconds)
        val_str = json.dumps(value)

        # Check if entry exists
        entry = db.query(models.CacheEntry).filter(models.CacheEntry.key == key).first()
        if entry:
            entry.value = val_str
            entry.expires_at = expires_at
        else:
            entry = models.CacheEntry(key=key, value=val_str, expires_at=expires_at)
            db.add(entry)
        db.commit()
    except (sqlalchemy.exc.SQLAlchemyError, json.JSONDecodeError, TypeError) as exc:
        db.rollback()
        logger.error("Error setting DB cache key '%s': %s", key, exc)


# ---------------------------------------------------------------------------
# Youden's J-statistic threshold optimiser
# ---------------------------------------------------------------------------


def calculate_optimal_inactivity_threshold(db: Session) -> int:
    """Optimize the user inactivity alert threshold (in days) using Youden's J-statistic.

    ``J = Sensitivity + Specificity - 1``.

    OPTIMIZED — replaces O(users × logs) N+1 pattern with a single aggregate
    database query that computes consecutive habit-log date gaps using a
    self-join on a row-number window function.  SQLite and PostgreSQL both
    support the ROW_NUMBER() window syntax used here, making this portable.

    Caches the calculated threshold in the database-backed CacheEntry for 12 hours
    to prevent executing this table-scan CTE query on every single user request.
    """
    cached_threshold = db_cache_get(db, "youden_threshold")
    if cached_threshold is not None:
        return cached_threshold

    default_threshold = DEFAULT_INACTIVITY_THRESHOLD_DAYS
    try:
        # ── Step 1: check minimum user count before expensive work ───────────
        user_count = db.query(func.count(models.User.id)).scalar()
        if user_count < 3:
            return default_threshold

        # ── Step 2: single-query gap extraction via self-join on row_number ──
        subq = db.query(
            models.HabitsLog.user_id.label("user_id"),
            models.HabitsLog.logged_date.label("logged_date"),
            func.row_number()
            .over(
                partition_by=models.HabitsLog.user_id,
                order_by=models.HabitsLog.logged_date.desc(),
            )
            .label("rn"),
        ).subquery("ranked")

        a = aliased(subq, name="a")
        b = aliased(subq, name="b")

        # Database agnostic date math
        if db.get_bind().dialect.name == "sqlite":
            day_diff = func.abs(func.julianday(a.c.logged_date) - func.julianday(b.c.logged_date))
        else:
            day_diff = func.abs(a.c.logged_date - b.c.logged_date)

        gaps_query = (
            db.query(func.cast(day_diff, Integer))
            .join(b, (a.c.user_id == b.c.user_id) & (a.c.rn == b.c.rn - 1))
            .filter(a.c.logged_date != b.c.logged_date)
        )

        gaps: list[int] = [row[0] for row in gaps_query.all() if row[0] is not None]

        if not gaps:
            return default_threshold

        # ── Step 3: Youden's J-statistic across candidate thresholds ─────────
        # Ground-truth: gaps > 7 days are "truly inactive" periods.
        actual_inactive = [g for g in gaps if g > 7]
        actual_active = [g for g in gaps if g <= 7]

        if not actual_inactive or not actual_active:
            return default_threshold

        best_threshold = default_threshold
        max_j = -1.0

        for t in range(2, 11):
            tp = sum(1 for g in actual_inactive if g >= t)
            fn = sum(1 for g in actual_inactive if g < t)
            tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0

            tn = sum(1 for g in actual_active if g < t)
            fp = sum(1 for g in actual_active if g >= t)
            tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0

            j = tpr + tnr - 1.0
            if j > max_j:
                max_j = j
                best_threshold = t

        # Cache the calculated optimal threshold for 12 hours
        db_cache_set(db, "youden_threshold", best_threshold, ttl_seconds=YOUDEN_CACHE_TTL_SECONDS)
        return best_threshold

    except sqlalchemy.exc.SQLAlchemyError as exc:
        logger.error("Error calculating Youden's J-statistic threshold: %s", exc)
        return default_threshold


# ---------------------------------------------------------------------------
# Personalised analytics endpoint
# ---------------------------------------------------------------------------


@router.get("", response_model=PersonalizedAnalyticsResponse)
@limiter.limit("15/minute")
def get_analytics(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> PersonalizedAnalyticsResponse:
    """Return personalised analytics for the authenticated user.

    Includes total CO₂, carbon saved via habits, per-category breakdown,
    and AI Coach tips tailored to the user's emission profile.
    """
    # Retrieve latest emissions log for the authenticated user
    latest_log = (
        db.query(models.EmissionsLog)
        .filter(models.EmissionsLog.user_id == current_user.id)
        .order_by(models.EmissionsLog.logged_date.desc())
        .first()
    )

    # Aggregate total carbon saved via habits in a single DB query
    total_saved_result = (
        db.query(func.sum(models.HabitsLog.co2_saved_kg))
        .filter(models.HabitsLog.user_id == current_user.id)
        .scalar()
    )
    carbon_saved_kg = round(float(total_saved_result or 0.0), 2)

    # No log yet — return zeroed-out response with a welcome tip
    if not latest_log:
        return PersonalizedAnalyticsResponse(
            total_co2_kg=0.0,
            carbon_saved_kg=carbon_saved_kg,
            daily_average_kg=0.0,
            weekly_breakdown={
                "energy": 0.0,
                "transport": 0.0,
                "food": 0.0,
                "waste": 0.0,
            },
            ai_coach_tips=[
                AICoachTip(
                    category="general",
                    impact="Medium",
                    savings_kg=5.0,
                    message=(
                        "Welcome to Carbifyio! Complete your Carbon Calculator log "
                        "to receive tailored coach suggestions."
                    ),
                ),
            ],
        )

    # ── Use the shared utility for breakdown — no duplicated factor math ────
    weekly_breakdown: dict[str, float] = calculate_co2_breakdown_from_log(latest_log)
    total_co2 = round(sum(weekly_breakdown.values()), 2)

    # ── AI Coach Tips ────────────────────────────────────────────────────────
    tips: list[AICoachTip] = _build_coach_tips(latest_log, weekly_breakdown, db)

    return PersonalizedAnalyticsResponse(
        total_co2_kg=total_co2,
        carbon_saved_kg=carbon_saved_kg,
        daily_average_kg=round(total_co2, 2),
        weekly_breakdown=weekly_breakdown,
        ai_coach_tips=tips,
    )


def _build_coach_tips(
    latest_log: models.EmissionsLog,
    weekly_breakdown: dict[str, float],
    db: Session,
) -> list[AICoachTip]:
    """Assemble a list of AI Coach tips based on the user's emission profile.

    The tip-generation logic analyses the dominant emission category and
    supplements with contextual suggestions until at least one tip is present.
    """
    tips: list[AICoachTip] = []

    # Calculate optimal inactivity threshold using Youden's J-statistic
    optimal_gap_threshold = calculate_optimal_inactivity_threshold(db)

    # Alert if the user has been inactive longer than the optimised threshold
    days_since_last_log = (datetime.date.today() - latest_log.logged_date).days
    if days_since_last_log >= optimal_gap_threshold:
        tips.append(
            AICoachTip(
                category="general",
                impact="High",
                savings_kg=7.5,
                message=(
                    f"Engagement Alert: It has been {days_since_last_log} days since "
                    f"your last log. Dynamic threshold optimization (Youden's J-statistic "
                    f"optimal threshold = {optimal_gap_threshold} days) indicates logging "
                    f"today will help you stay on track and avoid green habit churn!"
                ),
            ),
        )

    # Sort categories to surface the dominant emission source
    sorted_categories = sorted(weekly_breakdown.items(), key=lambda x: x[1], reverse=True)
    highest_cat, highest_val = sorted_categories[0]

    if highest_cat == "transport" and highest_val > 0:
        tips.append(
            AICoachTip(
                category="transport",
                impact="High",
                savings_kg=10.5,
                message=(
                    "Transport is your biggest source of emissions. Shifting 30 km of "
                    "single-occupancy petrol car commuting to public transit or cycling "
                    "this week will save over 10 kg CO2!"
                ),
            ),
        )
    elif highest_cat == "energy" and highest_val > 0:
        tips.append(
            AICoachTip(
                category="energy",
                impact="High",
                savings_kg=8.0,
                message=(
                    "Energy usage at home is dominant. Lowering your heating/cooling "
                    "by 2°C or using solar energy could save up to 8 kg CO2 per day."
                ),
            ),
        )
    elif highest_cat == "food":
        if latest_log.diet_type in ("meat_heavy", "medium_meat"):
            tips.append(
                AICoachTip(
                    category="food",
                    impact="High",
                    savings_kg=4.3,
                    message=(
                        "Your diet has high emissions. Shifting to vegetarian or vegan "
                        "options just twice a week will save 4.3 kg CO2."
                    ),
                ),
            )
        else:
            tips.append(
                AICoachTip(
                    category="food",
                    impact="Medium",
                    savings_kg=1.8,
                    message=(
                        "Great work maintaining a low-carbon diet! Sharing your "
                        "eco-friendly recipes with others can expand your positive impact."
                    ),
                ),
            )
    elif highest_cat == "waste" and highest_val > 0:
        tips.append(
            AICoachTip(
                category="waste",
                impact="Medium",
                savings_kg=3.5,
                message=(
                    "Reducing waste footprint. Try composting organic waste and avoiding "
                    "plastic wrap. Increasing your recycling rate to 80% saves ~3.5 kg CO2."
                ),
            ),
        )

    # Supplementary tips when the list is still short
    if len(tips) < 3:
        if latest_log.electricity_kwh > 10:
            tips.append(
                AICoachTip(
                    category="energy",
                    impact="Medium",
                    savings_kg=1.2,
                    message=(
                        "Turn off AC units and log 'Turned off AC/heating' in the "
                        "Habits tab to earn 15 Eco-points!"
                    ),
                ),
            )
        if latest_log.petrol_car_km > 20:
            tips.append(
                AICoachTip(
                    category="transport",
                    impact="Medium",
                    savings_kg=1.5,
                    message=(
                        "Log 'Walked/cycled instead of driving' to earn 20 Eco-points "
                        "and offset your transport emissions."
                    ),
                ),
            )
        # Safety net: always provide at least one actionable tip
        if not tips:
            tips.append(
                AICoachTip(
                    category="general",
                    impact="Low",
                    savings_kg=1.0,
                    message=(
                        "Explore new habits in the habits dashboard to unlock carbon "
                        "reductions and score more points."
                    ),
                ),
            )

    return tips


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


@router.get("/leaderboard", response_model=LeaderboardResponse)
@limiter.limit("15/minute")
def get_leaderboard(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> LeaderboardResponse:
    """Return the global eco-leaderboard (top 10) and the current user's rank.

    Results are cached in the database for 60 seconds to prevent full-table
    scans on every request.
    """
    cached_data = db_cache_get(db, "leaderboard")

    if cached_data is None:
        # Only the top-10 rows are fetched — avoids full-table scan
        top_users = db.query(models.User).order_by(models.User.points.desc()).limit(10).all()
        cached_data = [
            {"username": u.username, "points": u.points, "level": u.level} for u in top_users
        ]
        db_cache_set(db, "leaderboard", cached_data, ttl_seconds=LEADERBOARD_CACHE_TTL_SECONDS)

    leaderboard = [
        LeaderboardUser(
            username=entry["username"],
            points=entry["points"],
            level=entry["level"],
        )
        for entry in cached_data
    ]

    # Efficient rank: count users with strictly more points + 1
    user_rank = db.query(models.User).filter(models.User.points > current_user.points).count() + 1

    return LeaderboardResponse(
        leaderboard=leaderboard,
        user_rank=user_rank,
        user_points=current_user.points,
    )


# ---------------------------------------------------------------------------
# 14-day Emissions Trend
# ---------------------------------------------------------------------------


@router.get("/trend", response_model=TrendResponse)
@limiter.limit("15/minute")
def get_trend(
    request: Request,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
) -> TrendResponse:
    """Return a gapless 14-day daily CO₂ trend series for the authenticated user.

    Each element of ``trend`` represents one calendar day.  Days with no
    emissions log entry are zero-filled so the frontend always receives a
    dense, continuous series suitable for a line chart without date-gap logic.

    The response is NOT cached (per-user data, tiny query) — 14 rows max.
    """
    today = datetime.date.today()
    period_days = 14
    start_date = today - datetime.timedelta(days=period_days - 1)

    # Fetch only rows within the 14-day window — at most 14 rows per user
    logs = (
        db.query(models.EmissionsLog.logged_date, models.EmissionsLog.total_co2_kg)
        .filter(
            models.EmissionsLog.user_id == current_user.id,
            models.EmissionsLog.logged_date >= start_date,
            models.EmissionsLog.logged_date <= today,
        )
        .order_by(models.EmissionsLog.logged_date.asc())
        .all()
    )

    # Build a date → co2 lookup for O(1) access during the dense-fill pass
    log_map: dict[datetime.date, float] = {row[0]: round(row[1], 2) for row in logs}

    # Generate a gapless series — every day in the window, zero when no log
    trend: list[TrendDataPoint] = [
        TrendDataPoint(
            date=start_date + datetime.timedelta(days=i),
            total_co2_kg=log_map.get(start_date + datetime.timedelta(days=i), 0.0),
        )
        for i in range(period_days)
    ]

    return TrendResponse(trend=trend, period_days=period_days)
