-- Advanced Features for Production

-- Enable Full Text Search on conversation messages
ALTER TABLE conversation_messages ADD COLUMN IF NOT EXISTS search_vector tsvector;

CREATE INDEX IF NOT EXISTS idx_conversation_fts ON conversation_messages USING gin(search_vector);

-- Trigger to update search vector on message insert/update
CREATE OR REPLACE FUNCTION update_conversation_search_vector()
RETURNS TRIGGER AS $$
BEGIN
  NEW.search_vector := to_tsvector('english', COALESCE(NEW.message_text, ''));
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS conversation_search_vector_trigger ON conversation_messages;
CREATE TRIGGER conversation_search_vector_trigger
BEFORE INSERT OR UPDATE ON conversation_messages
FOR EACH ROW
EXECUTE FUNCTION update_conversation_search_vector();

-- Full text search function
CREATE OR REPLACE FUNCTION search_messages(search_query TEXT, session_id_filter UUID DEFAULT NULL)
RETURNS TABLE (
  id UUID,
  sender TEXT,
  message_text TEXT,
  created_at TIMESTAMP WITH TIME ZONE,
  relevance FLOAT
) AS $$
SELECT
  cm.id,
  cm.sender,
  cm.message_text,
  cm.created_at,
  ts_rank(cm.search_vector, plainto_tsquery('english', $1))::FLOAT as relevance
FROM conversation_messages cm
WHERE cm.search_vector @@ plainto_tsquery('english', $1)
  AND (session_id_filter IS NULL OR cm.session_id = session_id_filter)
ORDER BY relevance DESC
LIMIT 50
$$ LANGUAGE SQL STABLE;

-- Table for event logs (for monitoring and debugging)
CREATE TABLE IF NOT EXISTS event_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  event_data JSONB,
  metadata JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_event_logs_user_id ON event_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_event_type ON event_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at);

-- Function to log events
CREATE OR REPLACE FUNCTION log_event(
  user_id_param UUID,
  event_type_param TEXT,
  event_data_param JSONB DEFAULT NULL,
  metadata_param JSONB DEFAULT NULL
)
RETURNS void AS $$
INSERT INTO event_logs (user_id, event_type, event_data, metadata)
VALUES (user_id_param, event_type_param, event_data_param, metadata_param);
$$ LANGUAGE SQL;

-- View: Daily conversation metrics
CREATE OR REPLACE VIEW daily_metrics AS
SELECT
  DATE(cm.created_at) as date,
  COUNT(DISTINCT cm.session_id) as unique_sessions,
  COUNT(DISTINCT cm.user_id) as unique_users,
  COUNT(*) as total_messages,
  COUNT(CASE WHEN cm.sender = 'user' THEN 1 END) as user_messages,
  COUNT(CASE WHEN cm.sender = 'agent' THEN 1 END) as agent_messages,
  COUNT(DISTINCT a.id) FILTER (WHERE a.created_at::date = DATE(cm.created_at)) as appointments_created
FROM conversation_messages cm
LEFT JOIN appointments a ON cm.user_id = a.user_id
GROUP BY DATE(cm.created_at)
ORDER BY DATE(cm.created_at) DESC;

-- View: User retention (based on repeat sessions)
CREATE OR REPLACE VIEW user_retention AS
SELECT
  u.id,
  u.name,
  u.email,
  COUNT(DISTINCT s.id) as total_sessions,
  MIN(s.created_at) as first_session,
  MAX(s.created_at) as last_session,
  CASE
    WHEN COUNT(DISTINCT s.id) = 1 THEN 'single'
    WHEN COUNT(DISTINCT s.id) BETWEEN 2 AND 5 THEN 'occasional'
    WHEN COUNT(DISTINCT s.id) > 5 THEN 'frequent'
  END as engagement_level,
  CASE
    WHEN MAX(s.created_at) > now() - INTERVAL '7 days' THEN 'active'
    WHEN MAX(s.created_at) > now() - INTERVAL '30 days' THEN 'dormant'
    ELSE 'inactive'
  END as status
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
GROUP BY u.id, u.name, u.email
ORDER BY MAX(s.created_at) DESC;

-- Function: Get conversation transcript for a session
CREATE OR REPLACE FUNCTION get_session_transcript(session_id_param UUID)
RETURNS TABLE (
  order_num INTEGER,
  sender TEXT,
  message TEXT,
  created_at TIMESTAMP WITH TIME ZONE
) AS $$
SELECT
  ROW_NUMBER() OVER (ORDER BY cm.created_at ASC)::INTEGER,
  cm.sender,
  cm.message_text,
  cm.created_at
FROM conversation_messages cm
WHERE cm.session_id = $1
ORDER BY cm.created_at ASC
$$ LANGUAGE SQL STABLE;

-- Table for storing audit logs
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  table_name TEXT NOT NULL,
  record_id UUID,
  action TEXT NOT NULL,
  old_data JSONB,
  new_data JSONB,
  changed_by TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_table_name ON audit_logs(table_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_record_id ON audit_logs(record_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);

-- Function: Calculate session health score (0-100)
CREATE OR REPLACE FUNCTION get_session_health_score(session_id_param UUID)
RETURNS INTEGER AS $$
DECLARE
  message_count INTEGER;
  appointment_created BOOLEAN;
  avg_response_time FLOAT;
  score INTEGER := 0;
BEGIN
  -- Count messages
  SELECT COUNT(*) INTO message_count
  FROM conversation_messages
  WHERE session_id = session_id_param;

  score := score + LEAST(message_count * 10, 40); -- Max 40 points for messages

  -- Check if appointment was created
  SELECT EXISTS(SELECT 1 FROM appointments WHERE session_id = session_id_param)
  INTO appointment_created;

  IF appointment_created THEN
    score := score + 40;
  END IF;

  -- Check engagement (25 points for having scraped content)
  IF EXISTS(SELECT 1 FROM scraped_content WHERE session_id = session_id_param) THEN
    score := score + 20;
  END IF;

  RETURN LEAST(score, 100);
END
$$ LANGUAGE plpgsql;
