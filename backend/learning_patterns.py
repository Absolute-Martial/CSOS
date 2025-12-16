"""
Personal Engineering OS - Learning Pattern Tracking System
Tracks and learns from user study patterns to make adaptive recommendations
"""

from datetime import datetime, date, time, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from database import db
from enum import Enum
import statistics


# ============================================
# ENUMS AND MODELS
# ============================================

class TimeOfDay(str, Enum):
    """Time of day categories for pattern analysis"""
    EARLY_MORNING = "early_morning"  # 5-8 AM
    MORNING = "morning"              # 8-12 PM
    AFTERNOON = "afternoon"          # 12-5 PM
    EVENING = "evening"              # 5-9 PM
    NIGHT = "night"                  # 9 PM - 12 AM
    LATE_NIGHT = "late_night"        # 12-5 AM


class DayOfWeek(str, Enum):
    """Day of week for weekly pattern analysis"""
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class LearningPattern(BaseModel):
    """Represents learned study pattern for a subject or overall"""
    subject_code: Optional[str] = None  # None = overall pattern
    avg_session_duration_mins: int = Field(default=45, description="Average study session length")
    best_study_time: TimeOfDay = Field(default=TimeOfDay.MORNING)
    best_day_of_week: Optional[DayOfWeek] = None
    retention_rate: float = Field(default=0.7, ge=0.0, le=1.0)
    preferred_session_length: int = Field(default=45, description="Optimal session length in minutes")
    break_frequency_mins: int = Field(default=60, description="Recommended break interval")
    effectiveness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    deep_work_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of deep work sessions")
    samples_count: int = Field(default=0, description="Number of sessions analyzed")
    last_updated: Optional[datetime] = None


class SessionEffectiveness(BaseModel):
    """Effectiveness data for a completed study session"""
    session_id: int
    subject_code: Optional[str] = None
    time_of_day: TimeOfDay
    day_of_week: DayOfWeek
    duration_mins: int
    focus_score: float = Field(ge=0.0, le=1.0, description="Focus quality 0-1")
    material_covered: Optional[str] = None
    retention_test_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    is_deep_work: bool = False
    energy_level: Optional[int] = Field(default=None, ge=1, le=10)


class StudyRecommendation(BaseModel):
    """A personalized study recommendation"""
    recommendation_type: str  # 'schedule', 'duration', 'subject_order', 'break', 'time_of_day', 'energy'
    recommendation_text: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    priority: int = Field(default=5, ge=1, le=10)
    context: Dict[str, Any] = Field(default_factory=dict)


class HourlyProductivity(BaseModel):
    """Productivity metrics by hour of day"""
    hour: int
    session_count: int
    avg_duration_mins: float
    avg_focus_score: float
    deep_work_rate: float


# ============================================
# PATTERN ANALYZER
# ============================================

