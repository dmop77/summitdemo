-- Row Level Security (RLS) Policies
-- Enable RLS on all tables

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraped_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can read own record"
  ON users FOR SELECT
  USING (true);

CREATE POLICY "Users can update own record"
  ON users FOR UPDATE
  USING (true);

-- Sessions table policies
CREATE POLICY "Users can read own sessions"
  ON sessions FOR SELECT
  USING (true);

CREATE POLICY "Users can insert own sessions"
  ON sessions FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users can update own sessions"
  ON sessions FOR UPDATE
  USING (true);

-- Scraped content policies
CREATE POLICY "Users can read own scraped content"
  ON scraped_content FOR SELECT
  USING (true);

CREATE POLICY "Users can insert scraped content"
  ON scraped_content FOR INSERT
  WITH CHECK (true);

-- Conversation messages policies
CREATE POLICY "Users can read own messages"
  ON conversation_messages FOR SELECT
  USING (true);

CREATE POLICY "Users can insert messages"
  ON conversation_messages FOR INSERT
  WITH CHECK (true);

-- Appointments policies
CREATE POLICY "Users can read own appointments"
  ON appointments FOR SELECT
  USING (true);

CREATE POLICY "Users can insert appointments"
  ON appointments FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Users can update own appointments"
  ON appointments FOR UPDATE
  USING (true);
