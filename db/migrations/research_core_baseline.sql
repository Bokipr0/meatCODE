-- Fresh production research database only. Schema snapshot through 0027, restricted to the four intake tables.
BEGIN;
DO $guard$ BEGIN
 IF current_database()<>'research_prod' THEN RAISE EXCEPTION 'Requires dedicated research_prod'; END IF;
END $guard$;
CREATE SCHEMA IF NOT EXISTS user_research;
REVOKE ALL ON SCHEMA user_research FROM PUBLIC;
CREATE TABLE user_research.events (
    event_id uuid NOT NULL,
    environment text NOT NULL,
    session_id uuid NOT NULL,
    name text NOT NULL,
    scene text NOT NULL,
    duration_ms integer,
    error_code text,
    source_count integer,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    elapsed_ms bigint,
    CONSTRAINT events_duration_ms_check CHECK (((duration_ms >= 0) AND (duration_ms <= 3600000))),
    CONSTRAINT events_elapsed_ms_check CHECK (((elapsed_ms >= 0) AND (elapsed_ms <= 86400000))),
    CONSTRAINT events_environment_check CHECK ((environment = ANY (ARRAY['dev'::text, 'prod'::text]))),
    CONSTRAINT events_error_code_check CHECK ((error_code = ANY (ARRAY['network'::text, 'model_unavailable'::text, 'session_expired'::text, 'unknown'::text]))),
    CONSTRAINT events_name_check CHECK ((name = ANY (ARRAY['session.started'::text, 'scene.viewed'::text, 'module.clicked'::text, 'oracle.submitted'::text, 'oracle.completed'::text, 'oracle.failed'::text, 'feedback.submitted'::text]))),
    CONSTRAINT events_scene_check CHECK ((scene = ANY (ARRAY['oracle'::text, 'research'::text, 'science'::text, 'ecosystem'::text, 'simulate'::text, 'analytics'::text, 'database'::text, 'map'::text, 'papers'::text, 'dev'::text, 'inventory'::text, 'other'::text]))),
    CONSTRAINT events_source_count_check CHECK (((source_count >= 0) AND (source_count <= 1000))),
    CONSTRAINT research_production_only CHECK ((environment = 'prod'::text))
);
CREATE TABLE user_research.feedback (
    event_id uuid NOT NULL,
    environment text NOT NULL,
    session_id uuid NOT NULL,
    rating text,
    category text NOT NULL,
    comment text DEFAULT ''::text NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    elapsed_ms bigint,
    source text DEFAULT 'feedback'::text NOT NULL,
    context jsonb DEFAULT '{}'::jsonb NOT NULL,
    CONSTRAINT feedback_category_check CHECK ((category = ANY (ARRAY['answer'::text, 'usability'::text, 'bug'::text, 'other'::text]))),
    CONSTRAINT feedback_comment_check CHECK ((char_length(comment) <= 2000)),
    CONSTRAINT feedback_context_check CHECK ((jsonb_typeof(context) = 'object'::text)),
    CONSTRAINT feedback_elapsed_ms_check CHECK (((elapsed_ms >= 0) AND (elapsed_ms <= 86400000))),
    CONSTRAINT feedback_environment_check CHECK ((environment = ANY (ARRAY['dev'::text, 'prod'::text]))),
    CONSTRAINT feedback_rating_check CHECK ((rating = ANY (ARRAY['helpful'::text, 'neutral'::text, 'unhelpful'::text]))),
    CONSTRAINT feedback_rating_or_note CHECK (((source = 'denver'::text) OR (rating IS NOT NULL))),
    CONSTRAINT feedback_source_check CHECK ((source = ANY (ARRAY['feedback'::text, 'denver'::text]))),
    CONSTRAINT research_production_only CHECK ((environment = 'prod'::text))
);
COMMENT ON TABLE user_research.feedback IS 'Private first-party feedback, joined to the tester session; never forwarded to analytics providers.';
COMMENT ON COLUMN user_research.feedback.context IS 'Server-checked note anchors, capture elapsed time, and explicit missing-context status. Never an account identity.';
CREATE TABLE user_research.oracle_turns (
    turn_id uuid NOT NULL,
    environment text NOT NULL,
    session_id uuid NOT NULL,
    conversation_id uuid NOT NULL,
    turn_index integer NOT NULL,
    question text NOT NULL,
    answer text DEFAULT ''::text NOT NULL,
    status text NOT NULL,
    revision integer NOT NULL,
    source_ids bigint[] DEFAULT '{}'::bigint[] NOT NULL,
    error_code text,
    truncated boolean DEFAULT false NOT NULL,
    consent_version text NOT NULL,
    consent_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    elapsed_ms bigint,
    CONSTRAINT oracle_turns_answer_check CHECK ((char_length(answer) <= 64000)),
    CONSTRAINT oracle_turns_consent_version_check CHECK ((consent_version = ANY (ARRAY['2026-10-29-chat-v1'::text, '2026-10-29-journey-v1'::text, '2026-10-29-demo-v1'::text]))),
    CONSTRAINT oracle_turns_elapsed_ms_check CHECK (((elapsed_ms >= 0) AND (elapsed_ms <= 86400000))),
    CONSTRAINT oracle_turns_environment_check CHECK ((environment = ANY (ARRAY['dev'::text, 'prod'::text]))),
    CONSTRAINT oracle_turns_error_code_check CHECK ((error_code = ANY (ARRAY['network'::text, 'model_unavailable'::text, 'session_expired'::text, 'unknown'::text]))),
    CONSTRAINT oracle_turns_question_check CHECK (((char_length(question) >= 1) AND (char_length(question) <= 12000))),
    CONSTRAINT oracle_turns_revision_check CHECK (((revision >= 0) AND (revision <= 1000000))),
    CONSTRAINT oracle_turns_source_ids_check CHECK ((cardinality(source_ids) <= 100)),
    CONSTRAINT oracle_turns_status_check CHECK ((status = ANY (ARRAY['submitted'::text, 'complete'::text, 'failed'::text, 'clarification'::text, 'interrupted'::text]))),
    CONSTRAINT oracle_turns_turn_index_check CHECK (((turn_index >= 1) AND (turn_index <= 1000000))),
    CONSTRAINT research_production_only CHECK ((environment = 'prod'::text))
);
COMMENT ON TABLE user_research.oracle_turns IS 'Optional explicit full-chat research consent; question/answer text stays first-party, never Clarity/PostHog. Browser-observed transcript, not authoritative model audit.';
COMMENT ON COLUMN user_research.oracle_turns.elapsed_ms IS 'Browser-observed elapsed milliseconds since joining this tab testing journey, sampled on question submission; NULL means unknown.';
CREATE TABLE user_research.sessions (
    session_id uuid NOT NULL,
    environment text NOT NULL,
    consent_version text NOT NULL,
    consent_at timestamp with time zone DEFAULT now() NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_seen_at timestamp with time zone DEFAULT now() NOT NULL,
    user_ref uuid,
    clarity_ref uuid,
    tester_label character varying(80),
    CONSTRAINT research_production_only CHECK ((environment = 'prod'::text)),
    CONSTRAINT sessions_consent_version_check CHECK ((consent_version = ANY (ARRAY['2026-10-28'::text, '2026-10-29'::text, '2026-10-29-chat-v1'::text, '2026-10-29-journey-v1'::text, '2026-10-29-demo-v1'::text]))),
    CONSTRAINT sessions_environment_check CHECK ((environment = ANY (ARRAY['dev'::text, 'prod'::text]))),
    CONSTRAINT ur_distinct_journey_refs CHECK (((user_ref IS DISTINCT FROM session_id) AND (clarity_ref IS DISTINCT FROM session_id) AND ((user_ref IS NULL) OR (clarity_ref IS NULL) OR (user_ref <> clarity_ref))))
);
COMMENT ON COLUMN user_research.sessions.consent_version IS 'Policy version: demo-v1 denotes owner-directed first-use activation, journey/chat versions denote explicit opt-in. Do not interpret demo as checkbox consent.';
COMMENT ON COLUMN user_research.sessions.user_ref IS 'Optional consented tab pseudonym; not an account identifier or session deletion capability.';
COMMENT ON COLUMN user_research.sessions.clarity_ref IS 'Opaque reference sent as Clarity research_reference tag only after explicit journey-sharing consent; never session_id.';
ALTER TABLE ONLY user_research.events
    ADD CONSTRAINT events_pkey PRIMARY KEY (event_id, environment);
