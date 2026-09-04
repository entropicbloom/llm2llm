#!/usr/bin/env python3
"""Verify that every excerpt in insights.json is a verbatim quote from the stored conversation.

Each excerpt entry may carry a `turn` number; fragments joined with " ... " are checked
individually. Whitespace and markdown emphasis (*, **, _) are normalized before matching.

Usage: python scripts/verify_insights.py [path/to/insights.json]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("—", "-").replace("–", "-")
    s = re.sub(r"[*_`#>]+", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def main(path: str) -> int:
    ins = json.loads(Path(path).read_text())
    bad = 0
    for dyn in ins["dynamics"]:
        cid = dyn.get("conversationId")
        if not cid:
            continue
        f = ROOT / "conversations" / f"{cid}.json"
        if not f.exists():
            print(f"MISSING conversation {cid[:8]} for '{dyn['title']}'")
            bad += 1
            continue
        msgs = {m["turn_number"]: m for m in json.loads(f.read_text())["messages"]}
        for ex in dyn["excerpt"]:
            if ex.get("speaker") == "Both" or ex["text"].startswith("["):
                continue
            turn = ex.get("turn")
            haystacks = [norm(msgs[turn]["content"])] if turn in msgs else [norm(m["content"]) for m in msgs.values()]
            for frag in ex["text"].split(" ... "):
                nf = norm(frag)
                if not any(nf in h for h in haystacks):
                    print(f"NOT VERBATIM  {dyn['title']!r}  {cid[:8]} turn={turn} speaker={ex.get('speaker')}\n    {frag[:120]!r}")
                    bad += 1
    print("errors:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "llm2llm/dashboard/assets/insights.json")))
