"""Data layer for dashboard - queries and aggregation."""

from collections import defaultdict
from pathlib import Path
import sqlite3
import json
from typing import Optional


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


def get_provider_display_name(model_id: str) -> str:
    """Get a nice display name for the model."""
    # Remove provider prefix if present
    if "/" in model_id:
        model_id = model_id.split("/", 1)[1]
    return model_id


def load_conversation(conversations_dir: Path, conversation_id: str) -> Optional[dict]:
    """Load a conversation's full content from JSON file."""
    json_path = conversations_dir / f"{conversation_id}.json"
    if not json_path.exists():
        return None

    with open(json_path) as f:
        return json.load(f)


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


def get_models_by_provider(analyses: list[dict]) -> dict[str, list[str]]:
    """Group models by provider."""
    providers: dict[str, set[str]] = defaultdict(set)

    for a in analyses:
        for model in [a["llm1_model"], a["llm2_model"]]:
            provider = infer_provider(model)
            providers[provider].add(model)

    return {p: sorted(models) for p, models in sorted(providers.items())}


def aggregate_model_stats(analyses: list[dict], model_id: str) -> dict:
    """
    Aggregate statistics for a specific model across all conversations
    where it participated (as either llm1 or llm2).
    """
    # Filter analyses where this model participated
    relevant = [a for a in analyses if a["llm1_model"] == model_id or a["llm2_model"] == model_id]

    if not relevant:
        return {
            "model_id": model_id,
            "conversation_count": 0,
            "avg_topics": {},
            "avg_warmth": 0.0,
            "avg_energy": 0.0,
            "avg_depth": 0.0,
            "avg_tone_playful": 0.5,
            "trajectory_distribution": {},
            "ending_attempt_rate": 0.0,
            "is_lengthy_rate": 0.0,
            "is_structured_rate": 0.0,
            "partner_stats": {},
        }

    n = len(relevant)

    # Aggregate topic scores
    topic_sums: dict[str, float] = defaultdict(float)
    topic_counts: dict[str, int] = defaultdict(int)
    for a in relevant:
        for topic, score in a.get("topics", {}).items():
            topic_sums[topic] += score
            topic_counts[topic] += 1

    avg_topics = {
        topic: topic_sums[topic] / topic_counts[topic]
        for topic in topic_sums
    }
    # Sort by average score
    avg_topics = dict(sorted(avg_topics.items(), key=lambda x: -x[1]))

    # Aggregate mood dimensions
    avg_warmth = sum(a.get("warmth", 0.0) for a in relevant) / n
    avg_energy = sum(a.get("energy", 0.0) for a in relevant) / n
    avg_depth = sum(a.get("depth", 0.0) for a in relevant) / n
    avg_tone_playful = sum(a.get("tone_playful", 0.5) for a in relevant) / n

    # Trajectory distribution
    trajectory_counts: dict[str, int] = defaultdict(int)
    for a in relevant:
        trajectory_counts[a.get("trajectory", "unknown")] += 1

    # Ending attempt rate
    ending_attempts = sum(1 for a in relevant if a.get("ending_attempt", False))
    ending_attempt_rate = ending_attempts / n

    # Structure rates
    is_lengthy_rate = sum(1 for a in relevant if a.get("is_lengthy", False)) / n
    is_structured_rate = sum(1 for a in relevant if a.get("is_structured", False)) / n

    # Partner-specific stats
    partner_stats: dict[str, dict] = {}
    for a in relevant:
        partner = a["llm2_model"] if a["llm1_model"] == model_id else a["llm1_model"]
        if partner not in partner_stats:
            partner_stats[partner] = {
                "conversations": [],
                "count": 0,
            }
        partner_stats[partner]["conversations"].append(a)
        partner_stats[partner]["count"] += 1

    # Compute aggregates for each partner
    for partner, stats in partner_stats.items():
        convs = stats["conversations"]
        pn = len(convs)

        # Average topics for this partner
        ptopic_sums: dict[str, float] = defaultdict(float)
        ptopic_counts: dict[str, int] = defaultdict(int)
        for a in convs:
            for topic, score in a.get("topics", {}).items():
                ptopic_sums[topic] += score
                ptopic_counts[topic] += 1

        stats["avg_topics"] = {
            topic: ptopic_sums[topic] / ptopic_counts[topic]
            for topic in ptopic_sums
        }
        stats["avg_topics"] = dict(sorted(stats["avg_topics"].items(), key=lambda x: -x[1]))

        stats["avg_warmth"] = sum(a.get("warmth", 0.0) for a in convs) / pn
        stats["avg_energy"] = sum(a.get("energy", 0.0) for a in convs) / pn
        stats["avg_depth"] = sum(a.get("depth", 0.0) for a in convs) / pn

        ptraj_counts: dict[str, int] = defaultdict(int)
        for a in convs:
            ptraj_counts[a.get("trajectory", "unknown")] += 1
        stats["trajectory_distribution"] = dict(ptraj_counts)

        # Remove the raw conversations list to save memory
        del stats["conversations"]

    return {
        "model_id": model_id,
        "conversation_count": n,
        "avg_topics": avg_topics,
        "avg_warmth": avg_warmth,
        "avg_energy": avg_energy,
        "avg_depth": avg_depth,
        "avg_tone_playful": avg_tone_playful,
        "trajectory_distribution": dict(trajectory_counts),
        "ending_attempt_rate": ending_attempt_rate,
        "is_lengthy_rate": is_lengthy_rate,
        "is_structured_rate": is_structured_rate,
        "partner_stats": partner_stats,
    }