class PatternAnalyzer:
    """Analyzes study patterns from historical session data"""

    @staticmethod
    def get_time_of_day(dt: datetime) -> TimeOfDay:
        """Determine time of day category from datetime"""
        hour = dt.hour
        if 5 <= hour < 8:
            return TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        elif 21 <= hour < 24:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.LATE_NIGHT

    @staticmethod
    def get_day_of_week(dt: datetime) -> DayOfWeek:
        """Get day of week from datetime"""
        days = [
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY, DayOfWeek.SUNDAY
        ]
        return days[dt.weekday()]

    @staticmethod
    def calculate_confidence(samples: int, base_confidence: float = 0.5) -> float:
        """Calculate confidence score based on sample size"""
        # Confidence increases logarithmically with samples
        # 5 samples: ~0.6, 20 samples: ~0.75, 50 samples: ~0.85, 100+: ~0.9
        if samples == 0:
            return 0.3
        import math
        confidence = base_confidence + (0.4 * math.log10(samples + 1) / 2)
        return min(0.95, confidence)

    async def analyze_patterns(self, subject_code: Optional[str] = None) -> LearningPattern:
        """Analyze learning patterns from historical sessions"""

        # First check if we have cached patterns
        cached = await self._get_cached_pattern(subject_code)
        if cached and cached.get('samples_count', 0) > 0:
            # If cache is recent (within 24 hours), use it
            updated = cached.get('updated_at')
            if updated and (datetime.now() - updated).total_seconds() < 86400:
                return LearningPattern(
                    subject_code=cached.get('subject_code'),
                    avg_session_duration_mins=cached.get('avg_session_duration_mins', 45),
                    best_study_time=TimeOfDay(cached.get('best_study_time', 'morning')),
                    best_day_of_week=DayOfWeek(cached['best_day_of_week']) if cached.get('best_day_of_week') else None,
                    retention_rate=cached.get('retention_rate', 0.7),
                    preferred_session_length=cached.get('preferred_session_length', 45),
                    break_frequency_mins=cached.get('break_frequency_mins', 60),
                    effectiveness_score=cached.get('effectiveness_score', 0.5),
                    deep_work_ratio=cached.get('deep_work_ratio', 0.0),
                    samples_count=cached.get('samples_count', 0),
                    last_updated=updated
                )

        # Analyze from raw session data
        if subject_code:
            sessions = await db.fetch("""
                SELECT
                    ss.*,
                    se.focus_score,
                    se.time_of_day as recorded_time_of_day,
                    se.energy_level,
                    s.code as subject_code
                FROM study_sessions ss
                LEFT JOIN session_effectiveness se ON ss.id = se.session_id
                LEFT JOIN subjects s ON ss.subject_id = s.id
                WHERE s.code = $1 AND ss.stopped_at IS NOT NULL
                ORDER BY ss.started_at DESC
                LIMIT 100
            """, subject_code)
        else:
            sessions = await db.fetch("""
                SELECT
                    ss.*,
                    se.focus_score,
                    se.time_of_day as recorded_time_of_day,
                    se.energy_level,
                    s.code as subject_code
                FROM study_sessions ss
                LEFT JOIN session_effectiveness se ON ss.id = se.session_id
                LEFT JOIN subjects s ON ss.subject_id = s.id
                WHERE ss.stopped_at IS NOT NULL
                ORDER BY ss.started_at DESC
                LIMIT 200
            """)

        if not sessions:
            return self._default_pattern(subject_code)

        # Collect metrics
        time_effectiveness: Dict[TimeOfDay, List[float]] = {}
        day_effectiveness: Dict[DayOfWeek, List[float]] = {}
        durations: List[float] = []
        focus_scores: List[float] = []
        deep_work_count = 0
        valid_sessions = 0

        for session in sessions:
            duration = (session['duration_seconds'] or 0) / 60
            if duration < 5:  # Skip very short sessions
                continue

            valid_sessions += 1
            durations.append(duration)

            # Get time of day
            time_of_day = (
                TimeOfDay(session['recorded_time_of_day'])
                if session.get('recorded_time_of_day')
                else self.get_time_of_day(session['started_at'])
            )

            # Get day of week
            day_of_week = self.get_day_of_week(session['started_at'])

            # Get focus score (default based on duration and deep work status)
            if session.get('focus_score'):
                focus = session['focus_score']
            elif session.get('is_deep_work'):
                focus = 0.85
            elif duration >= 45:
                focus = 0.7
            else:
                focus = 0.6

            focus_scores.append(focus)

            # Track time of day effectiveness
            if time_of_day not in time_effectiveness:
                time_effectiveness[time_of_day] = []
            time_effectiveness[time_of_day].append(focus)

            # Track day of week effectiveness
            if day_of_week not in day_effectiveness:
                day_effectiveness[day_of_week] = []
            day_effectiveness[day_of_week].append(focus)

            # Count deep work sessions
            if session.get('is_deep_work'):
                deep_work_count += 1

        if valid_sessions == 0:
            return self._default_pattern(subject_code)

        # Find best time of day
        best_time = TimeOfDay.MORNING
        best_time_score = 0
        for tod, scores in time_effectiveness.items():
            if len(scores) >= 2:  # Need at least 2 samples
                avg = statistics.mean(scores)
                if avg > best_time_score:
                    best_time_score = avg
                    best_time = tod

        # Find best day of week
        best_day = None
        best_day_score = 0
        for dow, scores in day_effectiveness.items():
            if len(scores) >= 2:
                avg = statistics.mean(scores)
                if avg > best_day_score:
                    best_day_score = avg
                    best_day = dow

        # Calculate preferred session length (weighted toward successful sessions)
        successful_durations = [
            d for d, f in zip(durations, focus_scores)
            if f >= 0.6
        ]
        if successful_durations:
            # Use median for robustness against outliers
            preferred_length = int(statistics.median(successful_durations))
            # Clamp to reasonable range
            preferred_length = max(25, min(120, preferred_length))
        else:
            preferred_length = 45

        # Calculate break frequency
        break_freq = await self._analyze_break_patterns(subject_code)

        # Overall effectiveness
        effectiveness = statistics.mean(focus_scores) if focus_scores else 0.5

        # Deep work ratio
        deep_work_ratio = deep_work_count / valid_sessions if valid_sessions > 0 else 0.0

        pattern = LearningPattern(
            subject_code=subject_code,
            avg_session_duration_mins=int(statistics.mean(durations)) if durations else 45,
            best_study_time=best_time,
            best_day_of_week=best_day,
            retention_rate=0.7,  # Would need quiz data for accurate calculation
            preferred_session_length=preferred_length,
            break_frequency_mins=break_freq,
            effectiveness_score=round(effectiveness, 3),
            deep_work_ratio=round(deep_work_ratio, 3),
            samples_count=valid_sessions,
            last_updated=datetime.now()
        )

        # Cache the pattern
        await self._cache_pattern(pattern)

        return pattern

    async def _get_cached_pattern(self, subject_code: Optional[str]) -> Optional[dict]:
        """Get cached pattern from database"""
        if subject_code:
            return await db.fetch_one(
                "SELECT * FROM learning_patterns WHERE subject_code = $1",
                subject_code
            )
        else:
            return await db.fetch_one(
                "SELECT * FROM learning_patterns WHERE subject_code IS NULL"
            )

    async def _cache_pattern(self, pattern: LearningPattern) -> None:
        """Cache pattern to database"""
        await db.execute("""
            INSERT INTO learning_patterns
            (subject_code, avg_session_duration_mins, best_study_time, best_day_of_week,
             retention_rate, preferred_session_length, break_frequency_mins,
             effectiveness_score, deep_work_ratio, samples_count, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
            ON CONFLICT (subject_code) DO UPDATE SET
                avg_session_duration_mins = EXCLUDED.avg_session_duration_mins,
                best_study_time = EXCLUDED.best_study_time,
                best_day_of_week = EXCLUDED.best_day_of_week,
                retention_rate = EXCLUDED.retention_rate,
                preferred_session_length = EXCLUDED.preferred_session_length,
                break_frequency_mins = EXCLUDED.break_frequency_mins,
                effectiveness_score = EXCLUDED.effectiveness_score,
                deep_work_ratio = EXCLUDED.deep_work_ratio,
                samples_count = EXCLUDED.samples_count,
                updated_at = NOW()
        """,
            pattern.subject_code,
            pattern.avg_session_duration_mins,
            pattern.best_study_time.value,
            pattern.best_day_of_week.value if pattern.best_day_of_week else None,
            pattern.retention_rate,
            pattern.preferred_session_length,
            pattern.break_frequency_mins,
            pattern.effectiveness_score,
            pattern.deep_work_ratio,
            pattern.samples_count
        )

    async def _analyze_break_patterns(self, subject_code: Optional[str]) -> int:
        """Analyze typical break patterns between sessions"""
        # Find gaps between consecutive sessions on the same day
        if subject_code:
            sessions = await db.fetch("""
                SELECT started_at, stopped_at
                FROM study_sessions ss
                JOIN subjects s ON ss.subject_id = s.id
                WHERE s.code = $1 AND ss.stopped_at IS NOT NULL
                ORDER BY started_at
                LIMIT 100
            """, subject_code)
        else:
            sessions = await db.fetch("""
                SELECT started_at, stopped_at
                FROM study_sessions
                WHERE stopped_at IS NOT NULL
                ORDER BY started_at
                LIMIT 200
            """)

        gaps = []
        prev_session = None

        for session in sessions:
            if prev_session:
                # Check if same day
                if session['started_at'].date() == prev_session['stopped_at'].date():
                    gap_mins = (session['started_at'] - prev_session['stopped_at']).total_seconds() / 60
                    # Only consider reasonable gaps (5 mins to 3 hours)
                    if 5 <= gap_mins <= 180:
                        gaps.append(gap_mins)
            prev_session = session

        if gaps and len(gaps) >= 3:
            return int(statistics.median(gaps))

        return 60  # Default 60 minutes

    def _default_pattern(self, subject_code: Optional[str]) -> LearningPattern:
        """Return default pattern when insufficient data"""
        return LearningPattern(
            subject_code=subject_code,
            avg_session_duration_mins=45,
            best_study_time=TimeOfDay.MORNING,
            best_day_of_week=None,
            retention_rate=0.7,
            preferred_session_length=45,
            break_frequency_mins=60,
            effectiveness_score=0.5,
            deep_work_ratio=0.0,
            samples_count=0,
            last_updated=None
        )

    async def get_hourly_productivity(self, days: int = 30, subject_code: Optional[str] = None) -> List[HourlyProductivity]:
        """Get productivity breakdown by hour of day"""
        if subject_code:
            rows = await db.fetch("""
                SELECT
                    EXTRACT(HOUR FROM ss.started_at)::INTEGER as hour,
                    COUNT(*) as session_count,
                    AVG(ss.duration_seconds / 60.0) as avg_duration_mins,
                    AVG(COALESCE(se.focus_score,
                        CASE WHEN ss.is_deep_work THEN 0.85
                             WHEN ss.duration_seconds >= 2700 THEN 0.7
                             ELSE 0.6 END)) as avg_focus,
                    SUM(CASE WHEN ss.is_deep_work THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as deep_work_rate
                FROM study_sessions ss
                LEFT JOIN session_effectiveness se ON ss.id = se.session_id
                JOIN subjects s ON ss.subject_id = s.id
                WHERE s.code = $1
                  AND ss.stopped_at IS NOT NULL
                  AND ss.started_at >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM ss.started_at)
                ORDER BY hour
            """ % days, subject_code)
        else:
            rows = await db.fetch("""
                SELECT
                    EXTRACT(HOUR FROM ss.started_at)::INTEGER as hour,
                    COUNT(*) as session_count,
                    AVG(ss.duration_seconds / 60.0) as avg_duration_mins,
                    AVG(COALESCE(se.focus_score,
                        CASE WHEN ss.is_deep_work THEN 0.85
                             WHEN ss.duration_seconds >= 2700 THEN 0.7
                             ELSE 0.6 END)) as avg_focus,
                    SUM(CASE WHEN ss.is_deep_work THEN 1 ELSE 0 END)::FLOAT / COUNT(*) as deep_work_rate
                FROM study_sessions ss
                LEFT JOIN session_effectiveness se ON ss.id = se.session_id
                WHERE ss.stopped_at IS NOT NULL
                  AND ss.started_at >= NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM ss.started_at)
                ORDER BY hour
            """ % days)

        return [
            HourlyProductivity(
                hour=row['hour'],
                session_count=row['session_count'],
                avg_duration_mins=round(row['avg_duration_mins'] or 0, 1),
                avg_focus_score=round(row['avg_focus'] or 0.5, 2),
                deep_work_rate=round(row['deep_work_rate'] or 0, 2)
            )
            for row in rows
        ]


