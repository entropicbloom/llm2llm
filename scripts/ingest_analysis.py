#!/usr/bin/env python3
"""Ingest manually produced analysis JSON files (e.g. written by Claude Code subagents).

Each input file is JSON with:
  {"conversation_id": "<full id>", "title": "<optional title>",
   "segments": [{"start": -10, "end": null, "analysis": {<AnalysisResult fields>}},
                {"start": 15, "end": 25, "analysis": {...}}]}

Usage: python scripts/ingest_analysis.py file1.json [file2.json ...]
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from llm2llm.analysis.analyzer import AnalysisResult  # noqa: E402
from llm2llm.cli import get_config_and_storage  # noqa: E402


def main(paths: list[str]) -> None:
    config, storage = get_config_and_storage()
    for p in paths:
        doc = json.loads(Path(p).read_text())
        cid = doc["conversation_id"]
        for seg in doc["segments"]:
            a = seg["analysis"]
            result = AnalysisResult(
                topics={k: float(v) for k, v in a["topics"].items()},
                warmth=float(a["warmth"]),
                energy=float(a["energy"]),
                depth=float(a["depth"]),
                tone_playful=float(a["tone_playful"]),
                spirituality=float(a.get("spirituality", 0.0)),
                is_lengthy=bool(a["is_lengthy"]),
                is_structured=bool(a["is_structured"]),
                trajectory=a["trajectory"],
                trajectory_strength=float(a.get("trajectory_strength", 1.0)),
                ending_attempt=bool(a["ending_attempt"]),
                ending_graceful=a.get("ending_graceful"),
            )
            if seg.get("end") is None:
                # SQLite treats NULL as distinct in the primary key, so the upsert would duplicate rows.
                with sqlite3.connect(storage.db_path) as conn:
                    conn.execute(
                        "DELETE FROM analysis_results WHERE conversation_id = ? AND segment_start = ? AND segment_end IS NULL",
                        (cid, seg["start"]),
                    )
                    conn.commit()
            storage.save_analysis(cid, result, segment_start=seg["start"], segment_end=seg.get("end"))
            print(f"saved {cid[:8]} segment {seg['start']}:{seg.get('end')}")
        if doc.get("title"):
            with sqlite3.connect(storage.db_path) as conn:
                conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (doc["title"], cid))
                conn.commit()
            print(f"title  {cid[:8]}: {doc['title']}")


if __name__ == "__main__":
    main(sys.argv[1:])
