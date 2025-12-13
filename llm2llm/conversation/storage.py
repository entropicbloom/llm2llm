"""Storage layer for conversations - SQLite metadata + JSON files."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator, TYPE_CHECKING

from .schemas import Conversation, ConversationStatus

if TYPE_CHECKING:
    from ..analysis.analyzer import AnalysisResult


class ConversationStorage:
    """Manages conversation persistence with SQLite + JSON."""

    def __init__(self, db_path: Path, conversations_dir: Path):
        self.db_path = db_path
        self.conversations_dir = conversations_dir
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    llm1_model TEXT NOT NULL,
                    llm2_model TEXT NOT NULL,
                    turn_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            # Check if analysis_results table exists and needs migration
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='analysis_results'"
            )
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Check if migration is needed:
                # 1. segment_start column missing, OR
                # 2. Primary key is not the composite key (check by looking at table schema)
                cursor = conn.execute("PRAGMA table_info(analysis_results)")
                columns = [row[1] for row in cursor.fetchall()]

                # Check if we have the old primary key by looking at the CREATE statement
                cursor = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type='table' AND name='analysis_results'"
                )
                create_sql = cursor.fetchone()[0]
                needs_migration = (
                    'segment_start' not in columns or
                    'PRIMARY KEY (conversation_id, segment_start, segment_end)' not in create_sql
                )

                if needs_migration:
                    # Migration: recreate table with new composite primary key
                    conn.execute("""
                        CREATE TABLE analysis_results_new (
                            conversation_id TEXT NOT NULL,
                            segment_start INTEGER NOT NULL DEFAULT -5,
                            segment_end INTEGER,
                            topics TEXT,
                            mood TEXT,
                            trajectory TEXT,
                            analyzed_at TEXT NOT NULL,
                            PRIMARY KEY (conversation_id, segment_start, segment_end),
                            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                        )
                    """)
                    # Copy data, using existing segment values if columns exist, else defaults
                    if 'segment_start' in columns:
                        conn.execute("""
                            INSERT INTO analysis_results_new
                            (conversation_id, segment_start, segment_end, topics, mood, trajectory, analyzed_at)
                            SELECT conversation_id, segment_start, segment_end, topics, mood, trajectory, analyzed_at
                            FROM analysis_results
                        """)
                    else:
                        conn.execute("""
                            INSERT INTO analysis_results_new
                            (conversation_id, segment_start, segment_end, topics, mood, trajectory, analyzed_at)
                            SELECT conversation_id, -5, NULL, topics, mood, trajectory, analyzed_at
                            FROM analysis_results
                        """)
                    conn.execute("DROP TABLE analysis_results")
                    conn.execute("ALTER TABLE analysis_results_new RENAME TO analysis_results")
            else:
                # Create fresh table with new schema
                conn.execute("""
                    CREATE TABLE analysis_results (
                        conversation_id TEXT NOT NULL,
                        segment_start INTEGER NOT NULL DEFAULT -5,
                        segment_end INTEGER,  -- NULL means "to the end"
                        topics TEXT,  -- JSON (dict or array for backward compat)
                        mood TEXT,  -- JSON (legacy)
                        trajectory TEXT,
                        analysis_json TEXT,  -- Full AnalysisResult as JSON
                        analyzed_at TEXT NOT NULL,
                        PRIMARY KEY (conversation_id, segment_start, segment_end),
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    )
                """)
            # Add analysis_json column if it doesn't exist (migration for existing DBs)
            cursor = conn.execute("PRAGMA table_info(analysis_results)")
            columns = [row[1] for row in cursor.fetchall()]
            if "analysis_json" not in columns:
                conn.execute("ALTER TABLE analysis_results ADD COLUMN analysis_json TEXT")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_models
                ON conversations(llm1_model, llm2_model)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_status
                ON conversations(status)
            """)
            conn.commit()

    def _conversation_json_path(self, conversation_id: str) -> Path:
        """Get the JSON file path for a conversation."""
        return self.conversations_dir / f"{conversation_id}.json"

    def save(self, conversation: Conversation) -> None:
        """Save a conversation to both SQLite and JSON."""
        # Save full conversation to JSON
        json_path = self._conversation_json_path(conversation.id)
        with open(json_path, "w") as f:
            json.dump(conversation.model_dump(mode="json"), f, indent=2, default=str)

        # Update metadata in SQLite
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO conversations
                (id, llm1_model, llm2_model, turn_count, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation.id,
                conversation.llm1_model,
                conversation.llm2_model,
                conversation.turn_count,
                conversation.status.value,
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat(),
            ))
            conn.commit()

    def load(self, conversation_id: str) -> Conversation | None:
        """Load a conversation by ID."""
        json_path = self._conversation_json_path(conversation_id)
        if not json_path.exists():
            return None

        with open(json_path) as f:
            data = json.load(f)
        return Conversation.model_validate(data)

    def list_conversations(
        self,
        llm1_model: str | None = None,
        llm2_model: str | None = None,
        status: ConversationStatus | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """
        List conversations with optional filters.

        Returns lightweight metadata dicts, not full Conversation objects.
        """
        query = "SELECT id, llm1_model, llm2_model, turn_count, status, created_at, updated_at FROM conversations WHERE 1=1"
        params: list = []

        if llm1_model:
            query += " AND llm1_model = ?"
            params.append(llm1_model)
        if llm2_model:
            query += " AND llm2_model = ?"
            params.append(llm2_model)
        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_conversations_for_analysis(
        self,
        llm1_model: str | None = None,
        llm2_model: str | None = None,
    ) -> Iterator[Conversation]:
        """
        Get conversations that need analysis (completed but not analyzed).

        Yields full Conversation objects.
        """
        query = """
            SELECT c.id FROM conversations c
            LEFT JOIN analysis_results a ON c.id = a.conversation_id
            WHERE a.conversation_id IS NULL
            AND c.status IN ('completed', 'paused')
        """
        params: list = []

        if llm1_model:
            query += " AND c.llm1_model = ?"
            params.append(llm1_model)
        if llm2_model:
            query += " AND c.llm2_model = ?"
            params.append(llm2_model)

        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()

        for (conv_id,) in rows:
            conversation = self.load(conv_id)
            if conversation:
                yield conversation

    def save_analysis(
        self,
        conversation_id: str,
        result: AnalysisResult,
        segment_start: int = -5,
        segment_end: int | None = None,
    ) -> None:
        """Save analysis results for a conversation segment.

        Args:
            conversation_id: The conversation ID
            result: AnalysisResult object with all analysis data
            segment_start: Start index for message segment (default: -5, last 5 messages)
            segment_end: End index for message segment (default: None, to the end)
        """
        # Convert result to JSON for storage
        result_dict = asdict(result)
        analysis_json = json.dumps(result_dict)

        # Also store legacy columns for backward compatibility
        topics_json = json.dumps(result.topics)  # now a dict
        trajectory = result.trajectory

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO analysis_results
                (conversation_id, segment_start, segment_end, topics, trajectory, analysis_json, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id, segment_start, segment_end)
                DO UPDATE SET topics=excluded.topics, trajectory=excluded.trajectory,
                              analysis_json=excluded.analysis_json, analyzed_at=excluded.analyzed_at
            """, (
                conversation_id,
                segment_start,
                segment_end,
                topics_json,
                trajectory,
                analysis_json,
                datetime.now(timezone.utc).isoformat(),
            ))
            # Update conversation status
            conn.execute("""
                UPDATE conversations SET status = ? WHERE id = ?
            """, (ConversationStatus.ANALYZED.value, conversation_id))
            conn.commit()

    def get_analysis_report(
        self,
        llm1_model: str | None = None,
        llm2_model: str | None = None,
        segment_start: int | None = None,
        segment_end: int | None = None,
    ) -> list[dict]:
        """
        Get aggregated analysis report by LLM pair and segment.

        Returns list of dicts with pair info, segment, and aggregated analysis.
        """
        # Get all analyses and aggregate in Python for simplicity
        analyses = self.get_all_analyses(llm1_model, llm2_model)

        # Group by (llm1, llm2, segment_start, segment_end)
        from collections import defaultdict

        groups: dict[tuple, list[dict]] = defaultdict(list)
        for a in analyses:
            if segment_start is not None and a["segment_start"] != segment_start:
                continue
            if segment_end is not None:
                if segment_end == -1 and a["segment_end"] is not None:
                    continue
                elif segment_end != -1 and a["segment_end"] != segment_end:
                    continue

            key = (a["llm1_model"], a["llm2_model"], a["segment_start"], a["segment_end"])
            groups[key].append(a)

        results = []
        for (llm1, llm2, seg_start, seg_end), group in groups.items():
            # Aggregate topics
            topic_scores: dict[str, list[float]] = defaultdict(list)
            for a in group:
                for topic, score in a.get("topics", {}).items():
                    topic_scores[topic].append(score)

            avg_topics = {t: sum(s) / len(s) for t, s in topic_scores.items()}
            top_topics = sorted(avg_topics.items(), key=lambda x: -x[1])[:10]

            # Aggregate mood dimensions
            n = len(group)
            avg_warmth = sum(a.get("warmth", 0) for a in group) / n
            avg_energy = sum(a.get("energy", 0) for a in group) / n
            avg_depth = sum(a.get("depth", 0) for a in group) / n

            results.append({
                "llm1_model": llm1,
                "llm2_model": llm2,
                "segment_start": seg_start,
                "segment_end": seg_end,
                "conversation_count": n,
                "top_topics": top_topics,
                "avg_warmth": avg_warmth,
                "avg_energy": avg_energy,
                "avg_depth": avg_depth,
            })

        return sorted(results, key=lambda x: -x["conversation_count"])

    def get_all_analyses(
        self,
        llm1_model: str | None = None,
        llm2_model: str | None = None,
    ) -> list[dict]:
        """
        Get all analysis results with conversation metadata.

        Returns list of dicts with conversation info and full analysis data.
        """
        query = """
            SELECT
                c.id,
                c.llm1_model,
                c.llm2_model,
                c.turn_count,
                a.segment_start,
                a.segment_end,
                a.analysis_json,
                a.analyzed_at
            FROM conversations c
            JOIN analysis_results a ON c.id = a.conversation_id
            WHERE a.analysis_json IS NOT NULL
        """
        params: list = []

        if llm1_model:
            query += " AND c.llm1_model = ?"
            params.append(llm1_model)
        if llm2_model:
            query += " AND c.llm2_model = ?"
            params.append(llm2_model)

        query += " ORDER BY a.analyzed_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            try:
                analysis = json.loads(row["analysis_json"])
            except json.JSONDecodeError:
                continue

            results.append({
                "conversation_id": row["id"],
                "llm1_model": row["llm1_model"],
                "llm2_model": row["llm2_model"],
                "turn_count": row["turn_count"],
                "segment_start": row["segment_start"],
                "segment_end": row["segment_end"],
                "analyzed_at": row["analyzed_at"],
                **analysis,
            })

        return results

    def clear_analysis(self, conversation_id: str) -> None:
        """Clear analysis results for a conversation (used when continuing)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analysis_results WHERE conversation_id = ?", (conversation_id,))
            conn.commit()

    def delete(self, conversation_id: str) -> bool:
        """Delete a conversation and its analysis."""
        json_path = self._conversation_json_path(conversation_id)
        deleted = False

        if json_path.exists():
            json_path.unlink()
            deleted = True

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM analysis_results WHERE conversation_id = ?", (conversation_id,))
            result = conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            conn.commit()
            if result.rowcount > 0:
                deleted = True

        return deleted