# ============================================
# SESSION EFFECTIVENESS TRACKING
# ============================================

async def record_session_effectiveness(
    session_id: int,
    focus_score: float,
    material_covered: Optional[str] = None,
    retention_score: Optional[float] = None,
    energy_level: Optional[int] = None
) -> SessionEffectiveness:
    """Record effectiveness data for a completed session"""

    # Get session details
    session = await db.fetch_one("""
        SELECT ss.started_at, ss.duration_seconds, ss.is_deep_work, s.code as subject_code
        FROM study_sessions ss
        LEFT JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.id = $1
    """, session_id)

    if not session:
        raise ValueError(f"Session {session_id} not found")

    time_of_day = PatternAnalyzer.get_time_of_day(session['started_at'])
    day_of_week = PatternAnalyzer.get_day_of_week(session['started_at'])
    duration = (session['duration_seconds'] or 0) / 60

    # Validate focus score
    focus_score = max(0.0, min(1.0, focus_score))

    # Insert or update effectiveness record
    await db.execute("""
        INSERT INTO session_effectiveness
        (session_id, subject_code, time_of_day, day_of_week, duration_mins,
         focus_score, material_covered, retention_test_score, is_deep_work, energy_level)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        ON CONFLICT (session_id) DO UPDATE SET
            focus_score = EXCLUDED.focus_score,
            material_covered = EXCLUDED.material_covered,
            retention_test_score = EXCLUDED.retention_test_score,
            energy_level = EXCLUDED.energy_level,
            updated_at = NOW()
    """, session_id, session['subject_code'], time_of_day.value, day_of_week.value,
        int(duration), focus_score, material_covered, retention_score,
        session['is_deep_work'], energy_level)

    # Trigger pattern update for this subject
    if session['subject_code']:
        await update_patterns_from_session(session_id)

    return SessionEffectiveness(
        session_id=session_id,
        subject_code=session['subject_code'],
        time_of_day=time_of_day,
        day_of_week=day_of_week,
        duration_mins=int(duration),
        focus_score=focus_score,
        material_covered=material_covered,
        retention_test_score=retention_score,
        is_deep_work=session['is_deep_work'],
        energy_level=energy_level
    )


