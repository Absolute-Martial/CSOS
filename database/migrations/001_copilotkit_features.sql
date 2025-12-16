-- ============================================
-- Migration: 001_copilotkit_features.sql
-- Description: Add AI-powered features for learning patterns,
--              achievements, notifications, and wellbeing tracking
-- Version: 1.0.2
-- Date: 2025-12-16
-- ============================================

-- ============================================
-- 1. LEARNING PATTERNS TRACKING
-- ============================================

-- Track how users learn best for each subject
-- Stores aggregated learning analytics per subject to optimize scheduling
CREATE TABLE IF NOT EXISTS learning_patterns (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(10) NOT NULL,
    avg_comprehension_time_mins INTEGER DEFAULT 0,
    best_study_time VARCHAR(20) DEFAULT 'morning', -- 'morning', 'afternoon', 'evening', 'night'
    retention_rate DECIMAL(3,2) DEFAULT 0.00 CHECK (retention_rate >= 0.00 AND retention_rate <= 1.00),
    preferred_session_length INTEGER DEFAULT 60, -- in minutes
    break_frequency_mins INTEGER DEFAULT 25, -- pomodoro default
    effectiveness_score DECIMAL(3,2) DEFAULT 0.00 CHECK (effectiveness_score >= 0.00 AND effectiveness_score <= 1.00),
    samples_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_subject_pattern UNIQUE (subject_code)
);

COMMENT ON TABLE learning_patterns IS 'Aggregated learning analytics per subject for AI-driven schedule optimization';
COMMENT ON COLUMN learning_patterns.best_study_time IS 'Time of day when user learns this subject most effectively';
COMMENT ON COLUMN learning_patterns.retention_rate IS 'Average retention rate (0.00-1.00) based on revision performance';
COMMENT ON COLUMN learning_patterns.effectiveness_score IS 'Overall effectiveness score combining multiple factors';

