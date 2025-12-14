"""Data layer for dashboard - queries and aggregation."""

from pathlib import Path
import sqlite3
import json


def infer_provider(model_id: str) -> str:
    """Infer provider from model ID."""
    if model_id.startswith("claude-"):
        return "Anthropic"
    elif model_id.startswith("mistralai/"):
        return "Mistral"
    elif model_id.startswith("openai/"):
        return "OpenAI"
    elif model_id.startswith("google/"):
        return "Google"
    else:
        return "Other"


def load_all_analyses(db_path: Path) -> list[dict]:
    """Load all analysis results with conversation metadata."""
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
        ORDER BY a.analyzed_at DESC
    """

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(query).fetchall()

    results = []
    for row in rows:
        try:
            analysis = json.loads(row["analysis_json"])
        except json.JSONDecodeError:
            continue  # Skip malformed entries

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
