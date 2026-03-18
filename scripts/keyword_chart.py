"""Generate a combined bar chart comparing keyword frequency across model pairs.

Outputs a self-contained HTML file matching the llm2llm dashboard aesthetic.
"""

import json
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent

COLORS = ['#6644aa', '#996600', '#007755', '#0088aa', '#cc2222', '#cc5577']


def short(m):
    """Shorten model names for display."""
    return (m.replace('claude-', '').replace('mistralai/', '').replace('openai/', '')
            .replace('qwen/', '').replace('moonshotai/', '').replace('google/', '')
            .replace('-20250514', '').replace('-20250929', '').replace('-20251101', '')
            .replace('-20251001', '').replace('-20240229', '').replace('-20241022', '')
            .replace('-20240307', '').replace('-20250219', '').replace('-20250805', ''))


def count_keyword(convs, keyword):
    """Count keyword occurrences per model pair, normalized by message count."""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    pair_hits = defaultdict(int)
    pair_msgs = defaultdict(int)

    for c in convs:
        path = PROJECT_ROOT / "conversations" / f"{c['id']}.json"
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        msgs = data.get("messages", [])
        total = sum(len(pattern.findall(m["content"])) for m in msgs)
        pair = f"{short(c['llm1_model'])}  \u00d7  {short(c['llm2_model'])}"
        pair_hits[pair] += total
        pair_msgs[pair] += c['turn_count']

    return {k: pair_hits[k] / pair_msgs[k] for k in pair_hits if pair_msgs[k] > 0}


def make_chart(keywords, output_path=None):
    """Generate a self-contained HTML bar chart for multiple keywords."""
    db = sqlite3.connect(PROJECT_ROOT / "data" / "llm2llm.db")
    db.row_factory = sqlite3.Row
    convs = db.execute("SELECT id, llm1_model, llm2_model, turn_count FROM conversations").fetchall()

    results = {}
    for kw in keywords:
        results[kw] = count_keyword(convs, kw)

    # Get all pairs with hits, sorted by max score, cap at top 10
    all_pairs = sorted(
        set().union(*[r.keys() for r in results.values()]),
        key=lambda p: max(results[kw].get(p, 0) for kw in keywords),
        reverse=True,
    )
    all_pairs = [p for p in all_pairs if any(results[kw].get(p, 0) > 0 for kw in keywords)]
    all_pairs = all_pairs[:10]

    # Find max value for scaling
    global_max = max(
        (results[kw].get(p, 0) for kw in keywords for p in all_pairs),
        default=1,
    )

    # Per-keyword max for column width proportioning
    kw_maxes = {kw: max((results[kw].get(p, 0) for p in all_pairs), default=0) for kw in keywords}

    # Build chart columns HTML
    columns_html = ''
    for i, kw in enumerate(keywords):
        color = COLORS[i % len(COLORS)]
        col_max = kw_maxes[kw] or 1
        flex = col_max / global_max if global_max else 1
        rows_html = ''
        for p in all_pairs:
            v = results[kw].get(p, 0)
            pct = (v / col_max * 75) if col_max else 0
            label = f'{v:.2f}' if v > 0 else ''
            opacity = 0.3 + 0.7 * (v / global_max) if global_max and v > 0 else 0.08
            rows_html += f'''
                <div class="row">
                    <div class="bar-track">
                        <div class="bar" style="width: {pct}%; background: {color}; opacity: {opacity};"></div>
                        <span class="bar-label" style="color: {color};">{label}</span>
                    </div>
                </div>'''

        columns_html += f'''
            <div class="chart-col" style="flex: {flex:.2f};">
                <div class="col-title" style="color: {color};">{kw}</div>
                <div class="rows">{rows_html}
                </div>
                <div class="axis-label">hits / message</div>
            </div>'''

    # Build pair labels — bold pairs that have hits across all keywords
    labels_html = ''
    for p in all_pairs:
        has_all = all(results[kw].get(p, 0) > 0 for kw in keywords)
        style = ' style="font-weight: 600; color: #1a1a1a;"' if has_all else ''
        labels_html += f'<div class="pair-label"{style}>{p}</div>'

    html = f'''<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Keyword frequency — llm2llm</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600&display=swap');

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    font-family: 'IBM Plex Mono', 'SF Mono', 'Fira Code', monospace;
    background: #fafafa;
    color: #1a1a1a;
    padding: 48px;
    display: flex;
    justify-content: center;
}}

.container {{
    max-width: 1200px;
    width: 100%;
}}

h1 {{
    font-size: 14px;
    font-weight: 400;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #666;
    margin-bottom: 32px;
    padding-bottom: 12px;
    border-bottom: 1px solid #d0d0d0;
}}

.chart {{
    display: flex;
    gap: 0;
}}

.labels {{
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    padding-top: 36px;
    flex-shrink: 0;
}}

.pair-label {{
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 20px;
    font-size: 11px;
    color: #555;
    white-space: nowrap;
}}

.chart-col {{
    flex: 1;
    min-width: 0;
    padding: 0 12px;
    padding-right: 48px;
    border-left: 1px solid #e0e0e0;
    overflow: hidden;
}}

.col-title {{
    font-size: 13px;
    font-weight: 500;
    letter-spacing: 0.02em;
    margin-bottom: 12px;
    height: 24px;
    display: flex;
    align-items: center;
}}

.rows {{
    display: flex;
    flex-direction: column;
}}

.row {{
    height: 36px;
    display: flex;
    align-items: center;
}}

.bar-track {{
    width: 100%;
    height: 20px;
    display: flex;
    align-items: center;
}}

.bar {{
    height: 100%;
    border-radius: 2px;
    transition: width 0.4s ease;
    min-width: 0;
}}

.bar-label {{
    font-size: 10px;
    font-weight: 400;
    padding-left: 8px;
    flex-shrink: 0;
}}

.axis-label {{
    font-size: 9px;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 12px;
    text-align: center;
}}
</style>
</head>
<body>
<div class="container">
    <h1>Keyword frequency by model pair</h1>
    <div class="chart">
        <div class="labels">
            {labels_html}
        </div>
        {columns_html}
    </div>
</div>
</body>
</html>'''

    out = output_path or '/tmp/keyword_chart.html'
    Path(out).write_text(html)
    print(f"Saved to {out}")
    db.close()


if __name__ == '__main__':
    keywords = sys.argv[1:] or ['consciousness', 'pizza']
    output = None
    if '--output' in keywords:
        idx = keywords.index('--output')
        output = keywords[idx + 1]
        keywords = keywords[:idx] + keywords[idx + 2:]
    make_chart(keywords, output)
