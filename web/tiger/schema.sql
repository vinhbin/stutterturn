-- StutterTurn run logs as a time series (Tiger Data / TimescaleDB).
--
-- Every agent run is a time series: the run-log JSONL lines defined in
-- agent/CONTRACT.md (run_started / event / run_ended) become one `runs` row
-- plus one `events` hypertable row per event line. The event time dimension
-- is ts = run t0_wall + t (t is seconds since the first source sample,
-- monotonic clock; see "Time origin" in agent/CONTRACT.md).
--
-- Idempotent: safe to run repeatedly (IF NOT EXISTS / OR REPLACE throughout).
-- Applied automatically by web/tiger/ingest.py; see web/tiger/README.md.
--
-- Honesty notes, mirrored in the views below:
--   * Rows from agent/evidence/2026-10-10-first-replay are kept but marked
--     superseded = true (its model input was faulty; see that folder's README
--     and the replay-v2 README). Analysis views exclude superseded rows.
--   * Current evidence is 5 clips x 2 configurations, one run each. The views
--     return per-run / per-clip values; they deliberately compute no rates.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- runs: one row per run_started/run_ended pair (one replayed recording
-- through one configuration, agent/CONTRACT.md "What a run is").
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS runs (
    run_id            text PRIMARY KEY,
    config            text NOT NULL,              -- stock | patient | stock_fp32 | candidate
    model             text,                       -- e.g. stock-int8
    model_sha256      text,
    commit_sha        text,                       -- repo commit stamped into the log ("commit")
    contract_v        text,                       -- log schema version ("v")
    source_id         text,                       -- e.g. HeStutters_1_133.wav
    source_duration_s double precision,
    t0_wall           timestamptz NOT NULL,       -- wall clock of the first source sample
    services          text,                       -- on | off
    reason            text,                       -- run_ended.reason
    params            jsonb,                      -- run_started.params (vad_stop_s, threshold, ...)
    summary           jsonb,                      -- run_ended.summary, as logged
    evidence_dir      text NOT NULL,              -- committed folder the log was ingested from
    log_file          text NOT NULL,              -- JSONL file name
    superseded        boolean NOT NULL DEFAULT false
);

-- ---------------------------------------------------------------------------
-- events: every `event` line, as a hypertable.
-- ts is derived at ingest: t0_wall + t * interval '1 second'.
-- A hypertable fits because runs emit ordered, append-only, timestamped
-- events and every judge query slices or windows them by time.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    ts             timestamptz NOT NULL,          -- t0_wall + t
    run_id         text NOT NULL,
    config         text NOT NULL,
    source_id      text,
    seq            integer NOT NULL,              -- per-run, increases by one per line
    t              double precision NOT NULL,     -- seconds since first source sample
    kind           text NOT NULL,                 -- state | info | decision | audible
    name           text,                          -- turn_complete, cancelled, agent_audio_start, ...
    state          text,                          -- speaking | silence | holding | agent (kind=state)
    prob           double precision,              -- model probability when known
    threshold      double precision,
    trigger        text,                          -- smart_turn | fallback_timeout (decisions)
    model          text,
    silence_s      double precision,
    infer_ms       double precision,
    input_s        double precision,
    before_audible boolean,                       -- on `cancelled` events
    detail         text,
    superseded     boolean NOT NULL DEFAULT false,
    raw            jsonb NOT NULL,                -- the full JSONL line, unaltered
    -- The time column must be part of any hypertable unique index, so the
    -- logical upsert key (run_id, seq) carries ts too. ts is deterministic
    -- from (t0_wall, t), so re-ingesting the same committed log upserts
    -- in place instead of duplicating rows.
    CONSTRAINT events_pkey PRIMARY KEY (run_id, seq, ts)
);

