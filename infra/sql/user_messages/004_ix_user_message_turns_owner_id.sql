CREATE INDEX IF NOT EXISTS ix_user_message_turns_owner_id
    ON user_message_turns (conversation_owner_key, id);
