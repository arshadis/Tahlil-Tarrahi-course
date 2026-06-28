CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    full_name VARCHAR(150),
    email VARCHAR(150) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'user',
    total_score INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    question_type VARCHAR(30) NOT NULL CHECK (question_type IN ('multiple_choice', 'fill_blank', 'image')),
    difficulty VARCHAR(30) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    topic VARCHAR(100) NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT,
    image_url VARCHAR(500),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS question_options (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    option_text TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS daily_stages (
    id SERIAL PRIMARY KEY,
    stage_date DATE UNIQUE NOT NULL,
    difficulty VARCHAR(30) NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    question_count INTEGER NOT NULL,
    max_score INTEGER NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stage_questions (
    id SERIAL PRIMARY KEY,
    stage_id INTEGER NOT NULL REFERENCES daily_stages(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_game_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    stage_id INTEGER NOT NULL REFERENCES daily_stages(id),
    status VARCHAR(30) NOT NULL DEFAULT 'in_progress'
        CHECK (status IN ('in_progress', 'paused', 'completed', 'expired')),
    current_question_index INTEGER NOT NULL DEFAULT 0,
    score INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    paused_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_answers (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES user_game_sessions(id) ON DELETE CASCADE,
    question_id INTEGER NOT NULL REFERENCES questions(id),
    user_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    score_earned INTEGER NOT NULL DEFAULT 0,
    answered_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app_settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL
);
