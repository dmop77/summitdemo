-- Useful Queries for Voice Agent Analytics and Monitoring

-- Get all conversations in the last 7 days
SELECT
  u.name,
  u.email,
  s.session_id,
  COUNT(cm.id) as message_count,
  MIN(cm.created_at) as first_message,
  MAX(cm.created_at) as last_message,
  COUNT(CASE WHEN a.id IS NOT NULL THEN 1 END) as appointments_scheduled
FROM sessions s
JOIN users u ON s.user_id = u.id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
LEFT JOIN appointments a ON s.id = a.session_id
WHERE s.created_at > now() - INTERVAL '7 days'
GROUP BY u.id, u.name, u.email, s.id, s.session_id
ORDER BY MAX(cm.created_at) DESC;

-- Get user engagement summary
SELECT
  u.id,
  u.name,
  u.email,
  COUNT(DISTINCT s.id) as total_sessions,
  COUNT(DISTINCT cm.id) as total_messages,
  COUNT(DISTINCT a.id) as total_appointments,
  MAX(s.created_at) as last_activity
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
LEFT JOIN appointments a ON u.id = a.user_id
GROUP BY u.id, u.name, u.email
ORDER BY MAX(s.created_at) DESC;

-- Get conversion rate (users who scheduled appointments)
SELECT
  COUNT(DISTINCT u.id) as total_users,
  COUNT(DISTINCT a.user_id) as users_with_appointments,
  ROUND(100.0 * COUNT(DISTINCT a.user_id) / COUNT(DISTINCT u.id), 2) as conversion_rate_percent
FROM users u
LEFT JOIN appointments a ON u.id = a.user_id;

-- Get average session duration
SELECT
  AVG(EXTRACT(EPOCH FROM (max_time - min_time))/60) as avg_duration_minutes,
  STDDEV(EXTRACT(EPOCH FROM (max_time - min_time))/60) as stddev_duration_minutes,
  MIN(EXTRACT(EPOCH FROM (max_time - min_time))/60) as min_duration_minutes,
  MAX(EXTRACT(EPOCH FROM (max_time - min_time))/60) as max_duration_minutes
FROM (
  SELECT
    s.id,
    MIN(cm.created_at) as min_time,
    MAX(cm.created_at) as max_time
  FROM sessions s
  LEFT JOIN conversation_messages cm ON s.id = cm.session_id
  GROUP BY s.id
) subquery;

-- Get scraping success rate
SELECT
  COUNT(DISTINCT s.id) as total_sessions,
  COUNT(DISTINCT sc.id) as sessions_with_scrape,
  ROUND(100.0 * COUNT(DISTINCT sc.id) / COUNT(DISTINCT s.id), 2) as scrape_success_rate_percent,
  COUNT(DISTINCT sc.url) as unique_domains_scraped
FROM sessions s
LEFT JOIN scraped_content sc ON s.id = sc.session_id;

-- Get top discussed topics (most common appointment topics)
SELECT
  topic,
  COUNT(*) as frequency,
  COUNT(DISTINCT user_id) as unique_users,
  status
FROM appointments
GROUP BY topic, status
ORDER BY frequency DESC
LIMIT 20;

-- Get user by email with all related data
-- Replace 'user@example.com' with actual email
SELECT
  u.id,
  u.name,
  u.email,
  u.website_url,
  u.created_at,
  COUNT(DISTINCT s.id) as session_count,
  COUNT(DISTINCT cm.id) as message_count,
  COUNT(DISTINCT a.id) as appointment_count
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
LEFT JOIN appointments a ON u.id = a.user_id
WHERE u.email = 'user@example.com'
GROUP BY u.id, u.name, u.email, u.website_url, u.created_at;

-- Get session conversation flow (who spoke when)
-- Replace 'session-id-here' with actual session ID
SELECT
  ROW_NUMBER() OVER (ORDER BY cm.created_at) as turn_number,
  cm.sender,
  cm.message_text,
  cm.created_at,
  EXTRACT(EPOCH FROM (cm.created_at - LAG(cm.created_at) OVER (ORDER BY cm.created_at))) as seconds_since_last_message
FROM conversation_messages cm
WHERE cm.session_id = (
  SELECT id FROM sessions WHERE session_id = 'session-id-here' LIMIT 1
)
ORDER BY cm.created_at;

-- Get appointment scheduling pipeline
SELECT
  CASE
    WHEN a.status = 'scheduled' THEN 'Scheduled'
    WHEN a.status = 'completed' THEN 'Completed'
    WHEN a.status = 'cancelled' THEN 'Cancelled'
    WHEN a.status = 'no-show' THEN 'No Show'
  END as status,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM appointments
GROUP BY a.status
ORDER BY count DESC;

-- Monitor database table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Find slow or incomplete conversations (messages but no appointment)
SELECT
  u.name,
  u.email,
  s.session_id,
  COUNT(cm.id) as message_count,
  MAX(cm.created_at) as last_message_time,
  CASE
    WHEN COUNT(CASE WHEN a.id IS NOT NULL THEN 1 END) > 0 THEN 'Converted'
    ELSE 'No Appointment'
  END as outcome
FROM sessions s
JOIN users u ON s.user_id = u.id
LEFT JOIN conversation_messages cm ON s.id = cm.session_id
LEFT JOIN appointments a ON s.id = a.session_id
WHERE s.created_at > now() - INTERVAL '30 days'
GROUP BY u.id, u.name, u.email, s.id, s.session_id
HAVING COUNT(cm.id) >= 3
ORDER BY message_count DESC;

-- Export user data (GDPR compliance - get all user's data)
-- Replace 'user@example.com' with actual email
SELECT 'user' as data_type, row_to_json(u) as data
FROM users u
WHERE u.email = 'user@example.com'
UNION ALL
SELECT 'session', row_to_json(s)
FROM sessions s
WHERE s.user_id = (SELECT id FROM users WHERE email = 'user@example.com')
UNION ALL
SELECT 'message', row_to_json(cm)
FROM conversation_messages cm
WHERE cm.user_id = (SELECT id FROM users WHERE email = 'user@example.com')
UNION ALL
SELECT 'appointment', row_to_json(a)
FROM appointments a
WHERE a.user_id = (SELECT id FROM users WHERE email = 'user@example.com');
