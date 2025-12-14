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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Lab reports
CREATE TABLE lab_reports (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    status task_status DEFAULT 'pending',
    notes TEXT,
    file_path VARCHAR(500),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

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
