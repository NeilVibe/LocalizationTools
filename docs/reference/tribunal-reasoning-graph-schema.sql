-- Tribunal Reasoning Graph Schema
-- PostgreSQL 13+ with pgvector extension
-- Date: 2026-03-22
-- Purpose: Persistent verdict storage, contradiction detection, verdict reuse, decision audit trail

-- Enable pgvector extension for HNSW similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 1: tribunal_verdicts
-- ─────────────────────────────────────────────────────────────────────────────
-- Core table: Every verdict ever made. Survive session restarts. Track lineage.

DROP TABLE IF EXISTS tribunal_verdicts CASCADE;

CREATE TABLE tribunal_verdicts (
    verdict_id BIGSERIAL PRIMARY KEY,

    -- Question & Answer
    question TEXT NOT NULL,
    question_embedding vector(256),              -- Model2Vec 256-dim (updated weekly)
    verdict_text TEXT NOT NULL,                  -- FULL text, never summary
    verdict_summary TEXT,                        -- First ~300 chars (for lighter embedding)
    verdict_embedding vector(256),               -- Of verdict_summary
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),

    -- Tribunal Metadata
    personas TEXT[] NOT NULL DEFAULT '{}',       -- ["architect-db", "security-reviewer", ...]
    persona_models TEXT DEFAULT 'haiku',         -- Model(s) used for personas
    queen_model TEXT DEFAULT 'sonnet',
    total_ms INT,                                -- Wall-clock time (tribunal_decide elapsed)

    -- Lineage & Context
    phase_number INT,                            -- GSD phase: 1=research, 2=plan, 3=execute, 4=verify, 5=iterate
    task_id TEXT,                                -- FK to Ruflo task (if action-driven verdict)
    parent_decision_id BIGINT REFERENCES tribunal_verdicts(verdict_id) ON DELETE SET NULL,
    session_id TEXT,                             -- UUID of Claude session (for cross-session queries)

    -- Status
    response_status VARCHAR(16) DEFAULT 'success' CHECK (response_status IN ('success', 'partial', 'failed')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Indexes for common queries
CREATE INDEX idx_tribunal_verdicts_question_embedding ON tribunal_verdicts
    USING ivfflat (question_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_tribunal_verdicts_verdict_embedding ON tribunal_verdicts
    USING ivfflat (verdict_embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_tribunal_verdicts_phase ON tribunal_verdicts(phase_number);
CREATE INDEX idx_tribunal_verdicts_task_id ON tribunal_verdicts(task_id);
CREATE INDEX idx_tribunal_verdicts_parent ON tribunal_verdicts(parent_decision_id);
CREATE INDEX idx_tribunal_verdicts_session ON tribunal_verdicts(session_id);
CREATE INDEX idx_tribunal_verdicts_created ON tribunal_verdicts(created_at DESC);
CREATE INDEX idx_tribunal_verdicts_confidence ON tribunal_verdicts(confidence DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 2: tribunal_edges
-- ─────────────────────────────────────────────────────────────────────────────
-- Build decision graph. Trace causality, reuse, and conflicts.

DROP TABLE IF EXISTS tribunal_edges CASCADE;

CREATE TABLE tribunal_edges (
    edge_id BIGSERIAL PRIMARY KEY,

    -- Graph structure
    source_verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,
    target_verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,

    -- Edge semantics
    edge_type VARCHAR(32) NOT NULL CHECK (edge_type IN ('REFINES', 'CONTRADICTS', 'ENABLES', 'BLOCKS', 'REUSES')),
    severity VARCHAR(16) CHECK (severity IN ('warn', 'error', 'critical', NULL)),  -- For CONTRADICTS only
    reason TEXT,                                 -- "both about module splitting"
    confidence FLOAT DEFAULT 0.5 CHECK (confidence >= 0 AND confidence <= 1),
    detected_by VARCHAR(64) DEFAULT 'manual' CHECK (detected_by IN ('manual', 'contradiction_scanner', 'reuse_detector', 'parent_link')),

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    CONSTRAINT check_source_not_target CHECK (source_verdict_id <> target_verdict_id)
);

CREATE INDEX idx_tribunal_edges_source ON tribunal_edges(source_verdict_id);
CREATE INDEX idx_tribunal_edges_target ON tribunal_edges(target_verdict_id);
CREATE INDEX idx_tribunal_edges_type ON tribunal_edges(edge_type);
CREATE INDEX idx_tribunal_edges_severity ON tribunal_edges(severity);
CREATE INDEX idx_tribunal_edges_detected_by ON tribunal_edges(detected_by);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 3: tribunal_contradictions
-- ─────────────────────────────────────────────────────────────────────────────
-- Detect and track conflicts between verdicts.

DROP TABLE IF EXISTS tribunal_contradictions CASCADE;

CREATE TABLE tribunal_contradictions (
    contradiction_id BIGSERIAL PRIMARY KEY,

    -- The conflict
    verdict_a_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,
    verdict_b_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,

    -- Severity & type
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('warn', 'error', 'critical')),
    conflict_type VARCHAR(64),                   -- 'opposite_confidence', 'incompatible_actions', 'conflicting_personas'
    details TEXT,                                -- Human-readable explanation

    -- Resolution
    resolved BOOLEAN DEFAULT FALSE,
    resolution_note TEXT,

    -- Metadata
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    CONSTRAINT check_a_not_b CHECK (verdict_a_id <> verdict_b_id)
);

CREATE INDEX idx_tribunal_contradictions_verdict_a ON tribunal_contradictions(verdict_a_id);
CREATE INDEX idx_tribunal_contradictions_verdict_b ON tribunal_contradictions(verdict_b_id);
CREATE INDEX idx_tribunal_contradictions_severity ON tribunal_contradictions(severity);
CREATE INDEX idx_tribunal_contradictions_resolved ON tribunal_contradictions(resolved);
CREATE INDEX idx_tribunal_contradictions_detected_at ON tribunal_contradictions(detected_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE 4: tribunal_audits
-- ─────────────────────────────────────────────────────────────────────────────
-- Post-phase assessment: accuracy, adoption, expert performance.

DROP TABLE IF EXISTS tribunal_audits CASCADE;

CREATE TABLE tribunal_audits (
    audit_id BIGSERIAL PRIMARY KEY,

    -- Verdict reference
    verdict_id BIGINT NOT NULL REFERENCES tribunal_verdicts(verdict_id) ON DELETE CASCADE,

    -- Verdict-level assessment
    accuracy FLOAT CHECK (accuracy >= 0 AND accuracy <= 1),  -- "Did this verdict prove correct?"
    was_acted_on BOOLEAN,                        -- Did we implement the verdict's actions?
    implementation_result VARCHAR(32) CHECK (implementation_result IN ('success', 'partial', 'failed', 'deferred', NULL)),
    decision_lifecycle VARCHAR(32) CHECK (decision_lifecycle IN ('created', 'used', 'validated', 'superseded', 'archived', NULL)),

    -- Persona-level assessment
    persona_name TEXT,
    persona_accuracy FLOAT CHECK (persona_accuracy >= 0 AND persona_accuracy <= 1),  -- Was THIS persona correct?
    persona_confidence_vs_actual INT CHECK (persona_confidence_vs_actual IN (-1, 0, 1)),  -- -1: underconfident, 0: calibrated, +1: overconfident

    -- Notes
    notes TEXT,
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX idx_tribunal_audits_verdict ON tribunal_audits(verdict_id);
CREATE INDEX idx_tribunal_audits_accuracy ON tribunal_audits(verdict_id, accuracy);
CREATE INDEX idx_tribunal_audits_persona ON tribunal_audits(persona_name);
CREATE INDEX idx_tribunal_audits_persona_accuracy ON tribunal_audits(persona_name, persona_accuracy);
CREATE INDEX idx_tribunal_audits_assessed_at ON tribunal_audits(assessed_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Similar Questions (Verdict Reuse)
-- ─────────────────────────────────────────────────────────────────────────────
-- Find previously answered similar questions (for reuse, avoid redundant decisions).

-- SQL function to make reuse search easy
CREATE OR REPLACE FUNCTION find_reusable_verdicts(
    query_embedding vector(256),
    similarity_threshold FLOAT DEFAULT 0.85,
    days_old INT DEFAULT 90
)
RETURNS TABLE (
    verdict_id BIGINT,
    question TEXT,
    verdict_text TEXT,
    confidence FLOAT,
    personas TEXT[],
    created_at TIMESTAMP WITH TIME ZONE,
    similarity FLOAT
) AS $$
    SELECT
        v.verdict_id,
        v.question,
        v.verdict_text,
        v.confidence,
        v.personas,
        v.created_at,
        1 - (v.question_embedding <-> query_embedding)::FLOAT as similarity
    FROM tribunal_verdicts v
    WHERE v.question_embedding <-> query_embedding < (1 - similarity_threshold)
      AND v.created_at > now() - (days_old || ' days')::INTERVAL
      AND v.confidence > 0.7
      AND v.response_status = 'success'
    ORDER BY similarity DESC
    LIMIT 3;
$$ LANGUAGE SQL STABLE;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Ancestry Trace (Root Cause Analysis)
-- ─────────────────────────────────────────────────────────────────────────────
-- Recursively walk backward from verdict to root causes.

CREATE OR REPLACE FUNCTION trace_verdict_ancestry(
    starting_verdict_id BIGINT,
    max_depth INT DEFAULT 10
)
RETURNS TABLE (
    verdict_id BIGINT,
    question TEXT,
    confidence FLOAT,
    phase_number INT,
    created_at TIMESTAMP WITH TIME ZONE,
    depth INT
) AS $$
    WITH RECURSIVE ancestors AS (
        SELECT
            v.verdict_id, v.question, v.confidence, v.phase_number, v.created_at,
            1 AS depth
        FROM tribunal_verdicts v
        WHERE v.verdict_id = starting_verdict_id

        UNION ALL

        SELECT
            v.verdict_id, v.question, v.confidence, v.phase_number, v.created_at,
            a.depth + 1
        FROM tribunal_verdicts v
        JOIN ancestors a ON v.verdict_id = a.verdict_id
        WHERE a.depth < max_depth
          AND v.parent_decision_id IS NOT NULL
    )
    SELECT * FROM ancestors
    ORDER BY depth;
$$ LANGUAGE SQL;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Unresolved Contradictions (Decision Validation)
-- ─────────────────────────────────────────────────────────────────────────────
-- Find conflicts within a phase.

CREATE OR REPLACE FUNCTION find_phase_contradictions(
    phase INT
)
RETURNS TABLE (
    contradiction_id BIGINT,
    severity VARCHAR(16),
    conflict_type VARCHAR(64),
    verdict_a_question TEXT,
    verdict_b_question TEXT,
    verdict_a_confidence FLOAT,
    verdict_b_confidence FLOAT,
    details TEXT,
    detected_at TIMESTAMP WITH TIME ZONE,
    resolved BOOLEAN
) AS $$
    SELECT
        c.contradiction_id,
        c.severity,
        c.conflict_type,
        v_a.question,
        v_b.question,
        v_a.confidence,
        v_b.confidence,
        c.details,
        c.detected_at,
        c.resolved
    FROM tribunal_contradictions c
    JOIN tribunal_verdicts v_a ON c.verdict_a_id = v_a.verdict_id
    JOIN tribunal_verdicts v_b ON c.verdict_b_id = v_b.verdict_id
    WHERE v_a.phase_number = phase
      AND v_b.phase_number = phase
      AND c.resolved = FALSE
    ORDER BY
        CASE c.severity
            WHEN 'critical' THEN 1
            WHEN 'error' THEN 2
            WHEN 'warn' THEN 3
        END,
        c.detected_at DESC;
$$ LANGUAGE SQL;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Expert Performance (Quality Audit)
-- ─────────────────────────────────────────────────────────────────────────────
-- Which personas are most reliable? Overconfident? Underconfident?

CREATE OR REPLACE FUNCTION expert_performance_summary()
RETURNS TABLE (
    persona_name TEXT,
    total_verdicts BIGINT,
    avg_accuracy FLOAT,
    accuracy_count INT,
    confidence_calibration FLOAT,
    last_audit TIMESTAMP WITH TIME ZONE
) AS $$
    SELECT
        a.persona_name,
        COUNT(DISTINCT a.verdict_id)::BIGINT as total_verdicts,
        AVG(a.persona_accuracy)::FLOAT as avg_accuracy,
        COUNT(CASE WHEN a.persona_accuracy IS NOT NULL THEN 1 END)::INT as accuracy_count,
        AVG(a.persona_confidence_vs_actual)::FLOAT as confidence_calibration,
        MAX(a.assessed_at) as last_audit
    FROM tribunal_audits a
    WHERE a.persona_name IS NOT NULL
      AND a.assessed_at IS NOT NULL
    GROUP BY a.persona_name
    ORDER BY avg_accuracy DESC NULLS LAST;
$$ LANGUAGE SQL;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Decision Quality by Phase (Adoption Rate)
-- ─────────────────────────────────────────────────────────────────────────────
-- How many verdicts are actually used? Success rate by phase?

CREATE OR REPLACE FUNCTION phase_verdict_quality_summary()
RETURNS TABLE (
    phase_number INT,
    verdicts_created BIGINT,
    verdicts_acted_on BIGINT,
    success_count BIGINT,
    partial_count BIGINT,
    failed_count BIGINT,
    adoption_rate FLOAT,
    success_rate FLOAT
) AS $$
    SELECT
        v.phase_number,
        COUNT(DISTINCT v.verdict_id)::BIGINT as verdicts_created,
        COUNT(DISTINCT a.verdict_id)::BIGINT as verdicts_acted_on,
        COUNT(CASE WHEN a.implementation_result = 'success' THEN 1 END)::BIGINT as success_count,
        COUNT(CASE WHEN a.implementation_result = 'partial' THEN 1 END)::BIGINT as partial_count,
        COUNT(CASE WHEN a.implementation_result = 'failed' THEN 1 END)::BIGINT as failed_count,
        (COUNT(DISTINCT a.verdict_id)::FLOAT / NULLIF(COUNT(DISTINCT v.verdict_id), 0)) as adoption_rate,
        (SUM(CASE WHEN a.implementation_result = 'success' THEN 1 ELSE 0 END)::FLOAT /
         NULLIF(COUNT(DISTINCT a.verdict_id), 0)) as success_rate
    FROM tribunal_verdicts v
    LEFT JOIN tribunal_audits a ON v.verdict_id = a.verdict_id AND a.was_acted_on = TRUE
    WHERE v.phase_number IS NOT NULL
    GROUP BY v.phase_number
    ORDER BY v.phase_number;
$$ LANGUAGE SQL;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY: Decision Lineage (What Depends on What)
-- ─────────────────────────────────────────────────────────────────────────────
-- For a given verdict, what other decisions depend on it?

CREATE OR REPLACE FUNCTION verdict_dependents(
    starting_verdict_id BIGINT,
    edge_types VARCHAR[] DEFAULT ARRAY['ENABLES', 'REFINES']::VARCHAR[]
)
RETURNS TABLE (
    target_verdict_id BIGINT,
    target_question TEXT,
    edge_type VARCHAR(32),
    reason TEXT,
    target_phase INT,
    target_created TIMESTAMP WITH TIME ZONE
) AS $$
    SELECT
        t.verdict_id,
        t.question,
        e.edge_type,
        e.reason,
        t.phase_number,
        t.created_at
    FROM tribunal_verdicts t
    JOIN tribunal_edges e ON t.verdict_id = e.target_verdict_id
    WHERE e.source_verdict_id = starting_verdict_id
      AND e.edge_type = ANY(edge_types)
    ORDER BY t.created_at DESC;
$$ LANGUAGE SQL;

-- ─────────────────────────────────────────────────────────────────────────────
-- PERFORMANCE CHECKS
-- ─────────────────────────────────────────────────────────────────────────────

-- Verify IVFFLAT indexes exist and are configured correctly
SELECT
    schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('tribunal_verdicts', 'tribunal_edges', 'tribunal_contradictions')
  AND indexdef LIKE '%ivfflat%'
ORDER BY tablename, indexname;

-- ─────────────────────────────────────────────────────────────────────────────
-- SAMPLE DATA (for testing)
-- ─────────────────────────────────────────────────────────────────────────────
-- Uncomment to test schema with sample verdicts

-- INSERT INTO tribunal_verdicts (
--     question, verdict_text, confidence, personas, queen_model,
--     phase_number, response_status
-- ) VALUES (
--     'Should we split mega_index.py?',
--     'Split into 4 modules: builder, lookup, cache, export. Improves testability.',
--     0.9,
--     ARRAY['architecture-designer', 'python-pro'],
--     'sonnet',
--     1,
--     'success'
-- );

-- INSERT INTO tribunal_verdicts (
--     question, verdict_text, confidence, personas, queen_model,
--     phase_number, response_status, parent_decision_id
-- ) VALUES (
--     'How to test the split modules?',
--     'Use pytest fixtures per module. Add integration tests for cross-module flows.',
--     0.85,
--     ARRAY['test-master', 'python-pro'],
--     'sonnet',
--     1,
--     'success',
--     1
-- );

-- INSERT INTO tribunal_edges (
--     source_verdict_id, target_verdict_id, edge_type, reason
-- ) VALUES (
--     1, 2, 'ENABLES', 'Module split requires testing strategy'
-- );

-- SELECT * FROM find_reusable_verdicts(
--     (SELECT question_embedding FROM tribunal_verdicts LIMIT 1),
--     0.85
-- );

-- SELECT * FROM trace_verdict_ancestry(2, 10);

-- SELECT * FROM expert_performance_summary();

-- SELECT * FROM phase_verdict_quality_summary();
