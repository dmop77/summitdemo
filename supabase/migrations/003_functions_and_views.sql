-- Useful Functions and Views for Voice Agent

-- Get user statistics
CREATE OR REPLACE FUNCTION get_user_stats(user_id UUID)
RETURNS TABLE (
  sessions_count BIGINT,
  messages_count BIGINT,
  appointments_count BIGINT,
  total_message_duration_ms BIGINT,
  last_session TIMESTAMP WITH TIME ZONE
) AS $$
SELECT
  (SELECT COUNT(*) FROM sessions WHERE sessions.user_id = $1)::BIGINT,
  (SELECT COUNT(*) FROM conversation_messages WHERE conversation_messages.user_id = $1)::BIGINT,
  (SELECT COUNT(*) FROM appointments WHERE appointments.user_id = $1)::BIGINT,
  (SELECT COALESCE(SUM(audio_duration_ms), 0) FROM conversation_messages WHERE conversation_messages.user_id = $1)::BIGINT,
  (SELECT MAX(created_at) FROM sessions WHERE sessions.user_id = $1)
$$ LANGUAGE SQL STABLE;

-- Get session summary
CREATE OR REPLACE FUNCTION get_session_summary(session_id UUID)
RETURNS TABLE (
  user_name TEXT,
  user_email TEXT,
  message_count BIGINT,
  user_messages BIGINT,
  agent_messages BIGINT,
  session_duration_minutes FLOAT,
  status TEXT
) AS $$
SELECT
  u.name,
  u.email,
  COUNT(cm.id)::BIGINT,
  COUNT(CASE WHEN cm.sender = 'user' THEN 1 END)::BIGINT,
  COUNT(CASE WHEN cm.sender = 'agent' THEN 1 END)::BIGINT,
  EXTRACT(EPOCH FROM (MAX(cm.created_at) - MIN(cm.created_at)))/60::FLOAT,
  s.status
FROM sessions s
LEFT JOIN users u ON s.user_id = u.id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
WHERE s.id = $1
GROUP BY u.id, u.name, u.email, s.status
$$ LANGUAGE SQL STABLE;

-- View: Recent sessions with user info
CREATE OR REPLACE VIEW recent_sessions AS
SELECT
  s.id,
  s.session_id,
  u.name,
  u.email,
  u.website_url,
  s.website_summary,
  s.status,
  s.created_at,
  (SELECT COUNT(*) FROM conversation_messages WHERE session_id = s.id) as message_count
FROM sessions s
LEFT JOIN users u ON s.user_id = u.id
ORDER BY s.created_at DESC;

-- View: Upcoming appointments
CREATE OR REPLACE VIEW upcoming_appointments AS
SELECT
  a.id,
  a.topic,
  a.preferred_date,
  u.name,
  u.email,
  a.status,
  a.summary_notes,
  a.created_at
FROM appointments a
LEFT JOIN users u ON a.user_id = u.id
WHERE a.preferred_date > now()
  AND a.status = 'scheduled'
ORDER BY a.preferred_date ASC;

-- View: Conversation analytics by session
CREATE OR REPLACE VIEW conversation_analytics AS
SELECT
  s.session_id,
  u.name,
  COUNT(CASE WHEN cm.sender = 'user' THEN 1 END) as user_message_count,
  COUNT(CASE WHEN cm.sender = 'agent' THEN 1 END) as agent_message_count,
  AVG(CASE WHEN cm.audio_duration_ms > 0 THEN cm.audio_duration_ms END)::INTEGER as avg_user_audio_duration_ms,
  MIN(cm.created_at) as first_message,
  MAX(cm.created_at) as last_message,
  EXTRACT(EPOCH FROM (MAX(cm.created_at) - MIN(cm.created_at)))/60::FLOAT as session_duration_minutes
FROM sessions s
LEFT JOIN users u ON s.user_id = u.id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
GROUP BY s.id, s.session_id, u.id, u.name
ORDER BY MAX(cm.created_at) DESC;

-- Function: Archive old sessions
CREATE OR REPLACE FUNCTION archive_old_sessions(days_old INTEGER DEFAULT 90)
RETURNS TABLE (archived_count INTEGER) AS $$
UPDATE sessions
SET status = 'abandoned'
WHERE status = 'active'
  AND created_at < now() - (days_old || ' days')::INTERVAL
RETURNING 1
$$ LANGUAGE SQL;

-- Function: Get latest session for user
CREATE OR REPLACE FUNCTION get_latest_user_session(user_email TEXT)
RETURNS TABLE (
  session_id TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  message_count BIGINT,
  website_summary TEXT
) AS $$
SELECT
  s.session_id,
  s.created_at,
  COUNT(cm.id)::BIGINT,
  s.website_summary
FROM sessions s
LEFT JOIN users u ON s.user_id = u.id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
WHERE u.email = $1
GROUP BY s.id, s.session_id, s.created_at, s.website_summary
ORDER BY s.created_at DESC
LIMIT 1
$$ LANGUAGE SQL STABLE;
