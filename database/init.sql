-- ============================================
-- Personal Engineering OS - Database Schema
-- Version: 1.0.1
-- ============================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- ENUMS
-- ============================================

CREATE TYPE subject_type AS ENUM ('practice_heavy', 'concept_heavy');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed', 'cancelled');
CREATE TYPE progress_status AS ENUM ('not_started', 'in_progress', 'completed');
CREATE TYPE assignment_status AS ENUM ('locked', 'available', 'in_progress', 'submitted');
CREATE TYPE file_type AS ENUM ('slide', 'assignment', 'note');
CREATE TYPE notification_type AS ENUM ('due_date', 'revision', 'streak_warning', 'achievement');
CREATE TYPE log_level AS ENUM ('debug', 'info', 'warning', 'error');

-- ============================================
-- CORE TABLES
-- ============================================

-- Version metadata
CREATE TABLE version_metadata (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) NOT NULL DEFAULT '1.0.1',
    deployed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    changelog TEXT
);

INSERT INTO version_metadata (version, changelog) VALUES ('1.0.1', 'Initial release');

-- Subjects with credits
CREATE TABLE subjects (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    credits INTEGER NOT NULL DEFAULT 3,
    type subject_type NOT NULL,
    color VARCHAR(7) DEFAULT '#6366f1',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default subjects
INSERT INTO subjects (code, name, credits, type, color) VALUES
    ('MATH101', 'Mathematics I', 3, 'practice_heavy', '#3b82f6'),
    ('PHYS102', 'Physics I', 4, 'practice_heavy', '#ef4444'),
    ('CHEM101', 'Chemistry I', 3, 'concept_heavy', '#22c55e'),
    ('ENGG111', 'Engineering Fundamentals', 1, 'concept_heavy', '#f59e0b');

-- Chapters
CREATE TABLE chapters (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    total_pages INTEGER DEFAULT 0,
    folder_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(subject_id, number)
);

-- Chapter progress tracking
CREATE TABLE chapter_progress (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE UNIQUE,
    reading_status progress_status DEFAULT 'not_started',
    assignment_status assignment_status DEFAULT 'locked',
    mastery_level INTEGER DEFAULT 0 CHECK (mastery_level >= 0 AND mastery_level <= 100),
    revision_count INTEGER DEFAULT 0,
    last_revised_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- TASKS & LAB REPORTS
-- ============================================

-- General tasks
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    duration_mins INTEGER DEFAULT 60,
    scheduled_start TIMESTAMP WITH TIME ZONE,
    scheduled_end TIMESTAMP WITH TIME ZONE,
    status task_status DEFAULT 'pending',
    is_deep_work BOOLEAN DEFAULT FALSE,
    task_type VARCHAR(50) DEFAULT 'study', -- 'study', 'revision', 'practice', 'assignment', 'lab_work'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tasks_scheduled ON tasks(scheduled_start);
CREATE INDEX idx_tasks_status ON tasks(status);

-- Lab reports (enhanced)
CREATE TABLE lab_reports (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    experiment_name VARCHAR(200),
    lab_date DATE,
    due_date DATE NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    status task_status DEFAULT 'pending',
    notes TEXT,
    file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_lab_reports_due ON lab_reports(due_date);
CREATE INDEX idx_lab_reports_status ON lab_reports(status);

-- ============================================
-- REVISION SYSTEM (Weekly)
-- ============================================

CREATE TABLE revision_schedule (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    revision_number INTEGER NOT NULL,
    due_date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_revision_due ON revision_schedule(due_date, completed);

-- ============================================
-- FILE STORAGE
-- ============================================

CREATE TABLE chapter_files (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    file_type file_type NOT NULL,
    filename VARCHAR(255) NOT NULL,
    filepath VARCHAR(500) NOT NULL,
    mimetype VARCHAR(100),
    file_size INTEGER,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chapter_files ON chapter_files(chapter_id, file_type);

-- ============================================
-- STREAK & REWARDS
-- ============================================

CREATE TABLE user_streaks (
    id SERIAL PRIMARY KEY,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    last_activity DATE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO user_streaks (current_streak) VALUES (0);

CREATE TABLE rewards (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(10) NOT NULL,
    required_streak INTEGER NOT NULL,
    unlocked BOOLEAN DEFAULT FALSE,
    unlocked_at TIMESTAMP WITH TIME ZONE
);

INSERT INTO rewards (name, icon, required_streak) VALUES
    ('Bronze', '🔥', 3),
    ('Silver', '⚡', 7),
    ('Gold', '🌟', 14),
    ('Diamond', '💎', 30);

-- ============================================
-- AI MEMORY & GUIDELINES
-- ============================================

CREATE TABLE ai_memory (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    key VARCHAR(100) NOT NULL,
    value TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(category, key)
);

CREATE TABLE ai_guidelines (
    id SERIAL PRIMARY KEY,
    rule TEXT NOT NULL,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert default guidelines
INSERT INTO ai_guidelines (rule, priority) VALUES
    ('Wake time is 04:30, sleep time is 22:30. Never schedule outside these hours.', 1),
    ('Lab reports must be started at least 3 days before deadline.', 1),
    ('Deep work sessions must be at least 90 minutes.', 2),
    ('PHYS102 has highest priority (4 credits).', 2),
    ('Always confirm before creating folders or files.', 1);

CREATE TABLE conversation_history (
    id SERIAL PRIMARY KEY,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_calls JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- NOTIFICATIONS
-- ============================================

CREATE TABLE notifications (
    id SERIAL PRIMARY KEY,
    type notification_type NOT NULL,
    title VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    due_at TIMESTAMP WITH TIME ZONE,
    read BOOLEAN DEFAULT FALSE,
    dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_unread ON notifications(read, dismissed, due_at);

-- ============================================
-- SYSTEM LOGS
-- ============================================

CREATE TABLE system_logs (
    id SERIAL PRIMARY KEY,
    level log_level NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    context JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_logs_level ON system_logs(level, created_at DESC);

-- ============================================
-- NAMING RULES (AI-Enforced)
-- ============================================

CREATE TABLE naming_rules (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    pattern VARCHAR(200) NOT NULL,
    example VARCHAR(200) NOT NULL,
    description TEXT
);

INSERT INTO naming_rules (entity_type, pattern, example, description) VALUES
    ('subject', '[A-Z]{4}[0-9]{3}', 'MATH101', 'Uppercase letters + 3 digits'),
    ('chapter', 'chapter[0-9]{2}', 'chapter01', 'Lowercase + 2 digit number'),
    ('file', '[a-z_]+\\.[a-z]+', 'lecture_slides.pdf', 'Snake case + extension');

-- ============================================
-- FUNCTIONS
-- ============================================

-- Auto-schedule weekly revisions on chapter completion
CREATE OR REPLACE FUNCTION schedule_weekly_revisions()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.reading_status = 'completed' AND OLD.reading_status != 'completed' THEN
        INSERT INTO revision_schedule (chapter_id, revision_number, due_date)
        VALUES
            (NEW.chapter_id, 1, CURRENT_DATE + INTERVAL '7 days'),
            (NEW.chapter_id, 2, CURRENT_DATE + INTERVAL '14 days'),
            (NEW.chapter_id, 3, CURRENT_DATE + INTERVAL '21 days');
        
        NEW.assignment_status := 'available';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_schedule_revisions
    BEFORE UPDATE ON chapter_progress
    FOR EACH ROW
    EXECUTE FUNCTION schedule_weekly_revisions();

-- Update streak on activity
CREATE OR REPLACE FUNCTION update_streak()
RETURNS TRIGGER AS $$
DECLARE
    last_date DATE;
    current_st INTEGER;
BEGIN
    SELECT last_activity, current_streak INTO last_date, current_st FROM user_streaks LIMIT 1;
    
    IF last_date IS NULL OR last_date < CURRENT_DATE - 1 THEN
        UPDATE user_streaks SET current_streak = 1, last_activity = CURRENT_DATE;
    ELSIF last_date = CURRENT_DATE - 1 THEN
        UPDATE user_streaks SET 
            current_streak = current_streak + 1,
            longest_streak = GREATEST(longest_streak, current_streak + 1),
            last_activity = CURRENT_DATE;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_update_streak_revision
    AFTER UPDATE ON revision_schedule
    FOR EACH ROW
    WHEN (NEW.completed = TRUE AND OLD.completed = FALSE)
    EXECUTE FUNCTION update_streak();

-- ============================================
-- STUDY TIMER SYSTEM
-- ============================================

CREATE TABLE study_sessions (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    title VARCHAR(200),
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    stopped_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    is_deep_work BOOLEAN DEFAULT FALSE,
    notes TEXT,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_study_sessions_date ON study_sessions(started_at);
CREATE INDEX idx_study_sessions_subject ON study_sessions(subject_id);

-- Active timer tracking (single row ensures only one timer runs)
CREATE TABLE active_timer (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    session_id INTEGER REFERENCES study_sessions(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE SET NULL,
    title VARCHAR(200)
);

-- ============================================
-- FLASHCARD SYSTEM (with SM-2 Spaced Repetition)
-- ============================================

CREATE TABLE flashcard_decks (
    id SERIAL PRIMARY KEY,
    chapter_id INTEGER REFERENCES chapters(id) ON DELETE CASCADE,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    card_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_flashcard_decks_chapter ON flashcard_decks(chapter_id);

CREATE TABLE flashcards (
    id SERIAL PRIMARY KEY,
    deck_id INTEGER NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    hint TEXT,
    card_type VARCHAR(20) DEFAULT 'concept', -- 'concept', 'formula', 'code', 'definition'
    -- SM-2 spaced repetition algorithm fields
    ease_factor DECIMAL(4,2) DEFAULT 2.5 CHECK (ease_factor >= 1.3),
    interval_days INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review DATE DEFAULT CURRENT_DATE,
    last_reviewed_at TIMESTAMP WITH TIME ZONE,
    -- Performance tracking
    times_correct INTEGER DEFAULT 0,
    times_incorrect INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_flashcards_review ON flashcards(next_review, deck_id);
CREATE INDEX idx_flashcards_deck ON flashcards(deck_id);

-- Flashcard review history for analytics
CREATE TABLE flashcard_reviews (
    id SERIAL PRIMARY KEY,
    flashcard_id INTEGER NOT NULL REFERENCES flashcards(id) ON DELETE CASCADE,
    quality INTEGER NOT NULL CHECK (quality >= 0 AND quality <= 5),
    response_time_ms INTEGER,
    previous_interval INTEGER,
    new_interval INTEGER,
    reviewed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_flashcard_reviews_card ON flashcard_reviews(flashcard_id);

-- Formula cards (engineering-specific with LaTeX support)
CREATE TABLE formula_cards (
    id SERIAL PRIMARY KEY,
    deck_id INTEGER NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    latex_formula TEXT NOT NULL,
    plain_text VARCHAR(500),
    variables JSONB, -- {"m": "mass (kg)", "v": "velocity (m/s)"}
    unit VARCHAR(50),
    derivation_steps TEXT[],
    common_mistakes TEXT[],
    -- SM-2 fields
    ease_factor DECIMAL(4,2) DEFAULT 2.5,
    interval_days INTEGER DEFAULT 1,
    next_review DATE DEFAULT CURRENT_DATE,
    repetitions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STUDY GOALS SYSTEM
-- ============================================

CREATE TABLE goal_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    color VARCHAR(7) DEFAULT '#6366f1',
    icon VARCHAR(10) DEFAULT '🎯',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO goal_categories (name, color, icon, sort_order) VALUES
    ('Academic', '#3b82f6', '📚', 1),
    ('Skill Building', '#22c55e', '🛠️', 2),
    ('Personal', '#f59e0b', '🌟', 3),
    ('Career', '#8b5cf6', '💼', 4);

CREATE TABLE study_goals (
    id SERIAL PRIMARY KEY,
    category_id INTEGER REFERENCES goal_categories(id) ON DELETE SET NULL,
    subject_id INTEGER REFERENCES subjects(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    target_value INTEGER, -- e.g., "complete 10 chapters"
    current_value INTEGER DEFAULT 0,
    unit VARCHAR(50), -- e.g., "chapters", "hours", "assignments"
    deadline DATE,
    priority INTEGER DEFAULT 5 CHECK (priority >= 1 AND priority <= 10),
    completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_study_goals_deadline ON study_goals(deadline, completed);
CREATE INDEX idx_study_goals_category ON study_goals(category_id);

-- ============================================
-- ACHIEVEMENTS SYSTEM
-- ============================================

CREATE TYPE achievement_rarity AS ENUM ('common', 'rare', 'epic', 'legendary');

CREATE TABLE achievements (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10) NOT NULL,
    category VARCHAR(50), -- 'discipline', 'mastery', 'efficiency', 'streak'
    rarity achievement_rarity DEFAULT 'common',
    criteria_type VARCHAR(50) NOT NULL, -- 'deep_work_hours', 'flashcard_accuracy', 'streak_days'
    criteria_threshold INTEGER NOT NULL,
    points_reward INTEGER DEFAULT 0,
    unlocked BOOLEAN DEFAULT FALSE,
    unlocked_at TIMESTAMP WITH TIME ZONE,
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO achievements (code, name, description, icon, category, rarity, criteria_type, criteria_threshold, points_reward) VALUES
    ('deep_work_10', 'Focus Initiate', 'Complete 10 hours of deep work sessions', '🎯', 'discipline', 'common', 'deep_work_hours', 10, 50),
    ('deep_work_50', 'Deep Work Warrior', 'Complete 50 hours of deep work sessions', '⚔️', 'discipline', 'rare', 'deep_work_hours', 50, 200),
    ('deep_work_100', 'Focus Master', 'Complete 100 hours of deep work sessions', '🏆', 'discipline', 'epic', 'deep_work_hours', 100, 500),
    ('streak_7', 'Week Warrior', 'Maintain a 7-day study streak', '🔥', 'streak', 'common', 'streak_days', 7, 70),
    ('streak_30', 'Monthly Champion', 'Maintain a 30-day study streak', '💎', 'streak', 'epic', 'streak_days', 30, 300),
    ('streak_100', 'Legendary Learner', 'Maintain a 100-day study streak', '👑', 'streak', 'legendary', 'streak_days', 100, 1000),
    ('flashcard_100', 'Card Collector', 'Review 100 flashcards', '🃏', 'mastery', 'common', 'flashcards_reviewed', 100, 50),
    ('flashcard_1000', 'Memory Master', 'Review 1000 flashcards', '🧠', 'mastery', 'rare', 'flashcards_reviewed', 1000, 300),
    ('accuracy_90', 'Precision Student', 'Achieve 90% flashcard accuracy (min 50 reviews)', '🎯', 'mastery', 'rare', 'flashcard_accuracy', 90, 150),
    ('revisions_10', 'Revision Rookie', 'Complete 10 chapter revisions', '📖', 'discipline', 'common', 'revisions_completed', 10, 50),
    ('revisions_50', 'Revision Pro', 'Complete 50 chapter revisions', '📚', 'discipline', 'rare', 'revisions_completed', 50, 200),
    ('goals_5', 'Goal Getter', 'Complete 5 study goals', '🎯', 'efficiency', 'common', 'goals_completed', 5, 100),
    ('early_bird', 'Early Bird', 'Complete 10 study sessions before 06:00', '🌅', 'discipline', 'rare', 'early_sessions', 10, 150);

-- ============================================
-- AI TOKEN USAGE TRACKING
-- ============================================

CREATE TABLE ai_token_usage (
    id SERIAL PRIMARY KEY,
    usage_type VARCHAR(20) NOT NULL DEFAULT 'chat', -- 'chat', 'tool_call', 'flashcard_gen', 'image'
    tokens_used INTEGER NOT NULL,
    endpoint VARCHAR(100),
    model VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_token_usage_date ON ai_token_usage(created_at);

-- ============================================
-- QUICK SHARE SYSTEM
-- ============================================

CREATE TABLE quick_shares (
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) NOT NULL UNIQUE,
    resource_type VARCHAR(50) NOT NULL, -- 'file', 'chapter', 'flashcard_deck', 'goal'
    resource_id INTEGER NOT NULL,
    title VARCHAR(200),
    expires_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    max_access_count INTEGER, -- NULL = unlimited
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_quick_shares_code ON quick_shares(short_code);

CREATE TABLE share_access_logs (
    id SERIAL PRIMARY KEY,
    share_id INTEGER NOT NULL REFERENCES quick_shares(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    user_agent TEXT,
    accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- STUDY ANALYTICS AGGREGATES (for performance)
-- ============================================

CREATE TABLE daily_study_stats (
    id SERIAL PRIMARY KEY,
    stat_date DATE NOT NULL UNIQUE,
    total_study_seconds INTEGER DEFAULT 0,
    deep_work_seconds INTEGER DEFAULT 0,
    session_count INTEGER DEFAULT 0,
    flashcards_reviewed INTEGER DEFAULT 0,
    revisions_completed INTEGER DEFAULT 0,
    goals_progress INTEGER DEFAULT 0,
    points_earned INTEGER DEFAULT 0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_daily_stats_date ON daily_study_stats(stat_date);

-- ============================================
-- FUNCTIONS FOR NEW FEATURES
-- ============================================

-- Update daily stats when study session ends
CREATE OR REPLACE FUNCTION update_daily_study_stats()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.stopped_at IS NOT NULL AND OLD.stopped_at IS NULL THEN
        -- Calculate duration
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.stopped_at - NEW.started_at))::INTEGER;
        NEW.is_deep_work := NEW.duration_seconds >= 5400; -- 90 minutes

        -- Award points based on duration
        NEW.points_earned := LEAST(NEW.duration_seconds / 600, 50); -- 1 point per 10 mins, max 50

        -- Update daily stats
        INSERT INTO daily_study_stats (stat_date, total_study_seconds, deep_work_seconds, session_count, points_earned)
        VALUES (
            DATE(NEW.started_at),
            NEW.duration_seconds,
            CASE WHEN NEW.is_deep_work THEN NEW.duration_seconds ELSE 0 END,
            1,
            NEW.points_earned
        )
        ON CONFLICT (stat_date) DO UPDATE SET
            total_study_seconds = daily_study_stats.total_study_seconds + EXCLUDED.total_study_seconds,
            deep_work_seconds = daily_study_stats.deep_work_seconds + EXCLUDED.deep_work_seconds,
            session_count = daily_study_stats.session_count + 1,
            points_earned = daily_study_stats.points_earned + EXCLUDED.points_earned,
            updated_at = NOW();

        -- Add points to user streaks
        UPDATE user_streaks SET
            total_points = total_points + NEW.points_earned,
            updated_at = NOW();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_update_daily_stats
    BEFORE UPDATE ON study_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_daily_study_stats();

-- Update flashcard deck card count
CREATE OR REPLACE FUNCTION update_deck_card_count()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        UPDATE flashcard_decks SET card_count = card_count + 1, updated_at = NOW()
        WHERE id = NEW.deck_id;
    ELSIF TG_OP = 'DELETE' THEN
        UPDATE flashcard_decks SET card_count = card_count - 1, updated_at = NOW()
        WHERE id = OLD.deck_id;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_update_deck_count
    AFTER INSERT OR DELETE ON flashcards
    FOR EACH ROW
    EXECUTE FUNCTION update_deck_card_count();

-- Update streak on study session completion (30+ minutes)
CREATE OR REPLACE FUNCTION update_streak_on_session()
RETURNS TRIGGER AS $$
DECLARE
    last_date DATE;
    current_st INTEGER;
BEGIN
    IF NEW.stopped_at IS NOT NULL AND NEW.duration_seconds >= 1800 THEN -- 30 minutes minimum
        SELECT last_activity, current_streak INTO last_date, current_st FROM user_streaks LIMIT 1;

        IF last_date IS NULL OR last_date < CURRENT_DATE - 1 THEN
            UPDATE user_streaks SET current_streak = 1, last_activity = CURRENT_DATE, updated_at = NOW();
        ELSIF last_date = CURRENT_DATE - 1 THEN
            UPDATE user_streaks SET
                current_streak = current_streak + 1,
                longest_streak = GREATEST(longest_streak, current_streak + 1),
                last_activity = CURRENT_DATE,
                updated_at = NOW();
        ELSIF last_date < CURRENT_DATE THEN
            UPDATE user_streaks SET last_activity = CURRENT_DATE, updated_at = NOW();
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER tr_update_streak_session
    AFTER UPDATE ON study_sessions
    FOR EACH ROW
    WHEN (NEW.stopped_at IS NOT NULL AND OLD.stopped_at IS NULL)
    EXECUTE FUNCTION update_streak_on_session();

-- ============================================
-- COPILOTKIT AI-POWERED FEATURES
-- Version: 1.0.2
-- ============================================

-- ============================================
-- LEARNING PATTERNS TRACKING
-- ============================================

-- Track how users learn best for each subject
-- Stores aggregated learning analytics per subject to optimize scheduling
-- subject_code NULL means overall pattern across all subjects
CREATE TABLE learning_patterns (
    id SERIAL PRIMARY KEY,
    subject_code VARCHAR(20) UNIQUE,  -- NULL for overall pattern
    avg_session_duration_mins INTEGER DEFAULT 45,
    best_study_time VARCHAR(20) DEFAULT 'morning', -- 'early_morning', 'morning', 'afternoon', 'evening', 'night', 'late_night'
    best_day_of_week VARCHAR(20), -- 'monday', 'tuesday', etc.
    retention_rate DECIMAL(3,2) DEFAULT 0.70 CHECK (retention_rate >= 0.00 AND retention_rate <= 1.00),
    preferred_session_length INTEGER DEFAULT 45, -- in minutes
    break_frequency_mins INTEGER DEFAULT 60, -- recommended break interval
    effectiveness_score DECIMAL(4,3) DEFAULT 0.500 CHECK (effectiveness_score >= 0.000 AND effectiveness_score <= 1.000),
    deep_work_ratio DECIMAL(4,3) DEFAULT 0.000 CHECK (deep_work_ratio >= 0.000 AND deep_work_ratio <= 1.000),
    samples_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Track individual session effectiveness for granular analytics
CREATE TABLE session_effectiveness (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES study_sessions(id) ON DELETE CASCADE UNIQUE,
    subject_code VARCHAR(20),
    time_of_day VARCHAR(20) NOT NULL, -- 'early_morning', 'morning', 'afternoon', 'evening', 'night', 'late_night'
    day_of_week VARCHAR(20) NOT NULL, -- 'monday', 'tuesday', etc.
    duration_mins INTEGER NOT NULL CHECK (duration_mins > 0),
    focus_score DECIMAL(3,2) NOT NULL CHECK (focus_score >= 0.00 AND focus_score <= 1.00),
    material_covered TEXT,
    retention_test_score DECIMAL(3,2) CHECK (retention_test_score IS NULL OR (retention_test_score >= 0.00 AND retention_test_score <= 1.00)),
    is_deep_work BOOLEAN DEFAULT FALSE,
    energy_level INTEGER CHECK (energy_level IS NULL OR (energy_level >= 1 AND energy_level <= 10)),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_session_effectiveness_subject ON session_effectiveness(subject_code);
CREATE INDEX idx_session_effectiveness_time ON session_effectiveness(time_of_day);
CREATE INDEX idx_session_effectiveness_session ON session_effectiveness(session_id);
CREATE INDEX idx_session_effectiveness_day ON session_effectiveness(day_of_week);
CREATE INDEX idx_learning_patterns_subject ON learning_patterns(subject_code);

-- ============================================
-- ENHANCED ACHIEVEMENT SYSTEM
-- ============================================

-- Achievement definitions with richer metadata
CREATE TABLE achievement_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    icon VARCHAR(10) DEFAULT '🏆',
    category VARCHAR(50) NOT NULL, -- 'streak', 'study', 'goal', 'revision', 'special'
    threshold_value INTEGER NOT NULL DEFAULT 1,
    points INTEGER DEFAULT 10 CHECK (points >= 0),
    rarity VARCHAR(20) DEFAULT 'common' CHECK (rarity IN ('common', 'rare', 'epic', 'legendary')),
    is_hidden BOOLEAN DEFAULT FALSE,
    prerequisite_id INTEGER REFERENCES achievement_definitions(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User earned achievements with progress tracking
CREATE TABLE user_achievements (
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

CREATE INDEX idx_user_achievements_complete ON user_achievements(is_complete, notified);
CREATE INDEX idx_user_achievements_achievement ON user_achievements(achievement_id);

-- Progress snapshots for visualization
CREATE TABLE progress_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL UNIQUE,
    total_study_mins INTEGER DEFAULT 0,
    deep_work_mins INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    revisions_completed INTEGER DEFAULT 0,
    flashcards_reviewed INTEGER DEFAULT 0,
    goals_progress JSONB DEFAULT '{}',
    streak_count INTEGER DEFAULT 0,
    achievement_points INTEGER DEFAULT 0,
    subjects_studied JSONB DEFAULT '[]',
    energy_avg DECIMAL(3,1),
    focus_avg DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_progress_snapshots_date ON progress_snapshots(snapshot_date);

-- ============================================
-- ENHANCED NOTIFICATION SYSTEM
-- ============================================

-- Enhanced notifications with action support
CREATE TABLE notifications_v2 (
    id SERIAL PRIMARY KEY,
    type VARCHAR(50) NOT NULL, -- 'reminder', 'achievement', 'suggestion', 'warning', 'deadline', 'break'
    title VARCHAR(200) NOT NULL,
    message TEXT,
    priority VARCHAR(20) DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
    action_url VARCHAR(500),
    action_label VARCHAR(100),
    action_data JSONB,
    related_entity_type VARCHAR(50),
    related_entity_id INTEGER,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    dismissed_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_v2_scheduled ON notifications_v2(scheduled_for) WHERE scheduled_for IS NOT NULL AND sent_at IS NULL;
CREATE INDEX idx_notifications_v2_unread ON notifications_v2(read_at) WHERE read_at IS NULL AND dismissed_at IS NULL;
CREATE INDEX idx_notifications_v2_type ON notifications_v2(type);

-- Notification preferences per type
CREATE TABLE notification_preferences (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(50) NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT TRUE,
    quiet_hours_start TIME,
    quiet_hours_end TIME,
    frequency_limit INTEGER,
    channels JSONB DEFAULT '["app"]',
    custom_settings JSONB DEFAULT '{}',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO notification_preferences (notification_type, enabled, frequency_limit) VALUES
    ('reminder', TRUE, 10),
    ('achievement', TRUE, NULL),
    ('suggestion', TRUE, 5),
    ('warning', TRUE, NULL),
    ('deadline', TRUE, NULL),
    ('break', TRUE, 3);

-- ============================================
-- WELLBEING TRACKING
-- ============================================

-- Daily wellbeing metrics for burnout prevention
CREATE TABLE wellbeing_metrics (
    id SERIAL PRIMARY KEY,
    metric_date DATE NOT NULL UNIQUE,
    study_hours DECIMAL(4,2) DEFAULT 0.00,
    break_count INTEGER DEFAULT 0,
    break_total_mins INTEGER DEFAULT 0,
    deep_work_sessions INTEGER DEFAULT 0,
    task_completion_rate DECIMAL(3,2) CHECK (task_completion_rate IS NULL OR (task_completion_rate >= 0.00 AND task_completion_rate <= 1.00)),
    overdue_tasks INTEGER DEFAULT 0,
    stress_indicators JSONB DEFAULT '{}',
    wellbeing_score DECIMAL(3,2) CHECK (wellbeing_score IS NULL OR (wellbeing_score >= 0.00 AND wellbeing_score <= 1.00)),
    recommendations JSONB DEFAULT '[]',
    mood_rating INTEGER CHECK (mood_rating IS NULL OR (mood_rating >= 1 AND mood_rating <= 5)),
    energy_rating INTEGER CHECK (energy_rating IS NULL OR (energy_rating >= 1 AND energy_rating <= 5)),
    sleep_hours DECIMAL(3,1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_wellbeing_metrics_date ON wellbeing_metrics(metric_date);

-- Break sessions tracking
CREATE TABLE break_sessions (
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

CREATE INDEX idx_break_sessions_date ON break_sessions(started_at);
CREATE INDEX idx_break_sessions_type ON break_sessions(break_type);

-- Pomodoro timer status (singleton pattern - only one row)
CREATE TABLE pomodoro_status (
    id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    is_active BOOLEAN DEFAULT FALSE,
    current_phase VARCHAR(20) DEFAULT 'idle', -- 'work', 'short_break', 'long_break', 'idle'
    cycles_completed INTEGER DEFAULT 0,
    phase_started_at TIMESTAMP WITH TIME ZONE,
    cycle_started_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================
-- DEFAULT ACHIEVEMENT DEFINITIONS
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
    -- Special achievements
    ('perfectionist', 'Perfectionist', 'Complete all tasks for an entire week', '✨', 'special', 1, 75, 'epic'),
    ('hours_100', 'Century Study', 'Accumulate 100 hours of study time', '⏰', 'study', 100, 100, 'rare'),
    ('hours_500', 'Time Lord', 'Accumulate 500 hours of study time', '⌛', 'study', 500, 500, 'legendary'),
    ('balanced_week', 'Work-Life Balance', 'Take all suggested breaks for a week', '☯️', 'special', 1, 50, 'rare'),
    ('wellness_warrior', 'Wellness Warrior', 'Maintain wellbeing score above 0.8 for 7 days', '💚', 'special', 7, 75, 'epic');

-- ============================================
-- COPILOTKIT FUNCTIONS
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
    SELECT
        COALESCE(total_study_seconds / 60, 0),
        COALESCE(deep_work_seconds / 60, 0),
        COALESCE(flashcards_reviewed, 0),
        COALESCE(revisions_completed, 0),
        COALESCE(points_earned, 0)
    INTO total_study, deep_work, flashcards, revisions_done, points
    FROM daily_study_stats
    WHERE stat_date = snapshot_date_var;

    SELECT COUNT(*) INTO tasks_done
    FROM tasks
    WHERE status = 'completed'
    AND DATE(updated_at) = snapshot_date_var;

    SELECT current_streak INTO streak
    FROM user_streaks
    LIMIT 1;

    INSERT INTO progress_snapshots (
        snapshot_date, total_study_mins, deep_work_mins, tasks_completed,
        revisions_completed, flashcards_reviewed, streak_count, achievement_points
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

-- Function to update learning patterns from session effectiveness
-- This is a simple incremental update; the Python PatternAnalyzer does full analysis
CREATE OR REPLACE FUNCTION update_learning_pattern_from_session()
RETURNS TRIGGER AS $$
BEGIN
    -- Update or insert pattern for this subject
    INSERT INTO learning_patterns (
        subject_code, avg_session_duration_mins, best_study_time,
        preferred_session_length, effectiveness_score, samples_count, updated_at
    ) VALUES (
        NEW.subject_code, NEW.duration_mins, NEW.time_of_day,
        NEW.duration_mins, NEW.focus_score, 1, NOW()
    )
    ON CONFLICT (subject_code) DO UPDATE SET
        avg_session_duration_mins = (
            (learning_patterns.avg_session_duration_mins * learning_patterns.samples_count + NEW.duration_mins)
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

CREATE TRIGGER tr_update_learning_patterns
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
    score DECIMAL := 0.5;
    study_factor DECIMAL;
    break_factor DECIMAL;
    overdue_factor DECIMAL;
BEGIN
    IF p_study_hours >= 4 AND p_study_hours <= 8 THEN
        study_factor := 0.2;
    ELSIF p_study_hours > 8 THEN
        study_factor := -0.1 * (p_study_hours - 8);
    ELSE
        study_factor := 0.05 * p_study_hours;
    END IF;

    break_factor := LEAST(p_break_count * 0.05, 0.2);
    overdue_factor := -0.05 * p_overdue_tasks;

    score := GREATEST(0.00, LEAST(1.00, score + study_factor + break_factor + overdue_factor));

    RETURN score;
END;
$$ LANGUAGE plpgsql;

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
    SELECT COALESCE(total_study_seconds / 3600.0, 0)
    INTO study_hrs
    FROM daily_study_stats
    WHERE stat_date = today_date;

    SELECT COUNT(*), COALESCE(SUM(actual_duration_mins), 0)
    INTO breaks, break_mins
    FROM break_sessions
    WHERE DATE(started_at) = today_date AND was_completed = TRUE;

    SELECT COUNT(*)
    INTO deep_sessions
    FROM study_sessions
    WHERE DATE(started_at) = today_date AND is_deep_work = TRUE;

    SELECT COUNT(*)
    INTO overdue
    FROM tasks
    WHERE status = 'pending' AND scheduled_end < NOW();

    SELECT
        CASE
            WHEN COUNT(*) = 0 THEN NULL
            ELSE COUNT(*) FILTER (WHERE status = 'completed')::DECIMAL / COUNT(*)
        END
    INTO completion_rate
    FROM tasks
    WHERE DATE(scheduled_start) = today_date;

    wellbeing := calculate_wellbeing_score(
        COALESCE(study_hrs, 0),
        COALESCE(breaks, 0),
        COALESCE(overdue, 0),
        COALESCE(deep_sessions, 0)
    );

    INSERT INTO wellbeing_metrics (
        metric_date, study_hours, break_count, break_total_mins,
        deep_work_sessions, task_completion_rate, overdue_tasks,
        wellbeing_score, updated_at
    ) VALUES (
        today_date, COALESCE(study_hrs, 0), COALESCE(breaks, 0),
        COALESCE(break_mins, 0), COALESCE(deep_sessions, 0),
        completion_rate, COALESCE(overdue, 0), wellbeing, NOW()
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
    SELECT id, threshold_value
    INTO v_achievement_id, v_threshold
    FROM achievement_definitions
    WHERE code = p_achievement_code;

    IF v_achievement_id IS NULL THEN
        RETURN FALSE;
    END IF;

    SELECT is_complete INTO v_is_complete
    FROM user_achievements
    WHERE achievement_id = v_achievement_id;

    IF v_is_complete THEN
        RETURN FALSE;
    END IF;

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

CREATE TRIGGER tr_update_break_duration
    BEFORE UPDATE ON break_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_break_duration();