-- Track individual session effectiveness for granular analytics
-- Links to study_sessions and captures detailed performance metrics
CREATE TABLE IF NOT EXISTS session_effectiveness (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES study_sessions(id) ON DELETE CASCADE,
    subject_code VARCHAR(10) NOT NULL,
    time_of_day VARCHAR(20) NOT NULL, -- 'morning', 'afternoon', 'evening', 'night'
    duration_mins INTEGER NOT NULL CHECK (duration_mins > 0),
    focus_score DECIMAL(3,2) DEFAULT 0.00 CHECK (focus_score >= 0.00 AND focus_score <= 1.00),
    material_covered TEXT, -- chapters/topics covered
    retention_test_score DECIMAL(3,2) CHECK (retention_test_score IS NULL OR (retention_test_score >= 0.00 AND retention_test_score <= 1.00)),
    energy_level_start INTEGER CHECK (energy_level_start IS NULL OR (energy_level_start >= 1 AND energy_level_start <= 10)),
    energy_level_end INTEGER CHECK (energy_level_end IS NULL OR (energy_level_end >= 1 AND energy_level_end <= 10)),
    distractions_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE session_effectiveness IS 'Detailed effectiveness metrics for each study session';
COMMENT ON COLUMN session_effectiveness.focus_score IS 'Self-reported or calculated focus level (0.00-1.00)';
COMMENT ON COLUMN session_effectiveness.retention_test_score IS 'Score from post-session retention test if taken';

CREATE INDEX IF NOT EXISTS idx_session_effectiveness_subject ON session_effectiveness(subject_code);
CREATE INDEX IF NOT EXISTS idx_session_effectiveness_time ON session_effectiveness(time_of_day);
CREATE INDEX IF NOT EXISTS idx_session_effectiveness_session ON session_effectiveness(session_id);

-- ============================================
-- 2. ENHANCED ACHIEVEMENT SYSTEM
-- ============================================

-- Achievement definitions with richer metadata
-- Defines all possible achievements users can earn
CREATE TABLE IF NOT EXISTS achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '🏆',
    category VARCHAR(50) NOT NULL, -- 'streak', 'study', 'goal', 'revision', 'special'
    threshold_value INTEGER NOT NULL DEFAULT 1,
    points INTEGER DEFAULT 10 CHECK (points >= 0),
    rarity VARCHAR(20) DEFAULT 'common' CHECK (rarity IN ('common', 'rare', 'epic', 'legendary')),
    is_hidden BOOLEAN DEFAULT FALSE, -- hidden achievements for surprise unlocks
    prerequisite_id INTEGER REFERENCES achievement_definitions(id), -- for achievement chains
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE achievement_definitions IS 'Master list of all achievable milestones with criteria';
COMMENT ON COLUMN achievement_definitions.threshold_value IS 'Value that must be reached to unlock achievement';
COMMENT ON COLUMN achievement_definitions.is_hidden IS 'Hidden achievements are not shown until unlocked';

-- User earned achievements with progress tracking
CREATE TABLE IF NOT EXISTS user_achievements (
    id SERIAL PRIMARY KEY,
    achievement_id INTEGER NOT NULL REFERENCES achievement_definitions(id) ON DELETE CASCADE,
    progress_value INTEGER DEFAULT 0,
    is_complete BOOLEAN DEFAULT FALSE,
    earned_at TIMESTAMP WITH TIME ZONE,
    notified BOOLEAN DEFAULT FALSE,
    notification_dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_user_achievement UNIQUE (achievement_id)
);

COMMENT ON TABLE user_achievements IS 'Tracks user progress and completion status for each achievement';
COMMENT ON COLUMN user_achievements.notified IS 'Whether user has been notified of achievement unlock';

CREATE INDEX IF NOT EXISTS idx_user_achievements_complete ON user_achievements(is_complete, notified);
CREATE INDEX IF NOT EXISTS idx_user_achievements_achievement ON user_achievements(achievement_id);

-- Progress snapshots for visualization and historical tracking
-- Captures daily state for progress charts and analytics
CREATE TABLE IF NOT EXISTS progress_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_study_mins INTEGER DEFAULT 0,
    deep_work_mins INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    revisions_completed INTEGER DEFAULT 0,
    flashcards_reviewed INTEGER DEFAULT 0,
    goals_progress JSONB DEFAULT '{}', -- {"goal_id": progress_percentage, ...}
    streak_count INTEGER DEFAULT 0,
    achievement_points INTEGER DEFAULT 0,
    subjects_studied JSONB DEFAULT '[]', -- ["MATH101", "PHYS102", ...]
    energy_avg DECIMAL(3,1),
    focus_avg DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE progress_snapshots IS 'Daily aggregated metrics for progress visualization';
COMMENT ON COLUMN progress_snapshots.goals_progress IS 'JSON object mapping goal IDs to progress percentages';
COMMENT ON COLUMN progress_snapshots.subjects_studied IS 'Array of subject codes studied on this date';

CREATE INDEX IF NOT EXISTS idx_progress_snapshots_date ON progress_snapshots(snapshot_date);

-- ============================================
-- 3. ENHANCED NOTIFICATION SYSTEM
-- ============================================

-- Note: A basic notifications table already exists in init.sql
-- This creates an enhanced version with more features
-- Drop old constraints/indexes if upgrading

-- Enhanced notifications with action support
CREATE TABLE IF NOT EXISTS notifications_v2 (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'reminder', 'achievement', 'suggestion', 'warning', 'deadline', 'break'
    title VARCHAR(200) NOT NULL,
    message TEXT,
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    action_url VARCHAR(500), -- deep link or URL for action
    action_label VARCHAR(100), -- button text for action
    action_data JSONB, -- additional data for action handling
    related_entity_type VARCHAR(50), -- 'task', 'goal', 'achievement', 'lab_report'
    related_entity_id INTEGER,
    scheduled_for TIMESTAMP WITH TIME ZONE, -- when to show (NULL = immediately)
    sent_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE, -- auto-dismiss after this time
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE notifications_v2 IS 'Enhanced notification system with actions and scheduling';
COMMENT ON COLUMN notifications_v2.action_url IS 'Deep link or URL to navigate when notification action is clicked';
COMMENT ON COLUMN notifications_v2.scheduled_for IS 'Schedule notification for future delivery (NULL for immediate)';

CREATE INDEX IF NOT EXISTS idx_notifications_v2_scheduled ON notifications_v2(scheduled_for) WHERE scheduled_for IS NOT NULL AND sent_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_v2_unread ON notifications_v2(read_at) WHERE read_at IS NULL AND dismissed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_notifications_v2_type ON notifications_v2(type);

-- Notification preferences per notification type
CREATE TABLE IF NOT EXISTS notification_preferences (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME, -- don't send during these hours
    quiet_hours_end TIME,
    frequency_limit INTEGER, -- max notifications per hour of this type
    channels JSONB DEFAULT '["app"]', -- ["app", "email", "push"]
    custom_settings JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE notification_preferences IS 'User preferences for notification delivery';
COMMENT ON COLUMN notification_preferences.quiet_hours_start IS 'Start of quiet hours (no notifications)';
COMMENT ON COLUMN notification_preferences.channels IS 'Array of enabled notification channels';

-- Insert default notification preferences
INSERT INTO notification_preferences (notification_type, enabled, frequency_limit) VALUES
    ('reminder', TRUE, 10),
    ('achievement', TRUE, NULL),
    ('suggestion', TRUE, 5),
    ('warning', TRUE, NULL),
    ('deadline', TRUE, NULL),
    ('break', TRUE, 3)
ON CONFLICT (notification_type) DO NOTHING;

-- ============================================
-- 4. WELLBEING TRACKING
-- ============================================

-- Daily wellbeing metrics for burnout prevention
CREATE TABLE IF NOT EXISTS wellbeing_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL UNIQUE,
    study_hours DECIMAL(4,2) DEFAULT 0.00,
    break_count INTEGER DEFAULT 0,
    break_total_mins INTEGER DEFAULT 0,
    deep_work_sessions INTEGER DEFAULT 0,
    task_completion_rate DECIMAL(3,2) CHECK (task_completion_rate IS NULL OR (task_completion_rate >= 0.00 AND task_completion_rate <= 1.00)),
    overdue_tasks INTEGER DEFAULT 0,
    stress_indicators JSONB DEFAULT '{}', -- {"late_night_study": false, "skipped_breaks": 0, "overload_hours": 0}
    wellbeing_score DECIMAL(3,2) CHECK (wellbeing_score IS NULL OR (wellbeing_score >= 0.00 AND wellbeing_score <= 1.00)),
    recommendations JSONB DEFAULT '[]', -- ["Take more breaks", "Consider lighter schedule tomorrow"]
    mood_rating INTEGER CHECK (mood_rating IS NULL OR (mood_rating >= 1 AND mood_rating <= 5)),
    energy_rating INTEGER CHECK (energy_rating IS NULL OR (energy_rating >= 1 AND energy_rating <= 5)),
    sleep_hours DECIMAL(3,1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE wellbeing_metrics IS 'Daily wellbeing tracking for burnout prevention and self-care';
COMMENT ON COLUMN wellbeing_metrics.stress_indicators IS 'JSON object with various stress signals';
COMMENT ON COLUMN wellbeing_metrics.wellbeing_score IS 'Calculated overall wellbeing (0.00-1.00)';

CREATE INDEX IF NOT EXISTS idx_wellbeing_metrics_date ON wellbeing_metrics(metric_date);

-- Break sessions for detailed break tracking
CREATE TABLE IF NOT EXISTS break_sessions (
    id SERIAL PRIMARY KEY,
    break_type VARCHAR(50) NOT NULL, -- 'short', 'pomodoro', 'meal', 'exercise', 'meditation', 'walk'
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    suggested_duration_mins INTEGER,
    actual_duration_mins INTEGER,
    was_completed BOOLEAN DEFAULT FALSE,
    activity_notes TEXT,
    refreshment_rating INTEGER CHECK (refreshment_rating IS NULL OR (refreshment_rating >= 1 AND refreshment_rating <= 5)),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE break_sessions IS 'Track break sessions for wellbeing analysis';
COMMENT ON COLUMN break_sessions.refreshment_rating IS 'How refreshed user felt after break (1-5)';

CREATE INDEX IF NOT EXISTS idx_break_sessions_date ON break_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_break_sessions_type ON break_sessions(break_type);

-- ============================================
-- 5. INSERT DEFAULT ACHIEVEMENT DEFINITIONS
-- ============================================

INSERT INTO achievement_definitions (code, name, description, icon, category, threshold_value, points, rarity) VALUES
    -- Streak achievements
    ('streak_3', 'Getting Started', 'Maintain a 3-day study streak', '🔥', 'streak', 3, 10, 'common'),
    ('streak_7', 'Week Warrior', 'Maintain a 7-day study streak', '⚡', 'streak', 7, 25, 'common'),
    ('streak_14', 'Fortnight Fighter', 'Maintain a 14-day study streak', '🌟', 'streak', 14, 50, 'rare'),
    ('streak_30', 'Month Master', 'Maintain a 30-day study streak', '💎', 'streak', 30, 100, 'rare'),
    ('streak_100', 'Centurion', 'Maintain a 100-day study streak', '👑', 'streak', 100, 500, 'legendary'),

    -- Deep work achievements
    ('deep_work_1', 'Deep Diver', 'Complete your first 90+ minute focus session', '🎯', 'study', 1, 15, 'common'),
    ('deep_work_10', 'Focus Master', 'Complete 10 deep work sessions', '🧠', 'study', 10, 50, 'rare'),
    ('deep_work_50', 'Concentration King', 'Complete 50 deep work sessions', '🏰', 'study', 50, 200, 'epic'),

    -- Task achievements
    ('tasks_10', 'Task Tackler', 'Complete 10 tasks', '✅', 'goal', 10, 10, 'common'),
    ('tasks_50', 'Task Terminator', 'Complete 50 tasks', '⚔️', 'goal', 50, 50, 'rare'),
    ('tasks_100', 'Productivity Pro', 'Complete 100 tasks', '🏆', 'goal', 100, 100, 'rare'),
    ('tasks_500', 'Task Titan', 'Complete 500 tasks', '🦸', 'goal', 500, 500, 'legendary'),

    -- Revision achievements
    ('revision_master', 'Memory Champion', 'Complete all scheduled revisions for a chapter', '📚', 'revision', 1, 30, 'rare'),
    ('revision_10', 'Revision Rookie', 'Complete 10 revisions', '📖', 'revision', 10, 25, 'common'),
    ('revision_50', 'Revision Regular', 'Complete 50 revisions', '📕', 'revision', 50, 75, 'rare'),

    -- Time-based achievements
    ('early_bird', 'Early Bird', 'Study before 7 AM for 10 days', '🌅', 'special', 10, 20, 'common'),
    ('night_owl', 'Night Owl', 'Complete productive midnight study sessions (10 times)', '🦉', 'special', 10, 20, 'common'),

    -- Goal achievements
    ('goals_5', 'Goal Getter', 'Complete 5 study goals', '🎯', 'goal', 5, 30, 'common'),
    ('goals_25', 'Goal Crusher', 'Complete 25 study goals', '💪', 'goal', 25, 100, 'rare'),

    -- Perfect week
    ('perfectionist', 'Perfectionist', 'Complete all tasks for an entire week', '✨', 'special', 1, 75, 'epic'),

    -- Study hours
    ('hours_100', 'Century Study', 'Accumulate 100 hours of study time', '⏰', 'study', 100, 100, 'rare'),
    ('hours_500', 'Time Lord', 'Accumulate 500 hours of study time', '⌛', 'study', 500, 500, 'legendary'),

    -- Wellbeing achievements
    ('balanced_week', 'Work-Life Balance', 'Take all suggested breaks for a week', '☯️', 'special', 1, 50, 'rare'),
    ('wellness_warrior', 'Wellness Warrior', 'Maintain wellbeing score above 0.8 for 7 days', '💚', 'special', 7, 75, 'epic')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    icon = EXCLUDED.icon,
    category = EXCLUDED.category,
    threshold_value = EXCLUDED.threshold_value,
    points = EXCLUDED.points,
    rarity = EXCLUDED.rarity;

-- ============================================
-- 6. ADDITIONAL INDEXES FOR PERFORMANCE
-- ============================================

-- Learning patterns indexes
CREATE INDEX IF NOT EXISTS idx_learning_patterns_subject ON learning_patterns(subject_code);
CREATE INDEX IF NOT EXISTS idx_learning_patterns_effectiveness ON learning_patterns(effectiveness_score DESC);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_session_effectiveness_subject_time ON session_effectiveness(subject_code, time_of_day);
CREATE INDEX IF NOT EXISTS idx_user_achievements_status ON user_achievements(achievement_id, is_complete);

-- ============================================
-- 7. FUNCTIONS AND TRIGGERS
-- ============================================

-- Function to auto-create daily progress snapshot
CREATE OR REPLACE FUNCTION create_daily_progress_snapshot()
RETURNS void AS $$
DECLARE
    snapshot_date_var DATE := CURRENT_DATE;
    total_study INTEGER;
    deep_work INTEGER;
    tasks_done INTEGER;
    revisions_done INTEGER;
    flashcards INTEGER;
    streak INTEGER;
    points INTEGER;
BEGIN
    -- Get data from daily_study_stats
    SELECT
        COALESCE(total_study_seconds / 60, 0),
        COALESCE(deep_work_seconds / 60, 0),
        COALESCE(flashcards_reviewed, 0),
        COALESCE(revisions_completed, 0),
        COALESCE(points_earned, 0)
    INTO total_study, deep_work, flashcards, revisions_done, points
    FROM daily_study_stats
    WHERE stat_date = snapshot_date_var;

    -- Count completed tasks for today
    SELECT COUNT(*) INTO tasks_done
    FROM tasks
    WHERE status = 'completed'
    AND DATE(updated_at) = snapshot_date_var;

    -- Get current streak
    SELECT current_streak INTO streak
    FROM user_streaks
    LIMIT 1;

    -- Upsert progress snapshot
    INSERT INTO progress_snapshots (
        snapshot_date,
        total_study_mins,
        deep_work_mins,
        tasks_completed,
        revisions_completed,
        flashcards_reviewed,
        streak_count,
        achievement_points
    ) VALUES (
        snapshot_date_var,
        COALESCE(total_study, 0),
        COALESCE(deep_work, 0),
        COALESCE(tasks_done, 0),
        COALESCE(revisions_done, 0),
        COALESCE(flashcards, 0),
        COALESCE(streak, 0),
        COALESCE(points, 0)
    )
    ON CONFLICT (snapshot_date) DO UPDATE SET
        total_study_mins = EXCLUDED.total_study_mins,
        deep_work_mins = EXCLUDED.deep_work_mins,
        tasks_completed = EXCLUDED.tasks_completed,
        revisions_completed = EXCLUDED.revisions_completed,
        flashcards_reviewed = EXCLUDED.flashcards_reviewed,
        streak_count = EXCLUDED.streak_count,
        achievement_points = EXCLUDED.achievement_points,
        created_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION create_daily_progress_snapshot IS 'Creates or updates daily progress snapshot for visualization';

-- Function to update learning patterns from session effectiveness
CREATE OR REPLACE FUNCTION update_learning_pattern_from_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert learning pattern for this subject
    INSERT INTO learning_patterns (
        subject_code,
        avg_comprehension_time_mins,
        best_study_time,
        preferred_session_length,
        effectiveness_score,
        samples_count,
        updated_at
    ) VALUES (
        NEW.subject_code,
        NEW.duration_mins,
        NEW.time_of_day,
        NEW.duration_mins,
        NEW.focus_score,
        1,
        NOW()
    )
    ON CONFLICT (subject_code) DO UPDATE SET
        avg_comprehension_time_mins = (
            (learning_patterns.avg_comprehension_time_mins * learning_patterns.samples_count + NEW.duration_mins)
            / (learning_patterns.samples_count + 1)
        )::INTEGER,
        effectiveness_score = (
            (learning_patterns.effectiveness_score * learning_patterns.samples_count + NEW.focus_score)
            / (learning_patterns.samples_count + 1)
        ),
        samples_count = learning_patterns.samples_count + 1,
        updated_at = NOW();

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER IF NOT EXISTS tr_update_learning_patterns
    AFTER INSERT ON session_effectiveness
    FOR EACH ROW
    EXECUTE FUNCTION update_learning_pattern_from_session();

-- Function to calculate wellbeing score
CREATE OR REPLACE FUNCTION calculate_wellbeing_score(
    p_study_hours DECIMAL,
    p_break_count INTEGER,
    p_overdue_tasks INTEGER,
    p_deep_work_sessions INTEGER
) RETURNS DECIMAL AS $$
DECLARE
    score DECIMAL := 0.5; -- baseline
    study_factor DECIMAL;
    break_factor DECIMAL;
    overdue_factor DECIMAL;
BEGIN
    -- Study hours factor (optimal: 4-8 hours)
    IF p_study_hours >= 4 AND p_study_hours <= 8 THEN
        study_factor := 0.2;
    ELSIF p_study_hours > 8 THEN
        study_factor := -0.1 * (p_study_hours - 8); -- penalize overwork
    ELSE
        study_factor := 0.05 * p_study_hours;
    END IF;

    -- Break factor (reward taking breaks)
    break_factor := LEAST(p_break_count * 0.05, 0.2);

    -- Overdue tasks penalty
    overdue_factor := -0.05 * p_overdue_tasks;

    -- Calculate final score
    score := GREATEST(0.00, LEAST(1.00, score + study_factor + break_factor + overdue_factor));

    RETURN score;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_wellbeing_score IS 'Calculates wellbeing score based on study habits';

-- Function to update wellbeing metrics
CREATE OR REPLACE FUNCTION update_daily_wellbeing()
RETURNS void AS $$
DECLARE
    today_date DATE := CURRENT_DATE;
    study_hrs DECIMAL;
    breaks INTEGER;
    break_mins INTEGER;
    deep_sessions INTEGER;
    overdue INTEGER;
    completion_rate DECIMAL;
    wellbeing DECIMAL;
BEGIN
    -- Get study hours from daily stats
    SELECT COALESCE(total_study_seconds / 3600.0, 0)
    INTO study_hrs
    FROM daily_study_stats
    WHERE stat_date = today_date;

    -- Get break stats
    SELECT COUNT(*), COALESCE(SUM(actual_duration_mins), 0)
    INTO breaks, break_mins
    FROM break_sessions
    WHERE DATE(started_at) = today_date AND was_completed = TRUE;

    -- Count deep work sessions
    SELECT COUNT(*)
    INTO deep_sessions
    FROM study_sessions
    WHERE DATE(started_at) = today_date AND is_deep_work = TRUE;

    -- Count overdue tasks
    SELECT COUNT(*)
    INTO overdue
    FROM tasks
    WHERE status = 'pending' AND scheduled_end < NOW();

    -- Calculate completion rate
    SELECT
        CASE
            WHEN COUNT(*) = 0 THEN NULL
            ELSE COUNT(*) FILTER (WHERE status = 'completed')::DECIMAL / COUNT(*)
        END
    INTO completion_rate
    FROM tasks
    WHERE DATE(scheduled_start) = today_date;

    -- Calculate wellbeing score
    wellbeing := calculate_wellbeing_score(
        COALESCE(study_hrs, 0),
        COALESCE(breaks, 0),
        COALESCE(overdue, 0),
        COALESCE(deep_sessions, 0)
    );

    -- Upsert wellbeing metrics
    INSERT INTO wellbeing_metrics (
        metric_date,
        study_hours,
        break_count,
        break_total_mins,
        deep_work_sessions,
        task_completion_rate,
        overdue_tasks,
        wellbeing_score,
        updated_at
    ) VALUES (
        today_date,
        COALESCE(study_hrs, 0),
        COALESCE(breaks, 0),
        COALESCE(break_mins, 0),
        COALESCE(deep_sessions, 0),
        completion_rate,
        COALESCE(overdue, 0),
        wellbeing,
        NOW()
    )
    ON CONFLICT (metric_date) DO UPDATE SET
        study_hours = EXCLUDED.study_hours,
        break_count = EXCLUDED.break_count,
        break_total_mins = EXCLUDED.break_total_mins,
        deep_work_sessions = EXCLUDED.deep_work_sessions,
        task_completion_rate = EXCLUDED.task_completion_rate,
        overdue_tasks = EXCLUDED.overdue_tasks,
        wellbeing_score = EXCLUDED.wellbeing_score,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_daily_wellbeing IS 'Updates daily wellbeing metrics based on current data';

-- Function to check and award achievements
CREATE OR REPLACE FUNCTION check_achievement_progress(
    p_achievement_code VARCHAR(50),
    p_progress_value INTEGER
) RETURNS BOOLEAN AS $$
DECLARE
    v_achievement_id INTEGER;
    v_threshold INTEGER;
    v_is_complete BOOLEAN;
BEGIN
    -- Get achievement details
    SELECT id, threshold_value
    INTO v_achievement_id, v_threshold
    FROM achievement_definitions
    WHERE code = p_achievement_code;

    IF v_achievement_id IS NULL THEN
        RETURN FALSE;
    END IF;

    -- Check if already complete
    SELECT is_complete INTO v_is_complete
    FROM user_achievements
    WHERE achievement_id = v_achievement_id;

    IF v_is_complete THEN
        RETURN FALSE; -- Already earned
    END IF;

    -- Upsert progress
    INSERT INTO user_achievements (achievement_id, progress_value, is_complete, earned_at)
    VALUES (
        v_achievement_id,
        p_progress_value,
        p_progress_value >= v_threshold,
        CASE WHEN p_progress_value >= v_threshold THEN NOW() ELSE NULL END
    )
    ON CONFLICT (achievement_id) DO UPDATE SET
        progress_value = EXCLUDED.progress_value,
        is_complete = EXCLUDED.is_complete,
        earned_at = CASE
            WHEN EXCLUDED.is_complete AND NOT user_achievements.is_complete
            THEN NOW()
            ELSE user_achievements.earned_at
        END;

    RETURN p_progress_value >= v_threshold;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_achievement_progress IS 'Checks and updates achievement progress, returns TRUE if newly completed';

-- Trigger to update break session duration when ended
CREATE OR REPLACE FUNCTION update_break_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.ended_at IS NOT NULL AND OLD.ended_at IS NULL THEN
        NEW.actual_duration_mins := EXTRACT(EPOCH FROM (NEW.ended_at - NEW.started_at)) / 60;
        NEW.was_completed := TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_update_break_duration ON break_sessions;
CREATE TRIGGER tr_update_break_duration
    BEFORE UPDATE ON break_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_break_duration();

-- ============================================
-- 8. VERSION UPDATE
-- ============================================

INSERT INTO version_metadata (version, changelog)
VALUES ('1.0.2', 'Added CopilotKit features: learning patterns, enhanced achievements, notifications v2, wellbeing tracking')
ON CONFLICT DO NOTHING;

-- ============================================
-- END OF MIGRATION
-- ============================================
