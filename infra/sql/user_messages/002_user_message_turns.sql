CREATE TABLE IF NOT EXISTS user_message_turns (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES app_users(id) ON DELETE SET NULL,
    conversation_owner_key TEXT NOT NULL,
    client_user_label TEXT NOT NULL DEFAULT '',
    user_request TEXT NOT NULL,
    model_answer TEXT NOT NULL,
    routed_agent TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_message_turns_owner_created_at
    ON user_message_turns (conversation_owner_key, created_at);

CREATE INDEX IF NOT EXISTS ix_user_message_turns_trace_id
    ON user_message_turns (trace_id);
