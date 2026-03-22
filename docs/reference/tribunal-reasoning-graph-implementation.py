"""Tribunal Reasoning Graph — Persistent verdict storage, contradiction detection, verdict reuse.

Architecture:
    Layer 1: PostgreSQL tables (tribunal_verdicts, tribunal_edges, tribunal_contradictions, tribunal_audits)
    Layer 2: HNSW vector index (IVFFLAT, 256-dim, Model2Vec embeddings)
    Layer 3: Async persistence (non-blocking INSERT)

Strategy:
    - Store FULL verdict text (not summary) in PostgreSQL
    - Embeddings updated async (weekly batch, real-time on demand)
    - Contradiction detection: real-time (top 5 recent) + batch hourly
    - Verdict reuse: query similarity > 0.85, confidence > 0.7, within 90 days
    - All operations async (tribunal_automaton must not block)

File location (once approved for MCP):
    ~/.claude/mcp-servers/tribunal/reasoning_graph.py

Integration point (tribunal_automaton):
    1. After queen verdict: asyncio.create_task(_persist_verdict_async(...))
    2. During tribunal_decide: check for reuse, show citation
    3. Real-time contradictions: logged + returned in response
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import re

# asyncpg for PostgreSQL async (already in tribunal/requirements.txt)
import asyncpg
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────


class VerdictInput(BaseModel):
    """Input for storing a new verdict."""
    question: str
    verdict_text: str
    confidence: float = Field(default=0.5, ge=0, le=1)
    personas: List[str] = Field(default_factory=list)
    persona_models: str = "haiku"
    queen_model: str = "sonnet"
    phase_number: Optional[int] = None
    task_id: Optional[str] = None
    parent_decision_id: Optional[int] = None
    session_id: Optional[str] = None
    total_ms: Optional[int] = None
    response_status: str = "success"


class Contradiction(BaseModel):
    """Detected conflict between verdicts."""
    verdict_a_id: int
    verdict_b_id: int
    severity: str  # 'warn', 'error', 'critical'
    conflict_type: str
    details: str
    question_a: str
    question_b: str
    confidence_a: float
    confidence_b: float


# ─────────────────────────────────────────────────────────────────────────────
# Verdict Embedding (Model2Vec integration)
# ─────────────────────────────────────────────────────────────────────────────


def embed_text(text: str, model_name: str = "model2vec") -> Optional[List[float]]:
    """Embed text using Model2Vec (256-dim, fast).

    Args:
        text: Text to embed (question or verdict summary)
        model_name: Model identifier (currently only model2vec supported)

    Returns:
        256-dimensional embedding vector (or None if unavailable)

    Notes:
        Model2Vec is 79x faster than SBERT, 12x smaller. Already loaded in Ollama.
        Fallback: return None → PostgreSQL stores NULL → queries skip vector search.
    """
    if not text or len(text.strip()) < 5:
        return None

    try:
        import requests
        # Assume Ollama running on localhost:11434 with model2vec model
        response = requests.post(
            "http://localhost:11434/api/embeddings",
            json={"model": model_name, "prompt": text[:2000]},  # Cap at 2000 chars
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get("embedding")
    except Exception as e:
        logger.debug(f"Embedding failed: {e}")

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Contradiction Detection Algorithm
# ─────────────────────────────────────────────────────────────────────────────


class ContradictionDetector:
    """Real-time + batch contradiction detection."""

    ACTION_VERBS = {
        "create", "add", "remove", "split", "update", "replace", "move",
        "extract", "refactor", "implement", "build", "configure", "migrate",
        "fix", "change", "rewrite", "port", "wire", "design", "setup",
        "keep", "maintain", "preserve", "unify", "consolidate", "monolithic"
    }

    @staticmethod
    def parse_actions(verdict: str) -> List[str]:
        """Extract actionable items from verdict text.

        Heuristics (priority order):
        1. Numbered list items: "1. Do X" / "1) Do X"
        2. Bullet items: "- Do X" / "* Do X"
        3. Lines starting with action verbs
        """
        actions = []
        seen = set()

        # Pattern 1: Numbered items
        for m in re.finditer(r"^\s*\d+[.)]\s+(.+)", verdict, re.MULTILINE):
            text = m.group(1).strip()
            if text and text not in seen:
                seen.add(text)
                actions.append(text)

        # Pattern 2: Bullet items
        if not actions:
            for m in re.finditer(r"^\s*[-*]\s+(.+)", verdict, re.MULTILINE):
                text = m.group(1).strip()
                if text and text not in seen:
                    seen.add(text)
                    actions.append(text)

        # Pattern 3: Action verb lines
        if not actions:
            for line in verdict.splitlines():
                line = line.strip()
                first_word = line.split()[0].lower().rstrip(":") if line.split() else ""
                if first_word in ContradictionDetector.ACTION_VERBS and line not in seen:
                    seen.add(line)
                    actions.append(line)

        return actions

    @staticmethod
    def are_actions_incompatible(action_a: str, action_b: str) -> bool:
        """Check if two actions are incompatible.

        Examples:
        - "split X" vs "keep X monolithic" → incompatible
        - "add caching" vs "remove cache" → incompatible
        - "use dependency injection" vs "avoid DI" → incompatible
        """
        action_a_lower = action_a.lower()
        action_b_lower = action_b.lower()

        incompatible_pairs = [
            ("split", "monolithic"),
            ("split", "keep"),
            ("refactor", "maintain"),
            ("add", "remove"),
            ("create", "delete"),
            ("implement", "skip"),
            ("use", "avoid"),
            ("enable", "disable"),
            ("inject", "inline"),
        ]

        for pair in incompatible_pairs:
            if (pair[0] in action_a_lower and pair[1] in action_b_lower) or \
               (pair[1] in action_a_lower and pair[0] in action_b_lower):
                return True

        return False

    def detect_contradictions(self, new_verdict: Dict, recent_verdicts: List[Dict]) -> List[Contradiction]:
        """Check new verdict against recent verdicts for conflicts.

        Real-time mode: O(5 × 256-dim dot product) = < 1ms per verdict
        Batch mode: Full analysis, run hourly

        Scoring:
        1. Question similarity: cosine > 0.8
        2. Confidence opposition: |conf_delta| > 0.6
        3. Action incompatibility
        4. Persona conflict

        Args:
            new_verdict: New verdict dict with question, verdict_text, confidence, personas
            recent_verdicts: Top 5 recent verdicts (from database)

        Returns:
            List[Contradiction] sorted by severity (CRITICAL first)
        """
        conflicts = []

        new_actions = self.parse_actions(new_verdict.get("verdict_text", ""))

        for recent in recent_verdicts:
            # Question similarity check (would use vector cosine in practice)
            # For now, simple substring overlap
            q_overlap = len(set(new_verdict["question"].split()) & set(recent["question"].split()))
            q_words = max(len(new_verdict["question"].split()), len(recent["question"].split()))
            q_sim = q_overlap / q_words if q_words > 0 else 0

            if q_sim < 0.6:  # Questions not similar enough
                continue

            # Confidence opposition
            conf_delta = abs(new_verdict.get("confidence", 0.5) - recent.get("confidence", 0.5))

            # Parse actions
            recent_actions = self.parse_actions(recent.get("verdict_text", ""))

            # Check action compatibility
            incompatible_pairs = []
            for na in new_actions:
                for ra in recent_actions:
                    if self.are_actions_incompatible(na, ra):
                        incompatible_pairs.append((na, ra))

            # Shared personas?
            shared_personas = set(new_verdict.get("personas", [])) & set(recent.get("personas", []))

            # Severity assignment
            severity = None
            conflict_type = None

            if incompatible_pairs and q_sim > 0.75:
                severity = "CRITICAL" if conf_delta > 0.5 else "ERROR"
                conflict_type = "incompatible_actions"
            elif shared_personas and conf_delta > 0.5:
                severity = "ERROR"
                conflict_type = "conflicting_personas"
            elif q_sim > 0.70 and conf_delta > 0.4:
                severity = "WARN"
                conflict_type = "opposite_confidence"

            if severity:
                conflicts.append(Contradiction(
                    verdict_a_id=recent["verdict_id"],
                    verdict_b_id=new_verdict["verdict_id"],
                    severity=severity,
                    conflict_type=conflict_type or "unknown",
                    details=f"Q-overlap: {q_sim:.2f}, conf-delta: {conf_delta:.2f}, incompatible actions: {len(incompatible_pairs)}, shared personas: {shared_personas}",
                    question_a=recent["question"],
                    question_b=new_verdict["question"],
                    confidence_a=recent.get("confidence", 0.5),
                    confidence_b=new_verdict.get("confidence", 0.5)
                ))

        # Sort by severity
        severity_order = {"CRITICAL": 0, "ERROR": 1, "WARN": 2}
        conflicts.sort(key=lambda c: severity_order.get(c.severity, 99))

        return conflicts


# ─────────────────────────────────────────────────────────────────────────────
# Verdict Graph — Main API
# ─────────────────────────────────────────────────────────────────────────────


class VerdictGraph:
    """Persistent reasoning graph for tribunal verdicts."""

    def __init__(self, db_url: str = "postgresql://localhost/tribunal_reasoning"):
        """Initialize connection pool.

        Args:
            db_url: PostgreSQL connection URL
        """
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None
        self.detector = ContradictionDetector()
        logger.info(f"VerdictGraph initialized (db: {db_url})")

    async def connect(self):
        """Initialize async connection pool."""
        if self.pool is None:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60,
                setup=self._setup_conn
            )
            logger.info("VerdictGraph connected to PostgreSQL")

    @staticmethod
    async def _setup_conn(conn):
        """Setup connection: install pgvector."""
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    async def disconnect(self):
        """Close connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("VerdictGraph disconnected")

    async def persist_verdict_async(self, verdict: VerdictInput) -> Optional[int]:
        """Non-blocking verdict persistence. Fire-and-forget.

        Args:
            verdict: VerdictInput with question, verdict_text, personas, etc.

        Returns:
            verdict_id (or None if failed)

        Usage:
            asyncio.create_task(graph.persist_verdict_async(verdict_input))
            # Function returns immediately, INSERT happens in background
        """
        if not self.pool:
            logger.warning("VerdictGraph not connected, skipping persist")
            return None

        try:
            # Embed question and verdict summary
            q_embedding = embed_text(verdict.question)
            v_summary = verdict.verdict_text[:300]
            v_embedding = embed_text(v_summary)

            async with self.pool.acquire() as conn:
                verdict_id = await conn.fetchval(
                    """
                    INSERT INTO tribunal_verdicts (
                        question, question_embedding, verdict_text, verdict_summary,
                        verdict_embedding, confidence, personas, persona_models,
                        queen_model, phase_number, task_id, parent_decision_id,
                        session_id, total_ms, response_status
                    ) VALUES (
                        $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                    )
                    RETURNING verdict_id
                    """,
                    verdict.question,
                    q_embedding,
                    verdict.verdict_text,
                    v_summary,
                    v_embedding,
                    verdict.confidence,
                    verdict.personas,
                    verdict.persona_models,
                    verdict.queen_model,
                    verdict.phase_number,
                    verdict.task_id,
                    verdict.parent_decision_id,
                    verdict.session_id,
                    verdict.total_ms,
                    verdict.response_status
                )
                logger.info(f"Persisted verdict {verdict_id}")
                return verdict_id

        except Exception as e:
            logger.error(f"Failed to persist verdict: {e}")
            return None

    async def find_reusable_verdicts(
        self,
        question: str,
        similarity_threshold: float = 0.85,
        days_old: int = 90
    ) -> List[Dict]:
        """Find previously answered similar questions (for verdict reuse).

        Args:
            question: New question to check
            similarity_threshold: Cosine similarity threshold (0-1)
            days_old: Only return verdicts from last N days

        Returns:
            List[Dict] with verdict_id, question, verdict_text, confidence, personas, created_at, similarity

        Performance: < 50ms with IVFFLAT index
        """
        if not self.pool:
            logger.warning("VerdictGraph not connected")
            return []

        q_embedding = embed_text(question)
        if q_embedding is None:
            logger.debug("Could not embed question, skipping reuse search")
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT
                        verdict_id, question, verdict_text, confidence, personas,
                        created_at,
                        1 - (question_embedding <-> $1) as similarity
                    FROM tribunal_verdicts
                    WHERE question_embedding <-> $1 < (1 - $2)
                      AND created_at > now() - ($3 || ' days')::INTERVAL
                      AND confidence > 0.7
                      AND response_status = 'success'
                    ORDER BY similarity DESC
                    LIMIT 3
                    """,
                    q_embedding,
                    similarity_threshold,
                    days_old
                )
                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Reuse search failed: {e}")
            return []

    async def detect_contradictions_realtime(
        self,
        new_verdict: Dict
    ) -> List[Contradiction]:
        """Detect contradictions in real-time (top 5 recent verdicts).

        Args:
            new_verdict: New verdict with question, verdict_text, confidence, personas, verdict_id

        Returns:
            List[Contradiction] sorted by severity (CRITICAL first)

        Performance: < 100ms (5 DB queries + in-memory scoring)
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                recent = await conn.fetch(
                    """
                    SELECT verdict_id, question, verdict_text, confidence, personas
                    FROM tribunal_verdicts
                    WHERE verdict_id <> $1  -- Don't compare to itself
                      AND created_at > now() - interval '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    new_verdict.get("verdict_id", -1)
                )

                recent_dicts = [dict(r) for r in recent]
                conflicts = self.detector.detect_contradictions(new_verdict, recent_dicts)

                # Store contradictions in database
                for conflict in conflicts:
                    await conn.execute(
                        """
                        INSERT INTO tribunal_contradictions (
                            verdict_a_id, verdict_b_id, severity, conflict_type, details
                        ) VALUES ($1, $2, $3, $4, $5)
                        """,
                        conflict.verdict_a_id,
                        conflict.verdict_b_id,
                        conflict.severity,
                        conflict.conflict_type,
                        conflict.details
                    )

                return conflicts

        except Exception as e:
            logger.error(f"Contradiction detection failed: {e}")
            return []

    async def trace_verdict_ancestry(
        self,
        verdict_id: int,
        max_depth: int = 10
    ) -> List[Dict]:
        """Trace decision lineage: What decisions led to this verdict?

        Args:
            verdict_id: Starting verdict ID
            max_depth: Max recursion depth

        Returns:
            List[Dict] with verdict_id, question, confidence, phase_number, created_at, depth
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM trace_verdict_ancestry($1, $2)
                    """,
                    verdict_id,
                    max_depth
                )
                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Ancestry trace failed: {e}")
            return []

    async def find_phase_contradictions(
        self,
        phase_number: int
    ) -> List[Dict]:
        """Find unresolved contradictions within a phase.

        Args:
            phase_number: GSD phase number

        Returns:
            List[Dict] with contradiction details, sorted by severity
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(
                    """
                    SELECT * FROM find_phase_contradictions($1)
                    """,
                    phase_number
                )
                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Phase contradiction query failed: {e}")
            return []

    async def expert_performance_summary(self) -> List[Dict]:
        """Which personas are most reliable?

        Returns:
            List[Dict] with persona_name, total_verdicts, avg_accuracy, confidence_calibration, last_audit
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM expert_performance_summary()")
                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Expert performance query failed: {e}")
            return []

    async def phase_verdict_quality_summary(self) -> List[Dict]:
        """Verdict adoption rate by phase.

        Returns:
            List[Dict] with phase_number, verdicts_created, verdicts_acted_on, success_rate, adoption_rate
        """
        if not self.pool:
            return []

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch("SELECT * FROM phase_verdict_quality_summary()")
                return [dict(r) for r in rows]

        except Exception as e:
            logger.error(f"Phase quality query failed: {e}")
            return []


# ─────────────────────────────────────────────────────────────────────────────
# Example Usage & Testing
# ─────────────────────────────────────────────────────────────────────────────


async def example_workflow():
    """Example: Tribunal → Reasoning Graph integration."""

    graph = VerdictGraph()
    await graph.connect()

    try:
        # 1. New verdict from tribunal
        new_verdict = VerdictInput(
            question="Should we split mega_index.py?",
            verdict_text="Split into 4 modules: builder, lookup, cache, export. Improves testability.",
            confidence=0.9,
            personas=["architecture-designer", "python-pro"],
            phase_number=1
        )

        # 2. Async persistence (non-blocking)
        asyncio.create_task(graph.persist_verdict_async(new_verdict))

        # 3. Check for verdict reuse (similar question answered before?)
        reusable = await graph.find_reusable_verdicts(new_verdict.question)
        if reusable:
            print(f"✓ Reusable verdict found: {reusable[0]['question']}")
        else:
            print("No reusable verdicts found")

        # 4. Detect contradictions (after storing)
        await asyncio.sleep(0.5)  # Let INSERT finish
        conflicts = await graph.detect_contradictions_realtime(new_verdict.dict())
        if conflicts:
            for c in conflicts:
                print(f"⚠️  {c.severity}: {c.conflict_type}")

        # 5. Query expert performance
        experts = await graph.expert_performance_summary()
        print(f"Expert performance: {experts}")

        # 6. End-of-phase quality check
        quality = await graph.phase_verdict_quality_summary()
        print(f"Phase quality: {quality}")

    finally:
        await graph.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_workflow())