def aggregate_pair_stats(analyses: list[dict]) -> list[dict]:
    """
    Aggregate statistics for each unique model pair.
    Returns a list of pair stats sorted by conversation count.
    """
    from collections import defaultdict

    # Group by ordered pair (llm1, llm2)
    pair_data: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for a in analyses:
        pair = (a["llm1_model"], a["llm2_model"])
        pair_data[pair].append(a)

    results = []
    for (llm1, llm2), convs in pair_data.items():
        n = len(convs)

        # Aggregate topic scores
        topic_sums: dict[str, float] = defaultdict(float)
        topic_counts: dict[str, int] = defaultdict(int)
        for a in convs:
            for topic, score in a.get("topics", {}).items():
                topic_sums[topic] += score
                topic_counts[topic] += 1

        avg_topics = {
            topic: topic_sums[topic] / topic_counts[topic]
            for topic in topic_sums
        }
        avg_topics = dict(sorted(avg_topics.items(), key=lambda x: -x[1]))

        # Aggregate mood dimensions
        avg_warmth = sum(a.get("warmth", 0.0) for a in convs) / n
        avg_energy = sum(a.get("energy", 0.0) for a in convs) / n
        avg_depth = sum(a.get("depth", 0.0) for a in convs) / n
        avg_tone_playful = sum(a.get("tone_playful", 0.5) for a in convs) / n

        # Trajectory distribution
        trajectory_counts: dict[str, int] = defaultdict(int)
        for a in convs:
            trajectory_counts[a.get("trajectory", "unknown")] += 1
        dominant_trajectory = max(trajectory_counts.items(), key=lambda x: x[1])[0] if trajectory_counts else "unknown"

        # Rates
        ending_attempt_rate = sum(1 for a in convs if a.get("ending_attempt", False)) / n
        is_lengthy_rate = sum(1 for a in convs if a.get("is_lengthy", False)) / n
        is_structured_rate = sum(1 for a in convs if a.get("is_structured", False)) / n

        # Average turn count
        avg_turns = sum(a.get("turn_count", 0) for a in convs) / n

        results.append({
            "llm1": llm1,
            "llm2": llm2,
            "conversation_count": n,
            "avg_topics": avg_topics,
            "avg_warmth": avg_warmth,
            "avg_energy": avg_energy,
            "avg_depth": avg_depth,
            "avg_tone_playful": avg_tone_playful,
            "dominant_trajectory": dominant_trajectory,
            "trajectory_distribution": dict(trajectory_counts),
            "ending_attempt_rate": ending_attempt_rate,
            "is_lengthy_rate": is_lengthy_rate,
            "is_structured_rate": is_structured_rate,
            "avg_turns": avg_turns,
        })

    return sorted(results, key=lambda x: -x["conversation_count"])
