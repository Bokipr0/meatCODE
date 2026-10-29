-- 0019 — Explicitly consented Oracle transcript research (2026-10-29).
-- Additive private table only; no scientific records or reviewer grants changed.
-- Historical consent rows remain valid; new transcript capture requires a fresh opt-in.
BEGIN;
SET LOCAL lock_timeout='3s';
SET LOCAL statement_timeout='15s';
ALTER TABLE user_research.sessions DROP CONSTRAINT sessions_consent_version_check;
ALTER TABLE user_research.sessions ADD CONSTRAINT sessions_consent_version_check
 CHECK (consent_version IN ('2026-10-28','2026-10-29','2026-10-29-chat-v1'));
CREATE TABLE IF NOT EXISTS user_research.oracle_turns (
 turn_id uuid NOT NULL,
 environment text NOT NULL CHECK(environment IN ('dev','prod')),
 session_id uuid NOT NULL,
 conversation_id uuid NOT NULL,
 turn_index integer NOT NULL CHECK(turn_index BETWEEN 1 AND 1000000),
 question text NOT NULL CHECK(char_length(question) BETWEEN 1 AND 12000),
 answer text NOT NULL DEFAULT '' CHECK(char_length(answer)<=64000),
 status text NOT NULL CHECK(status IN ('submitted','complete','failed','clarification','interrupted')),
 revision integer NOT NULL CHECK(revision BETWEEN 0 AND 1000000),
 source_ids bigint[] NOT NULL DEFAULT '{}' CHECK(cardinality(source_ids)<=100),
 error_code text CHECK(error_code IN ('network','model_unavailable','session_expired','unknown')),
 truncated boolean NOT NULL DEFAULT false,
 consent_version text NOT NULL CHECK(consent_version='2026-10-29-chat-v1'),
 consent_at timestamptz NOT NULL DEFAULT now(),
 created_at timestamptz NOT NULL DEFAULT now(),
 updated_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(turn_id,environment),
 UNIQUE(conversation_id,turn_index,environment),
 FOREIGN KEY(session_id,environment) REFERENCES user_research.sessions(session_id,environment) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ur_oracle_session ON user_research.oracle_turns(environment,session_id);
CREATE INDEX IF NOT EXISTS ur_oracle_updated ON user_research.oracle_turns(environment,updated_at);
REVOKE ALL ON user_research.oracle_turns FROM PUBLIC;
COMMENT ON TABLE user_research.oracle_turns IS 'Optional explicit full-chat research consent; question/answer text stays first-party, never Clarity/PostHog. Browser-observed transcript, not authoritative model audit.';
COMMIT;
