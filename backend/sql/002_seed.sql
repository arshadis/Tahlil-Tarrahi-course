INSERT INTO users (username, full_name, email, password_hash, role)
VALUES
('admin', 'مدیر سیستم', 'admin@example.local', '$2b$12$3qXoYyBfDn.XcHdh.6o1jO2ptSPy5TrF72zWnMrd9duEJ4uZsQ/gy', 'admin')
ON CONFLICT (username) DO NOTHING;

INSERT INTO app_settings (setting_key, setting_value)
VALUES
('game_start_time', '08:00'),
('game_end_time', '17:00'),
('questions_per_stage', '10'),
('delay_penalty', '20'),
('leaderboard_enabled', 'true'),
('chat_enabled', 'false')
ON CONFLICT (setting_key) DO NOTHING;
