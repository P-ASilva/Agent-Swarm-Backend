CREATE TABLE IF NOT EXISTS app_users (
    id UUID PRIMARY KEY,
    google_subject TEXT NOT NULL UNIQUE,
    email TEXT,
    issuer TEXT,
    audience TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_app_users_google_subject
    ON app_users (google_subject);