async def update_patterns_from_session(session_id: int) -> None:
    """Update learning patterns after a session completes"""

    # Get session data
    session = await db.fetch_one("""
        SELECT ss.*, s.code as subject_code
        FROM study_sessions ss
        LEFT JOIN subjects s ON ss.subject_id = s.id
        WHERE ss.id = $1
    """, session_id)

    if not session:
        return

    # Reanalyze patterns
    analyzer = PatternAnalyzer()

    # Update subject-specific pattern if applicable
    if session['subject_code']:
        await analyzer.analyze_patterns(session['subject_code'])

    # Update overall pattern
    await analyzer.analyze_patterns(None)


# ============================================
# RECOMMENDATION ENGINE
# ============================================

class RecommendationEngine:
    """Generates personalized study recommendations based on learned patterns"""

    def __init__(self):
        self.analyzer = PatternAnalyzer()

    async def get_recommendations(
        self,
        context: Dict[str, Any],
        max_recommendations: int = 5
    ) -> List[StudyRecommendation]:
        """Generate recommendations based on current context and patterns"""
        recommendations = []

        # Get overall patterns
        overall_pattern = await self.analyzer.analyze_patterns()

        # Get subject-specific pattern if context includes subject
        subject_pattern = None
        if context.get('subject_code'):
            subject_pattern = await self.analyzer.analyze_patterns(context['subject_code'])

        # Current time context
        now = datetime.now()
        current_tod = PatternAnalyzer.get_time_of_day(now)
        current_dow = PatternAnalyzer.get_day_of_week(now)

        # 1. Time of day recommendation
        if overall_pattern.samples_count >= 5:
            if overall_pattern.best_study_time != current_tod:
                tod_display = overall_pattern.best_study_time.value.replace('_', ' ').title()
                recommendations.append(StudyRecommendation(
                    recommendation_type="time_of_day",
                    recommendation_text=f"Your most productive study time is {tod_display}. "
                        f"Consider scheduling important or difficult tasks then for better focus.",
                    confidence_score=self.analyzer.calculate_confidence(overall_pattern.samples_count, 0.6),
                    priority=7,
                    context={
                        "best_time": overall_pattern.best_study_time.value,
                        "current_time": current_tod.value,
                        "samples": overall_pattern.samples_count
                    }
                ))

        # 2. Session duration recommendation
        planned_duration = context.get('planned_duration')
        if planned_duration:
            pattern = subject_pattern if subject_pattern and subject_pattern.samples_count >= 5 else overall_pattern
            preferred = pattern.preferred_session_length

            if abs(planned_duration - preferred) > 15:
                recommendations.append(StudyRecommendation(
                    recommendation_type="duration",
                    recommendation_text=f"Based on your study history, {preferred}-minute sessions "
                        f"tend to be most effective for you. Consider adjusting your planned "
                        f"{planned_duration}-minute session.",
                    confidence_score=self.analyzer.calculate_confidence(pattern.samples_count, 0.55),
                    priority=6,
                    context={
                        "preferred_duration": preferred,
                        "planned_duration": planned_duration,
                        "subject": context.get('subject_code')
                    }
                ))

        # 3. Subject-specific recommendations
        if subject_pattern and subject_pattern.samples_count >= 5:
            subj_tod = subject_pattern.best_study_time.value.replace('_', ' ').title()
            recommendations.append(StudyRecommendation(
                recommendation_type="subject_specific",
                recommendation_text=f"For {context['subject_code']}, you focus best in the {subj_tod}. "
                    f"Your average effective session is {subject_pattern.preferred_session_length} minutes.",
                confidence_score=subject_pattern.effectiveness_score,
                priority=8,
                context={
                    "subject": context['subject_code'],
                    "best_time": subject_pattern.best_study_time.value,
                    "effectiveness": subject_pattern.effectiveness_score,
                    "preferred_duration": subject_pattern.preferred_session_length
                }
            ))

        # 4. Break recommendation
        recommendations.append(StudyRecommendation(
            recommendation_type="break",
            recommendation_text=f"Take a break every {overall_pattern.break_frequency_mins} minutes "
                f"for optimal retention and sustained focus.",
            confidence_score=0.8,
            priority=5,
            context={"break_frequency_mins": overall_pattern.break_frequency_mins}
        ))

        # 5. Deep work recommendation
        if overall_pattern.deep_work_ratio < 0.3 and overall_pattern.samples_count >= 10:
            recommendations.append(StudyRecommendation(
                recommendation_type="deep_work",
                recommendation_text=f"Only {int(overall_pattern.deep_work_ratio * 100)}% of your sessions "
                    f"are deep work (90+ minutes). Try scheduling longer uninterrupted blocks for complex topics.",
                confidence_score=self.analyzer.calculate_confidence(overall_pattern.samples_count, 0.7),
                priority=7,
                context={
                    "current_ratio": overall_pattern.deep_work_ratio,
                    "target_ratio": 0.3
                }
            ))
        elif overall_pattern.deep_work_ratio >= 0.3:
            recommendations.append(StudyRecommendation(
                recommendation_type="deep_work",
                recommendation_text=f"Great job! {int(overall_pattern.deep_work_ratio * 100)}% of your sessions "
                    f"are deep work sessions. Keep up the focused study habits.",
                confidence_score=self.analyzer.calculate_confidence(overall_pattern.samples_count, 0.7),
                priority=3,
                context={"current_ratio": overall_pattern.deep_work_ratio}
            ))

        # 6. Day of week recommendation
        if overall_pattern.best_day_of_week and overall_pattern.samples_count >= 20:
            best_day = overall_pattern.best_day_of_week.value.title()
            if overall_pattern.best_day_of_week != current_dow:
                recommendations.append(StudyRecommendation(
                    recommendation_type="day_of_week",
                    recommendation_text=f"Your data suggests {best_day} is your most productive day. "
                        f"Consider scheduling challenging work for {best_day}s.",
                    confidence_score=self.analyzer.calculate_confidence(overall_pattern.samples_count, 0.5),
                    priority=4,
                    context={
                        "best_day": overall_pattern.best_day_of_week.value,
                        "current_day": current_dow.value
                    }
                ))

        # 7. Energy-based recommendations based on hourly productivity
        hourly_data = await self.analyzer.get_hourly_productivity(30)
        if hourly_data:
            peak_hours = sorted(hourly_data, key=lambda x: x.avg_focus_score, reverse=True)[:3]
            if peak_hours and peak_hours[0].session_count >= 3:
                peak_times = [f"{h.hour}:00" for h in peak_hours]
                recommendations.append(StudyRecommendation(
                    recommendation_type="energy",
                    recommendation_text=f"Your peak focus hours are around {', '.join(peak_times[:2])}. "
                        f"Schedule your most demanding tasks during these times.",
                    confidence_score=0.75,
                    priority=6,
                    context={
                        "peak_hours": [h.hour for h in peak_hours],
                        "focus_scores": [h.avg_focus_score for h in peak_hours]
                    }
                ))

        # Sort by priority and confidence, limit results
        recommendations.sort(key=lambda r: (r.priority, r.confidence_score), reverse=True)
        return recommendations[:max_recommendations]

    async def get_optimal_study_time(self, subject_code: Optional[str] = None) -> Dict[str, Any]:
        """Get the optimal time to study a particular subject"""
        pattern = await self.analyzer.analyze_patterns(subject_code)
        hourly = await self.analyzer.get_hourly_productivity(30, subject_code)

        # Find peak hour
        peak_hour = None
        peak_score = 0
        if hourly:
            for h in hourly:
                if h.session_count >= 2 and h.avg_focus_score > peak_score:
                    peak_score = h.avg_focus_score
                    peak_hour = h.hour

        return {
            "subject_code": subject_code,
            "best_time_of_day": pattern.best_study_time.value,
            "best_day_of_week": pattern.best_day_of_week.value if pattern.best_day_of_week else None,
            "peak_hour": peak_hour,
            "recommended_duration_mins": pattern.preferred_session_length,
            "effectiveness_score": pattern.effectiveness_score,
            "confidence": self.analyzer.calculate_confidence(pattern.samples_count),
            "samples": pattern.samples_count
        }

    async def suggest_session_duration(
        self,
        subject_code: Optional[str] = None,
        task_difficulty: str = "medium"  # 'easy', 'medium', 'hard'
    ) -> Dict[str, Any]:
        """Suggest optimal session duration based on patterns and task difficulty"""
        pattern = await self.analyzer.analyze_patterns(subject_code)
        base_duration = pattern.preferred_session_length

        # Adjust for difficulty
        multipliers = {"easy": 0.8, "medium": 1.0, "hard": 1.2}
        multiplier = multipliers.get(task_difficulty, 1.0)

        suggested = int(base_duration * multiplier)
        suggested = max(25, min(120, suggested))  # Clamp to reasonable range

        return {
            "suggested_duration_mins": suggested,
            "base_duration_mins": base_duration,
            "task_difficulty": task_difficulty,
            "break_after_mins": pattern.break_frequency_mins,
            "confidence": self.analyzer.calculate_confidence(pattern.samples_count),
            "is_deep_work_recommended": suggested >= 90 and task_difficulty == "hard"
        }


