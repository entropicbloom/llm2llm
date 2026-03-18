"""Generate a combined bar chart comparing keyword frequency across model pairs."""

import json
import re
import sqlite3
import sys
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


PROJECT_ROOT = Path(__file__).parent.parent

PALETTE = ['#7C3AED', '#E86A17', '#10A37F', '#2563EB', '#DC2626', '#D4AF37']


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
    """Generate a combined horizontal bar chart for multiple keywords."""
    db = sqlite3.connect(PROJECT_ROOT / "data" / "llm2llm.db")
    db.row_factory = sqlite3.Row
    convs = db.execute("SELECT id, llm1_model, llm2_model, turn_count FROM conversations").fetchall()

    results = {}
    for kw in keywords:
        results[kw] = count_keyword(convs, kw)

    # Get all pairs with hits, sorted by first keyword's rate
    all_pairs = sorted(
        set().union(*[r.keys() for r in results.values()]),
        key=lambda p: results[keywords[0]].get(p, 0),
        reverse=True,
    )
    # Keep only pairs that have hits for at least one keyword, cap at top 10
    all_pairs = [p for p in all_pairs if any(results[kw].get(p, 0) > 0 for kw in keywords)]
    # Rank by max score across any keyword to keep the most interesting pairs
    all_pairs.sort(key=lambda p: max(results[kw].get(p, 0) for kw in keywords), reverse=True)
    all_pairs = all_pairs[:10]

    n = len(keywords)
    fig_w = 7 * n
    fig_h = max(5, len(all_pairs) * 0.38)
    fig, axes = plt.subplots(1, n, figsize=(fig_w, fig_h), sharey=True)
    if n == 1:
        axes = [axes]

    fig.patch.set_facecolor('#0f0f0f')
    fig.suptitle('Keyword frequency by model pair',
                 fontsize=15, fontweight='600', color='#e0e0e0',
                 fontfamily='monospace', y=0.99)

    y = np.arange(len(all_pairs))
    h = 0.55

    for i, kw in enumerate(keywords):
        ax = axes[i]
        ax.set_facecolor('#0f0f0f')
        vals = [results[kw].get(p, 0) for p in all_pairs]
        color = PALETTE[i % len(PALETTE)]
        max_val = max(vals) if vals else 1

        # Gradient-like effect: vary alpha by value
        bar_colors = [(*matplotlib.colors.to_rgb(color), 0.3 + 0.65 * (v / max_val) if max_val else 0.3) for v in vals]
        bars = ax.barh(y, vals, h, color=bar_colors, edgecolor=color, linewidth=0.5)

        ax.set_title(kw, fontsize=13, color=color, fontweight='600',
                     fontfamily='monospace', pad=12)
        ax.set_xlabel('hits / message', fontsize=9, color='#888', fontfamily='monospace')
        ax.tick_params(colors='#888', labelsize=8)
        ax.invert_yaxis()

        # Minimal grid
        ax.xaxis.grid(True, color='#222', linewidth=0.5)
        ax.set_axisbelow(True)
        for spine in ax.spines.values():
            spine.set_visible(False)

        if i == 0:
            ax.set_yticks(y)
            ax.set_yticklabels(all_pairs, fontsize=7.5, fontfamily='monospace', color='#ccc')

        for bar, v in zip(bars, vals):
            if v > 0:
                ax.text(v + max_val * 0.02, bar.get_y() + bar.get_height() / 2,
                        f'{v:.2f}', va='center', fontsize=7,
                        color='#999', fontfamily='monospace')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out = output_path or '/tmp/keyword_chart.png'
    plt.savefig(out, dpi=180, bbox_inches='tight', facecolor='#0f0f0f')
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
