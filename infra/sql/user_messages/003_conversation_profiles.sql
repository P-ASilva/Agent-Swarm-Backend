CREATE TABLE IF NOT EXISTS conversation_profiles (
    conversation_owner_key TEXT PRIMARY KEY,
    display_name TEXT,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_conversation_profiles_updated_at
    ON conversation_profiles (updated_at);