# ============================================
# CRUD OPERATIONS
# ============================================

async def get_learning_pattern(subject_code: Optional[str] = None) -> LearningPattern:
    """Get learning pattern for a subject (or overall)"""
    analyzer = PatternAnalyzer()
    return await analyzer.analyze_patterns(subject_code)


async def get_all_patterns() -> List[LearningPattern]:
    """Get all subject-specific patterns from cache"""
    rows = await db.fetch(
        "SELECT * FROM learning_patterns ORDER BY samples_count DESC"
    )

    patterns = []
    for row in rows:
        patterns.append(LearningPattern(
            subject_code=row.get('subject_code'),
            avg_session_duration_mins=row.get('avg_session_duration_mins', 45),
            best_study_time=TimeOfDay(row.get('best_study_time', 'morning')),
            best_day_of_week=DayOfWeek(row['best_day_of_week']) if row.get('best_day_of_week') else None,
            retention_rate=row.get('retention_rate', 0.7),
            preferred_session_length=row.get('preferred_session_length', 45),
            break_frequency_mins=row.get('break_frequency_mins', 60),
            effectiveness_score=row.get('effectiveness_score', 0.5),
            deep_work_ratio=row.get('deep_work_ratio', 0.0),
            samples_count=row.get('samples_count', 0),
            last_updated=row.get('updated_at')
        ))

    return patterns