SELECT create_hypertable('events', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS events_name_ts_idx ON events (name, ts);
CREATE INDEX IF NOT EXISTS events_run_seq_idx ON events (run_id, seq);

-- ---------------------------------------------------------------------------
-- Judge queries, as named views. Each returns values a judge can check
-- against the committed JSONL files and the evidence README tables.
-- ---------------------------------------------------------------------------

-- Per-run decision timeline: everything the agent logged, in order, with the
-- run's configuration and clip attached. Includes superseded rows but says so.
CREATE OR REPLACE VIEW run_decision_timeline AS
SELECT e.ts, e.run_id, e.config, e.source_id, e.seq, e.t,
       e.kind, e.name, e.state, e.prob, e.threshold, e.trigger,
       e.silence_s, e.infer_ms, e.input_s, e.before_audible, e.detail,
       e.model, e.superseded
FROM events e
ORDER BY e.run_id, e.seq;

-- First completion decision per run (current evidence only): when each
-- configuration first decided "turn complete" on each clip, and whether the
-- model decided (smart_turn) or the 3 s silence fallback did
-- (fallback_timeout — on these 3 s clips that happens during the appended
-- synthetic silence; cite it as such, per agent/CONTRACT.md).
CREATE OR REPLACE VIEW clip_first_completion AS
SELECT DISTINCT ON (e.run_id)
       e.source_id, e.config, e.run_id,
       e.t       AS first_complete_t,
       e.trigger,
       e.prob,                                    -- null for fallback decisions
       e.silence_s
FROM events e
WHERE e.name = 'turn_complete' AND NOT e.superseded
ORDER BY e.run_id, e.t, e.seq;

-- Decision -> first-audio gap per run (current evidence only). The gap is
-- measured from the completion decision the audio actually answered (the
-- latest turn_complete at or before agent_audio_start): an earlier decision
-- cancelled by the speaker resuming produced no audio and must not be
-- credited with one. first_audio_t includes Gemini + ElevenLabs latency
-- (reported separately from the run summary); it is when the first sample
-- was scheduled to play, not measured speaker output.
CREATE OR REPLACE VIEW decision_to_audio_gap AS
WITH first_audio AS (
    SELECT DISTINCT ON (run_id) run_id, t AS first_audio_t
    FROM events
    WHERE name = 'agent_audio_start' AND NOT superseded
    ORDER BY run_id, t, seq
)
SELECT r.source_id, r.config, a.run_id,
       (SELECT max(d.t) FROM events d
         WHERE d.run_id = a.run_id
           AND d.name = 'turn_complete'
           AND d.t <= a.first_audio_t)           AS answered_decision_t,
       a.first_audio_t,
       a.first_audio_t -
       (SELECT max(d.t) FROM events d
         WHERE d.run_id = a.run_id
           AND d.name = 'turn_complete'
           AND d.t <= a.first_audio_t)           AS gap_s,
       (r.summary ->> 'llm_latency_s')::double precision      AS llm_latency_s,
       (r.summary ->> 'tts_first_audio_s')::double precision  AS tts_first_audio_s
FROM first_audio a
JOIN runs r USING (run_id);

-- Replies cancelled before any audio (current evidence only): the speaker
-- resumed after a completion decision and the pending reply was dropped
-- before a single sample played. These are cancelled decisions, not
-- observed audible interruptions.
CREATE OR REPLACE VIEW cancelled_before_audio AS
SELECT r.source_id, r.config, e.run_id,
       e.t AS cancelled_t,
       (SELECT max(d.t) FROM events d
         WHERE d.run_id = e.run_id
           AND d.name = 'turn_complete'
           AND d.t <= e.t)                        AS cancelled_decision_t
FROM events e
JOIN runs r USING (run_id)
WHERE e.name = 'cancelled'
  AND e.before_audible
  AND NOT r.superseded;

-- The agent's own run_ended summaries, flattened (all rows, superseded
-- flagged). Lets a judge cross-check the event-derived views above against
-- what the agent itself reported for the same run.
CREATE OR REPLACE VIEW run_outcomes AS
SELECT run_id, source_id, config, evidence_dir, superseded, commit_sha,
       (summary ->> 'first_turn_complete_t')::double precision AS first_turn_complete_t,
       summary ->> 'trigger'                                    AS trigger,
       (summary ->> 'first_agent_audio_t')::double precision    AS first_agent_audio_t,
       (summary ->> 'llm_latency_s')::double precision          AS llm_latency_s,
       (summary ->> 'tts_first_audio_s')::double precision      AS tts_first_audio_s,
       (summary ->> 'speaker_resumed_after_decision')::boolean  AS speaker_resumed_after_decision,
       (summary ->> 'cancelled')::boolean                       AS cancelled,
       (summary ->> 'audible_interruption')::boolean            AS audible_interruption,
       (summary ->> 'no_response')::boolean                     AS no_response
FROM runs;