ALTER TABLE ONLY user_research.feedback
    ADD CONSTRAINT feedback_pkey PRIMARY KEY (event_id, environment);
ALTER TABLE ONLY user_research.oracle_turns
    ADD CONSTRAINT oracle_turns_conversation_id_turn_index_environment_key UNIQUE (conversation_id, turn_index, environment);
ALTER TABLE ONLY user_research.oracle_turns
    ADD CONSTRAINT oracle_turns_pkey PRIMARY KEY (turn_id, environment);
ALTER TABLE ONLY user_research.sessions
    ADD CONSTRAINT sessions_pkey PRIMARY KEY (session_id, environment);
CREATE INDEX ur_events_created ON user_research.events USING btree (created_at);
CREATE INDEX ur_events_session_time ON user_research.events USING btree (environment, session_id, created_at);
CREATE INDEX ur_feedback_created ON user_research.feedback USING btree (created_at);
CREATE INDEX ur_oracle_session ON user_research.oracle_turns USING btree (environment, session_id);
CREATE INDEX ur_oracle_updated ON user_research.oracle_turns USING btree (environment, updated_at);
CREATE INDEX ur_sessions_clarity_ref ON user_research.sessions USING btree (environment, clarity_ref) WHERE (clarity_ref IS NOT NULL);
CREATE INDEX ur_sessions_last_seen ON user_research.sessions USING btree (last_seen_at);
ALTER TABLE ONLY user_research.events
    ADD CONSTRAINT events_session_id_environment_fkey FOREIGN KEY (session_id, environment) REFERENCES user_research.sessions(session_id, environment) ON DELETE CASCADE;
ALTER TABLE ONLY user_research.feedback
    ADD CONSTRAINT feedback_session_id_environment_fkey FOREIGN KEY (session_id, environment) REFERENCES user_research.sessions(session_id, environment) ON DELETE CASCADE;
ALTER TABLE ONLY user_research.oracle_turns
    ADD CONSTRAINT oracle_turns_session_id_environment_fkey FOREIGN KEY (session_id, environment) REFERENCES user_research.sessions(session_id, environment) ON DELETE CASCADE;
GRANT USAGE ON SCHEMA user_research TO research_prod_reader,research_prod_writer;
REVOKE ALL ON ALL TABLES IN SCHEMA user_research FROM PUBLIC;
GRANT SELECT ON ALL TABLES IN SCHEMA user_research TO research_prod_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA user_research TO research_prod_writer;
COMMIT;