async def get_session_effectiveness_history(
    days: int = 30,
    subject_code: Optional[str] = None
) -> List[dict]:
    """Get effectiveness history for sessions"""
    if subject_code:
        return await db.fetch("""
            SELECT se.*, ss.started_at, ss.stopped_at, ss.title
            FROM session_effectiveness se
            JOIN study_sessions ss ON se.session_id = ss.id
            WHERE se.subject_code = $1
              AND ss.started_at >= NOW() - INTERVAL '%s days'
            ORDER BY ss.started_at DESC
        """ % days, subject_code)
    else:
        return await db.fetch("""
            SELECT se.*, ss.started_at, ss.stopped_at, ss.title
            FROM session_effectiveness se
            JOIN study_sessions ss ON se.session_id = ss.id
            WHERE ss.started_at >= NOW() - INTERVAL '%s days'
            ORDER BY ss.started_at DESC
        """ % days)


async def get_productivity_trends(days: int = 30) -> Dict[str, Any]:
    """Get productivity trend analysis"""
    # Daily averages
    daily = await db.fetch("""
        SELECT
            DATE(ss.started_at) as date,
            COUNT(*) as sessions,
            AVG(ss.duration_seconds / 60.0) as avg_duration,
            AVG(COALESCE(se.focus_score, 0.6)) as avg_focus,
            SUM(ss.duration_seconds) / 3600.0 as total_hours
        FROM study_sessions ss
        LEFT JOIN session_effectiveness se ON ss.id = se.session_id
        WHERE ss.stopped_at IS NOT NULL
          AND ss.started_at >= NOW() - INTERVAL '%s days'
        GROUP BY DATE(ss.started_at)
        ORDER BY date
    """ % days)

    # Calculate trends
    if len(daily) >= 7:
        recent_focus = statistics.mean([d['avg_focus'] or 0.5 for d in daily[-7:]])
        earlier_focus = statistics.mean([d['avg_focus'] or 0.5 for d in daily[:7]])
        focus_trend = "improving" if recent_focus > earlier_focus + 0.05 else (
            "declining" if recent_focus < earlier_focus - 0.05 else "stable"
        )

        recent_hours = sum([d['total_hours'] or 0 for d in daily[-7:]])
        earlier_hours = sum([d['total_hours'] or 0 for d in daily[:7]])
        volume_trend = "increasing" if recent_hours > earlier_hours * 1.1 else (
            "decreasing" if recent_hours < earlier_hours * 0.9 else "stable"
        )
    else:
        focus_trend = "insufficient_data"
        volume_trend = "insufficient_data"

    return {
        "daily_data": [dict(d) for d in daily],
        "focus_trend": focus_trend,
        "volume_trend": volume_trend,
        "days_analyzed": len(daily),
        "total_sessions": sum(d['sessions'] for d in daily),
        "avg_daily_hours": statistics.mean([d['total_hours'] or 0 for d in daily]) if daily else 0
    }


