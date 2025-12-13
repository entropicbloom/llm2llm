"""Storage layer for conversations - SQLite metadata + JSON files."""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator

from .schemas import Conversation, ConversationStatus


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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_results (
                    conversation_id TEXT PRIMARY KEY,
                    topics TEXT,  -- JSON array of topics
                    mood TEXT,
                    trajectory TEXT,
                    analyzed_at TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
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
        topics: list[str],
        mood: str,
        trajectory: str,
    ) -> None:
        """Save analysis results for a conversation."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_results
                (conversation_id, topics, mood, trajectory, analyzed_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                conversation_id,
                json.dumps(topics),
                mood,
                trajectory,
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
    ) -> list[dict]:
        """
        Get aggregated analysis report by LLM pair.

        Returns list of dicts with pair info and aggregated analysis.
        """
        query = """
            SELECT
                c.llm1_model,
                c.llm2_model,
                COUNT(*) as conversation_count,
                GROUP_CONCAT(a.topics) as all_topics,
                GROUP_CONCAT(a.mood) as all_moods,
                GROUP_CONCAT(a.trajectory) as all_trajectories
            FROM conversations c
            JOIN analysis_results a ON c.id = a.conversation_id
            WHERE 1=1
        """
        params: list = []

        if llm1_model:
            query += " AND c.llm1_model = ?"
            params.append(llm1_model)
        if llm2_model:
            query += " AND c.llm2_model = ?"
            params.append(llm2_model)

        query += " GROUP BY c.llm1_model, c.llm2_model ORDER BY conversation_count DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            # Parse aggregated topics (GROUP_CONCAT joins JSON arrays with commas)
            # The data looks like: '["topic1","topic2"],["topic3"]' - need to parse carefully
            all_topics_str = row["all_topics"] or ""
            all_topics = []
            # Split by ],[ to separate JSON arrays, then reconstruct and parse each
            if all_topics_str:
                # Try parsing the concatenated string - it's multiple JSON arrays joined by commas
                # We need to find complete JSON arrays
                depth = 0
                current = ""
                for char in all_topics_str:
                    current += char
                    if char == "[":
                        depth += 1
                    elif char == "]":
                        depth -= 1
                        if depth == 0:
                            try:
                                parsed = json.loads(current.strip().lstrip(","))
                                if isinstance(parsed, list):
                                    all_topics.extend(parsed)
                            except json.JSONDecodeError:
                                pass  # Skip malformed entries
                            current = ""

            # Count topic frequencies
            topic_counts: dict[str, int] = {}
            for topic in all_topics:
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

            # Count mood frequencies
            moods = [m for m in (row["all_moods"] or "").split(",") if m]
            mood_counts: dict[str, int] = {}
            for mood in moods:
                mood_counts[mood] = mood_counts.get(mood, 0) + 1

            results.append({
                "llm1_model": row["llm1_model"],
                "llm2_model": row["llm2_model"],
                "conversation_count": row["conversation_count"],
                "top_topics": sorted(topic_counts.items(), key=lambda x: -x[1])[:10],
                "mood_distribution": sorted(mood_counts.items(), key=lambda x: -x[1]),
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
