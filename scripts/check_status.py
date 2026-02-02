#!/usr/bin/env python3
"""Check for conversations that need attention (non-analyzed, incomplete, orphaned)."""

import sqlite3
import json
from pathlib import Path


def main():
    base_dir = Path(__file__).parent.parent
    db_path = base_dir / "data" / "llm2llm.db"
    convos_dir = base_dir / "conversations"

    if not db_path.exists():
        print("ERROR: Database not found at", db_path)
        return

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Get all conversation IDs from database
    db_convos = {row["id"]: dict(row) for row in conn.execute(
        "SELECT id, llm1_model, llm2_model, turn_count, status FROM conversations"
    )}

    # Get all conversation JSON files
    json_files = {f.stem: f for f in convos_dir.glob("*.json")}

    # Find orphaned JSON files (not in DB)
    orphaned = set(json_files.keys()) - set(db_convos.keys())

    # Find missing JSON files (in DB but no file)
    missing_json = set(db_convos.keys()) - set(json_files.keys())

    # Categorize DB conversations
    needs_analysis = []
    incomplete = []
    empty = []

    for cid, c in db_convos.items():
        if c["turn_count"] == 0:
            empty.append(c)
        elif c["turn_count"] < 50 and c["status"] == "active":
            incomplete.append(c)
        elif c["status"] in ("completed", "paused") and c["status"] != "analyzed":
            needs_analysis.append(c)

    # Print results
    def short_model(m):
        return m.split("/")[-1][:20] if "/" in m else m[:20]

    def print_convo(c):
        print(f"  {c['id'][:12]}  {c['turn_count']:3} turns  {short_model(c['llm1_model']):20} × {short_model(c['llm2_model']):20}")

    if needs_analysis:
        print(f"\n=== NEEDS ANALYSIS ({len(needs_analysis)}) ===")
        for c in sorted(needs_analysis, key=lambda x: x["turn_count"], reverse=True):
            print_convo(c)

    if incomplete:
        print(f"\n=== INCOMPLETE ({len(incomplete)}) ===")
        for c in sorted(incomplete, key=lambda x: x["turn_count"], reverse=True):
            print_convo(c)

    if empty:
        print(f"\n=== EMPTY ({len(empty)}) ===")
        for c in empty:
            print_convo(c)

    if orphaned:
        print(f"\n=== ORPHANED JSON FILES ({len(orphaned)}) ===")
        print("  (JSON exists but not in database)")
        for cid in sorted(orphaned):
            # Try to read the JSON to get info
            try:
                with open(json_files[cid]) as f:
                    data = json.load(f)
                turns = len(data.get("messages", []))
                llm1 = data.get("llm1_model", "?")
                llm2 = data.get("llm2_model", "?")
                print(f"  {cid[:12]}  {turns:3} turns  {short_model(llm1):20} × {short_model(llm2):20}")
            except Exception as e:
                print(f"  {cid[:12]}  (error reading: {e})")

    if missing_json:
        print(f"\n=== MISSING JSON FILES ({len(missing_json)}) ===")
        print("  (in database but JSON file missing)")
        for cid in sorted(missing_json):
            c = db_convos[cid]
            print_convo(c)

    # Summary
    total_issues = len(needs_analysis) + len(incomplete) + len(empty) + len(orphaned) + len(missing_json)
    if total_issues == 0:
        print("\n✓ All conversations are complete and analyzed!")
    else:
        print(f"\n--- {total_issues} total issues ---")

    conn.close()


if __name__ == "__main__":
    main()