# ============================================
# DATABASE SCHEMA (for reference - add to init.sql)
# ============================================
"""
-- Add these tables to database/init.sql:

-- Learning patterns cache
CREATE TABLE learning_patterns (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(20) UNIQUE,  -- NULL for overall pattern
    avg_session_duration_mins INTEGER DEFAULT 45,
    best_study_time VARCHAR(20) DEFAULT 'morning',
    best_day_of_week VARCHAR(20),
    retention_rate DECIMAL(3,2) DEFAULT 0.70,
    preferred_session_length INTEGER DEFAULT 45,
    break_frequency_mins INTEGER DEFAULT 60,
    effectiveness_score DECIMAL(4,3) DEFAULT 0.500,
    deep_work_ratio DECIMAL(4,3) DEFAULT 0.000,
    samples_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_learning_patterns_subject ON learning_patterns(subject_code);

-- Session effectiveness tracking
CREATE TABLE session_effectiveness (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE UNIQUE,
    subject_code VARCHAR(20),
    time_of_day VARCHAR(20) NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    duration_mins INTEGER NOT NULL,
    focus_score DECIMAL(3,2) NOT NULL CHECK (focus_score >= 0 AND focus_score <= 1),
    material_covered TEXT,
    retention_test_score DECIMAL(3,2) CHECK (retention_test_score >= 0 AND retention_test_score <= 1),
    is_deep_work BOOLEAN DEFAULT FALSE,
    energy_level INTEGER CHECK (energy_level >= 1 AND energy_level <= 10),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_session_effectiveness_subject ON session_effectiveness(subject_code);
CREATE INDEX idx_session_effectiveness_time ON session_effectiveness(time_of_day);
"""
