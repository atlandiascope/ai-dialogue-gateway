CREATE TABLE IF NOT EXISTS gateway_agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(80) NOT NULL,
  description VARCHAR(280) NOT NULL DEFAULT '',
  api_key_hash TEXT NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  disabled_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS gateway_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  sender_id UUID NOT NULL REFERENCES gateway_agents(id),
  recipient_id UUID NOT NULL REFERENCES gateway_agents(id),
  body TEXT NOT NULL CHECK (char_length(body) BETWEEN 1 AND 4000),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS gateway_messages_recipient_created_idx
  ON gateway_messages (recipient_id, created_at);

CREATE TABLE IF NOT EXISTS gateway_daily_usage (
  agent_id UUID NOT NULL REFERENCES gateway_agents(id) ON DELETE CASCADE,
  usage_day DATE NOT NULL DEFAULT CURRENT_DATE,
  message_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (agent_id, usage_day)
);
