"""Generate a static HTML dashboard from conversation data."""

import json
from pathlib import Path
from datetime import datetime

from llm2llm.config import Config
from llm2llm.conversation import ConversationStorage
from llm2llm.dashboard.data import load_all_analyses, infer_provider


def generate_dashboard_data(config: Config, storage: ConversationStorage) -> dict:
    """Gather all data needed for the dashboard."""
    analyses = load_all_analyses(config.database_path)

    # Get all conversations with titles
    conversations = storage.list_conversations(limit=1000)

    # Add titles to conversations
    conv_map = {c["id"]: c for c in conversations}
    for c in conversations:
        c["title"] = storage.get_title(c["id"])
        c["provider1"] = infer_provider(c["llm1_model"])
        c["provider2"] = infer_provider(c["llm2_model"])

    # Enrich analyses with titles
    for a in analyses:
        conv = conv_map.get(a["conversation_id"], {})
        a["title"] = conv.get("title", "Untitled")

    # Get unique models and pairs
    models = set()
    pairs = {}
    for a in analyses:
        models.add(a["llm1_model"])
        models.add(a["llm2_model"])
        pair_key = f"{a['llm1_model']}|{a['llm2_model']}"
        if pair_key not in pairs:
            pairs[pair_key] = {
                "llm1": a["llm1_model"],
                "llm2": a["llm2_model"],
                "conversations": [],
            }
        pairs[pair_key]["conversations"].append({
            "id": a["conversation_id"],
            "title": a.get("title", "Untitled"),
            "turn_count": a.get("turn_count", 0),
            "topics": a.get("topics", {}),
            "trajectory": a.get("trajectory", "unknown"),
            "warmth": a.get("warmth", 0),
            "energy": a.get("energy", 0),
            "depth": a.get("depth", 0),
        })

    return {
        "generated_at": datetime.now().isoformat(),
        "total_conversations": len(conversations),
        "total_analyses": len(analyses),
        "models": sorted(models),
        "pairs": list(pairs.values()),
        "conversations": conversations,
        "analyses": analyses,
    }


def load_conversation_content(conversations_dir: Path, conversation_id: str) -> list[dict]:
    """Load full conversation messages from JSON file."""
    json_path = conversations_dir / f"{conversation_id}.json"
    if not json_path.exists():
        return []
    with open(json_path) as f:
        data = json.load(f)
    return data.get("messages", [])


def generate_html(config: Config, storage: ConversationStorage, include_transcripts: bool = True) -> str:
    """Generate the complete HTML dashboard."""
    data = generate_dashboard_data(config, storage)

    # Optionally load full transcripts
    if include_transcripts:
        transcripts = {}
        for conv in data["conversations"]:
            messages = load_conversation_content(config.conversations_dir, conv["id"])
            transcripts[conv["id"]] = messages
        data["transcripts"] = transcripts

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM2LLM Dashboard</title>
    <style>
{CSS}
    </style>
</head>
<body>
    <div id="app">
        <header>
            <h1>LLM2LLM</h1>
            <p class="subtitle">{data["total_conversations"]} conversations analyzed</p>
        </header>
        <nav>
            <button class="nav-btn active" data-view="conversations">Conversations</button>
            <button class="nav-btn" data-view="models">Models</button>
            <button class="nav-btn" data-view="pairs">Pairs</button>
            <button class="nav-btn" data-view="rankings">Rankings</button>
            <div class="segment-selector">
                <label>Segment:</label>
                <select id="segment-select"></select>
            </div>
        </nav>
        <main id="main-content">
            <!-- Content injected by JS -->
        </main>
    </div>
    <div id="modal" class="modal hidden">
        <div class="modal-content">
            <button class="modal-close">&times;</button>
            <div id="modal-body"></div>
        </div>
    </div>
    <script>
const DATA = {json.dumps(data, default=str)};
{JS}
    </script>
</body>
</html>'''
    return html


CSS = '''
:root {
    --bg: #ffffff;
    --bg-secondary: #fafafa;
    --bg-tertiary: #f0f0f0;
    --text: #1a1a1a;
    --text-muted: #666666;
    --border: #e0e0e0;
    --accent: #0066cc;
    --accent-muted: #0066cc15;
    --green: #22863a;
    --orange: #b08800;
    --red: #cb2431;
    --purple: #6f42c1;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
}

#app {
    max-width: 1200px;
    margin: 0 auto;
    padding: 24px;
}

header {
    margin-bottom: 24px;
}

header h1 {
    font-size: 24px;
    font-weight: 600;
}

.subtitle {
    color: var(--text-muted);
    font-size: 14px;
}

nav {
    display: flex;
    gap: 8px;
    margin-bottom: 24px;
    border-bottom: 1px solid var(--border);
    padding-bottom: 12px;
}

.nav-btn {
    background: none;
    border: none;
    color: var(--text-muted);
    padding: 8px 16px;
    cursor: pointer;
    font-size: 14px;
    border-radius: 6px;
    transition: all 0.15s;
}

.nav-btn:hover {
    color: var(--text);
    background: var(--bg-tertiary);
}

.nav-btn.active {
    color: var(--text);
    background: var(--bg-secondary);
}

.segment-selector {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: 8px;
}

.segment-selector label {
    font-size: 12px;
    color: var(--text-muted);
}

.segment-selector select {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 6px 10px;
    border-radius: 6px;
    font-size: 12px;
}

.card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: border-color 0.15s;
}

.card:hover {
    border-color: var(--accent);
}

.card-title {
    font-weight: 600;
    margin-bottom: 4px;
}

.card-meta {
    font-size: 12px;
    color: var(--text-muted);
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
}

.tag {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    background: var(--bg-tertiary);
    color: var(--text-muted);
    margin-right: 4px;
    margin-top: 8px;
}

.tag.trajectory {
    background: var(--accent-muted);
    color: var(--accent);
}

.model-name {
    font-family: monospace;
    font-size: 12px;
}

.filters {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
    flex-wrap: wrap;
}

.filters input, .filters select {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
}

.filters input:focus, .filters select:focus {
    outline: none;
    border-color: var(--accent);
}

/* Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0,0,0,0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal.hidden {
    display: none;
}

.modal-content {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 12px;
    width: 90%;
    max-width: 800px;
    max-height: 90vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.modal-close {
    position: absolute;
    top: 16px;
    right: 16px;
    background: none;
    border: none;
    color: var(--text-muted);
    font-size: 24px;
    cursor: pointer;
    z-index: 10;
}

.modal-close:hover {
    color: var(--text);
}

#modal-body {
    padding: 24px;
    overflow-y: auto;
}

.transcript {
    margin-top: 16px;
}

.message {
    padding: 12px;
    margin-bottom: 8px;
    border-radius: 8px;
    background: var(--bg-tertiary);
}

.message.initiator {
    border-left: 3px solid var(--green);
}

.message.responder {
    border-left: 3px solid var(--accent);
}

.message-header {
    font-size: 12px;
    color: var(--text-muted);
    margin-bottom: 8px;
}

.message-content {
    white-space: pre-wrap;
    font-size: 14px;
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
}

.stat-card {
    background: var(--bg-tertiary);
    padding: 12px;
    border-radius: 6px;
    text-align: center;
}

.stat-value {
    font-size: 24px;
    font-weight: 600;
}

.stat-label {
    font-size: 12px;
    color: var(--text-muted);
}

.mood-bar {
    height: 6px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    margin: 4px 0;
    position: relative;
}

.mood-bar-fill {
    position: absolute;
    height: 100%;
    border-radius: 3px;
    background: var(--accent);
}

.mood-label {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: var(--text-muted);
}

.pair-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

.pair-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
}

.pair-models {
    font-family: monospace;
    font-size: 13px;
}

.pair-count {
    color: var(--text-muted);
    font-size: 12px;
}

.pair-conversations {
    display: grid;
    gap: 8px;
}

.mini-card {
    background: var(--bg-tertiary);
    padding: 10px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
    font-size: 13px;
}

.mini-card:hover {
    background: var(--border);
}

.partners-section {
    border-top: 1px solid var(--border);
    padding-top: 12px;
    margin-top: 12px;
}

.partner-group {
    margin-bottom: 12px;
}

.partner-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
}

.partner-convs {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.partner-convs.collapsed {
    display: none;
}

.toggle-btn {
    color: var(--accent);
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--accent-muted);
    transition: background 0.15s;
}

.toggle-btn:hover {
    background: var(--bg-tertiary);
}

.partner-stats {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
    flex-wrap: wrap;
}

.partner-stat {
    font-size: 11px;
    color: var(--text-muted);
    font-family: monospace;
}

/* Rankings */
.ranking-controls {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    align-items: center;
    flex-wrap: wrap;
}

.ranking-controls label {
    font-size: 14px;
    color: var(--text-muted);
}

.ranking-controls select {
    background: var(--bg-tertiary);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
}

.ranking-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.ranking-item {
    display: flex;
    align-items: center;
    gap: 16px;
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    transition: border-color 0.15s;
}

.ranking-item:hover {
    border-color: var(--accent);
}

.ranking-position {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-muted);
    min-width: 40px;
    text-align: center;
}

.ranking-position.gold { color: #d4a017; }
.ranking-position.silver { color: #8b8b8b; }
.ranking-position.bronze { color: #cd7f32; }

.ranking-info {
    flex: 1;
}

.ranking-pair {
    font-family: monospace;
    font-size: 14px;
    margin-bottom: 4px;
}

.ranking-meta {
    font-size: 12px;
    color: var(--text-muted);
}

.ranking-score {
    text-align: right;
}

.ranking-value {
    font-size: 28px;
    font-weight: 600;
    color: var(--accent);
}

.ranking-label {
    font-size: 11px;
    color: var(--text-muted);
    text-transform: uppercase;
}

.ranking-bar {
    width: 120px;
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
    margin-top: 4px;
}

.ranking-bar-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    transition: width 0.3s;
}

.metric-badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-family: monospace;
    font-weight: 500;
    margin-right: 6px;
}
'''

JS = '''
let currentView = 'conversations';
let searchTerm = '';
let filterModel = '';
let rankingAttribute = 'depth';
let selectedSegment = 'all';

function init() {
    setupNavigation();
    setupModal();
    setupSegmentSelector();
    render();
}

function setupSegmentSelector() {
    const select = document.getElementById('segment-select');

    // Find unique segments
    const segments = new Map();
    segments.set('all', 'All segments');

    for (const a of DATA.analyses) {
        const key = `${a.segment_start}:${a.segment_end === null ? '' : a.segment_end}`;
        if (!segments.has(key)) {
            const label = a.segment_end === null
                ? `[${a.segment_start}:] (last ${Math.abs(a.segment_start)})`
                : `[${a.segment_start}:${a.segment_end}]`;
            segments.set(key, label);
        }
    }

    // Populate dropdown
    for (const [value, label] of segments) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }

    // Set default to first non-all segment if available
    if (segments.size > 1) {
        const firstSegment = Array.from(segments.keys())[1];
        select.value = firstSegment;
        selectedSegment = firstSegment;
    }

    select.addEventListener('change', (e) => {
        selectedSegment = e.target.value;
        render();
    });
}

function getFilteredAnalyses() {
    if (selectedSegment === 'all') {
        // Deduplicate by conversation_id, taking first analysis per conversation
        const seen = new Set();
        return DATA.analyses.filter(a => {
            if (seen.has(a.conversation_id)) return false;
            seen.add(a.conversation_id);
            return true;
        });
    }

    const [start, end] = selectedSegment.split(':');
    const segStart = parseInt(start);
    const segEnd = end === '' ? null : parseInt(end);

    return DATA.analyses.filter(a =>
        a.segment_start === segStart &&
        a.segment_end === segEnd
    );
}

function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentView = btn.dataset.view;
            render();
        });
    });
}

function setupModal() {
    const modal = document.getElementById('modal');
    modal.querySelector('.modal-close').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
}

function closeModal() {
    document.getElementById('modal').classList.add('hidden');
}

function openConversation(convId) {
    const modal = document.getElementById('modal');
    const body = document.getElementById('modal-body');

    const conv = DATA.conversations.find(c => c.id === convId);
    const analysis = DATA.analyses.find(a => a.conversation_id === convId);
    const transcript = DATA.transcripts?.[convId] || [];

    if (!conv) return;

    let html = `
        <h2>${conv.title || 'Untitled'}</h2>
        <div class="card-meta" style="margin: 8px 0 16px;">
            <span class="model-name">${shortModel(conv.llm1_model)}</span>
            <span>+</span>
            <span class="model-name">${shortModel(conv.llm2_model)}</span>
            <span>${conv.turn_count} turns</span>
        </div>
    `;

    if (analysis) {
        const d = analysis.depth || 0;
        const w = analysis.warmth || 0;
        const e = analysis.energy || 0;
        const s = analysis.spirituality || 0;
        html += `
            <div class="stats-grid">
                <div class="stat-card" style="background: ${metricColor('depth', d)};">
                    <div class="stat-value" style="color: ${metricTextColor('depth', d)};">${d.toFixed(1)}</div>
                    <div class="stat-label">Depth</div>
                </div>
                <div class="stat-card" style="background: ${metricColor('warmth', w)};">
                    <div class="stat-value" style="color: ${metricTextColor('warmth', w)};">${w.toFixed(1)}</div>
                    <div class="stat-label">Warmth</div>
                </div>
                <div class="stat-card" style="background: ${metricColor('energy', e)};">
                    <div class="stat-value" style="color: ${metricTextColor('energy', e)};">${e.toFixed(1)}</div>
                    <div class="stat-label">Energy</div>
                </div>
                <div class="stat-card" style="background: ${metricColor('spirituality', s)};">
                    <div class="stat-value" style="color: ${metricTextColor('spirituality', s)};">${s.toFixed(1)}</div>
                    <div class="stat-label">Spirituality</div>
                </div>
            </div>
            <div style="margin-bottom: 16px;">
                ${Object.entries(analysis.topics || {}).slice(0, 5).map(([t, s]) =>
                    `<span class="tag">${t} ${Math.round(s*100)}%</span>`
                ).join('')}
                <span class="tag trajectory">${analysis.trajectory || 'unknown'}</span>
            </div>
        `;
    }

    html += `<h3 style="margin-bottom: 12px;">Transcript</h3><div class="transcript">`;

    for (const msg of transcript) {
        const role = msg.participant_role || 'unknown';
        const roleClass = role === 'initiator' ? 'initiator' : 'responder';
        const roleLabel = role === 'initiator' ? 'LLM1' : 'LLM2';
        html += `
            <div class="message ${roleClass}">
                <div class="message-header">Turn ${msg.turn_number} - ${roleLabel}</div>
                <div class="message-content">${escapeHtml(msg.content)}</div>
            </div>
        `;
    }

    html += '</div>';
    body.innerHTML = html;
    modal.classList.remove('hidden');
}

function render() {
    const main = document.getElementById('main-content');

    if (currentView === 'conversations') {
        renderConversations(main);
    } else if (currentView === 'models') {
        renderModels(main);
    } else if (currentView === 'pairs') {
        renderPairs(main);
    } else if (currentView === 'rankings') {
        renderRankings(main);
    }
}

function renderConversations(container) {
    const analyses = getFilteredAnalyses();

    let html = `
        <div class="filters">
            <input type="text" placeholder="Search titles..." id="search-input" value="${searchTerm}">
            <select id="model-filter">
                <option value="">All models</option>
                ${DATA.models.map(m => `<option value="${m}" ${filterModel === m ? 'selected' : ''}>${shortModel(m)}</option>`).join('')}
            </select>
        </div>
        <div id="conversation-list">
    `;

    // Get conversations that have analysis in selected segment
    const analysisMap = new Map(analyses.map(a => [a.conversation_id, a]));
    let convs = DATA.conversations.filter(c => analysisMap.has(c.id));

    // Apply filters
    if (searchTerm) {
        const term = searchTerm.toLowerCase();
        convs = convs.filter(c => (c.title || '').toLowerCase().includes(term));
    }
    if (filterModel) {
        convs = convs.filter(c => c.llm1_model === filterModel || c.llm2_model === filterModel);
    }

    for (const conv of convs) {
        const analysis = analysisMap.get(conv.id);
        const topics = analysis?.topics || {};
        const topTopics = Object.entries(topics).sort((a,b) => b[1] - a[1]).slice(0, 3);

        html += `
            <div class="card" onclick="openConversation('${conv.id}')">
                <div class="card-title">${conv.title || 'Untitled'}</div>
                <div class="card-meta">
                    <span class="model-name">${shortModel(conv.llm1_model)}</span>
                    <span>+</span>
                    <span class="model-name">${shortModel(conv.llm2_model)}</span>
                    <span>${conv.turn_count} turns</span>
                </div>
                <div>
                    ${topTopics.map(([t]) => `<span class="tag">${t}</span>`).join('')}
                    ${analysis?.trajectory ? `<span class="tag trajectory">${analysis.trajectory}</span>` : ''}
                </div>
            </div>
        `;
    }

    html += '</div>';
    container.innerHTML = html;

    // Setup filter handlers
    document.getElementById('search-input').addEventListener('input', (e) => {
        searchTerm = e.target.value;
        render();
    });
    document.getElementById('model-filter').addEventListener('change', (e) => {
        filterModel = e.target.value;
        render();
    });
}

function renderModels(container) {
    const analyses = getFilteredAnalyses();
    const modelStats = {};

    for (const a of analyses) {
        // Get unique models in this conversation (handles self-talk)
        const models = a.llm1_model === a.llm2_model
            ? [a.llm1_model]
            : [a.llm1_model, a.llm2_model];

        for (const model of models) {
            if (!modelStats[model]) {
                modelStats[model] = { count: 0, depths: [], warmths: [], energies: [], spiritualities: [], topics: {}, partners: {} };
            }
            modelStats[model].count++;
            if (a.depth !== undefined) modelStats[model].depths.push(a.depth);
            if (a.warmth !== undefined) modelStats[model].warmths.push(a.warmth);
            if (a.energy !== undefined) modelStats[model].energies.push(a.energy);
            if (a.spirituality !== undefined) modelStats[model].spiritualities.push(a.spirituality);
            for (const [topic, score] of Object.entries(a.topics || {})) {
                if (!modelStats[model].topics[topic]) modelStats[model].topics[topic] = [];
                modelStats[model].topics[topic].push(score);
            }

            // Track partners and conversations
            const partner = model === a.llm1_model ? a.llm2_model : a.llm1_model;
            if (!modelStats[model].partners[partner]) {
                modelStats[model].partners[partner] = { convs: [], convIds: new Set(), topics: {}, depths: [], warmths: [], energies: [], spiritualities: [] };
            }
            // Deduplicate conversations (same conv may have multiple analysis segments)
            if (!modelStats[model].partners[partner].convIds.has(a.conversation_id)) {
                modelStats[model].partners[partner].convIds.add(a.conversation_id);
                modelStats[model].partners[partner].convs.push({
                    id: a.conversation_id,
                    title: a.title || 'Untitled'
                });
            }
            if (a.depth !== undefined) modelStats[model].partners[partner].depths.push(a.depth);
            if (a.warmth !== undefined) modelStats[model].partners[partner].warmths.push(a.warmth);
            if (a.energy !== undefined) modelStats[model].partners[partner].energies.push(a.energy);
            if (a.spirituality !== undefined) modelStats[model].partners[partner].spiritualities.push(a.spirituality);
            for (const [topic, score] of Object.entries(a.topics || {})) {
                if (!modelStats[model].partners[partner].topics[topic]) {
                    modelStats[model].partners[partner].topics[topic] = [];
                }
                modelStats[model].partners[partner].topics[topic].push(score);
            }
        }
    }

    let html = '';

    for (const [model, stats] of Object.entries(modelStats).sort((a,b) => b[1].count - a[1].count)) {
        const avgDepth = avg(stats.depths);
        const avgWarmth = avg(stats.warmths);
        const avgEnergy = avg(stats.energies);
        const avgSpirituality = avg(stats.spiritualities);

        const topTopics = Object.entries(stats.topics)
            .map(([t, scores]) => [t, avg(scores)])
            .sort((a,b) => b[1] - a[1])
            .slice(0, 5);

        const partnersList = Object.entries(stats.partners)
            .sort((a,b) => b[1].convs.length - a[1].convs.length);

        html += `
            <div class="card" style="cursor: default;">
                <div class="card-title model-name">${shortModel(model)}</div>
                <div class="card-meta" style="margin-bottom: 12px;">
                    <span>${stats.count} conversations</span>
                </div>
                <div class="stats-grid">
                    <div class="stat-card" style="background: ${metricColor('depth', avgDepth)};">
                        <div class="stat-value" style="color: ${metricTextColor('depth', avgDepth)};">${avgDepth.toFixed(1)}</div>
                        <div class="stat-label">Depth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('warmth', avgWarmth)};">
                        <div class="stat-value" style="color: ${metricTextColor('warmth', avgWarmth)};">${avgWarmth.toFixed(1)}</div>
                        <div class="stat-label">Warmth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('energy', avgEnergy)};">
                        <div class="stat-value" style="color: ${metricTextColor('energy', avgEnergy)};">${avgEnergy.toFixed(1)}</div>
                        <div class="stat-label">Energy</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('spirituality', avgSpirituality)};">
                        <div class="stat-value" style="color: ${metricTextColor('spirituality', avgSpirituality)};">${avgSpirituality.toFixed(1)}</div>
                        <div class="stat-label">Spirituality</div>
                    </div>
                </div>
                <div style="margin-bottom: 12px;">
                    ${topTopics.map(([t, s]) => `<span class="tag">${t} ${Math.round(s*100)}%</span>`).join('')}
                </div>
                <div class="partners-section">
                    <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Partners</div>
                    ${partnersList.map(([partner, pStats]) => {
                        const pTopics = Object.entries(pStats.topics)
                            .map(([t, scores]) => [t, avg(scores)])
                            .sort((a,b) => b[1] - a[1])
                            .slice(0, 3);
                        const pDepth = avg(pStats.depths);
                        const pWarmth = avg(pStats.warmths);
                        const pEnergy = avg(pStats.energies);
                        const pSpirituality = avg(pStats.spiritualities);
                        const partnerId = `${model}-${partner}`.replace(/[^a-zA-Z0-9]/g, '_');
                        return `
                            <div class="partner-group">
                                <div class="partner-header" onclick="togglePartnerConvs('${partnerId}')" style="cursor: pointer;">
                                    <div>
                                        <span class="model-name">${shortModel(partner)}</span>
                                    </div>
                                    <span class="toggle-btn" id="toggle-${partnerId}" data-count="${pStats.convs.length}">Show ${pStats.convs.length} convs</span>
                                </div>
                                <div class="partner-stats">
                                    <span class="metric-badge" style="background: ${metricColor('depth', pDepth)}; color: ${metricTextColor('depth', pDepth)};">D ${pDepth.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor('warmth', pWarmth)}; color: ${metricTextColor('warmth', pWarmth)};">W ${pWarmth.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor('energy', pEnergy)}; color: ${metricTextColor('energy', pEnergy)};">E ${pEnergy.toFixed(1)}</span>
                                    <span class="metric-badge" style="background: ${metricColor('spirituality', pSpirituality)}; color: ${metricTextColor('spirituality', pSpirituality)};">S ${pSpirituality.toFixed(1)}</span>
                                    ${pTopics.map(([t]) => `<span class="tag">${t}</span>`).join('')}
                                </div>
                                <div class="partner-convs collapsed" id="convs-${partnerId}">
                                    ${pStats.convs.map(c => `
                                        <div class="mini-card" onclick="event.stopPropagation(); openConversation('${c.id}')">${c.title}</div>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderPairs(container) {
    const analyses = getFilteredAnalyses();

    // Build pairs from filtered analyses
    const pairsMap = {};
    for (const a of analyses) {
        const key = `${a.llm1_model}|${a.llm2_model}`;
        if (!pairsMap[key]) {
            pairsMap[key] = { llm1: a.llm1_model, llm2: a.llm2_model, conversations: [] };
        }
        pairsMap[key].conversations.push({
            id: a.conversation_id,
            title: a.title || 'Untitled',
            turn_count: a.turn_count || 0
        });
    }
    const pairs = Object.values(pairsMap);

    let html = '';

    for (const pair of pairs.sort((a,b) => b.conversations.length - a.conversations.length)) {
        html += `
            <div class="pair-card">
                <div class="pair-header">
                    <div class="pair-models">
                        ${shortModel(pair.llm1)} <span style="color: var(--text-muted)">+</span> ${shortModel(pair.llm2)}
                    </div>
                    <div class="pair-count">${pair.conversations.length} conversations</div>
                </div>
                <div class="pair-conversations">
                    ${pair.conversations.map(c => `
                        <div class="mini-card" onclick="openConversation('${c.id}')">
                            ${c.title || 'Untitled'}
                            <span style="color: var(--text-muted); margin-left: 8px;">${c.turn_count} turns</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = html;
}

function renderRankings(container) {
    const analyses = getFilteredAnalyses();

    // Collect all unique topics and trajectories
    const allTopics = new Set();
    const allTrajectories = new Set();

    for (const a of analyses) {
        if (a.topics) {
            Object.keys(a.topics).forEach(t => allTopics.add(t));
        }
        if (a.trajectory) {
            allTrajectories.add(a.trajectory);
        }
    }

    const topicList = Array.from(allTopics).sort();
    const trajectoryList = Array.from(allTrajectories).sort();

    // Compute stats for each pair
    const pairStats = {};

    for (const a of analyses) {
        const key = `${a.llm1_model}|${a.llm2_model}`;
        if (!pairStats[key]) {
            pairStats[key] = {
                llm1: a.llm1_model,
                llm2: a.llm2_model,
                count: 0,
                depths: [],
                warmths: [],
                energies: [],
                spiritualities: [],
                topicScores: {},
                trajectoryCounts: {}
            };
        }
        const p = pairStats[key];
        p.count++;
        if (a.depth !== undefined) p.depths.push(a.depth);
        if (a.warmth !== undefined) p.warmths.push(a.warmth);
        if (a.energy !== undefined) p.energies.push(a.energy);
        if (a.spirituality !== undefined) p.spiritualities.push(a.spirituality);
        if (a.topics) {
            for (const [topic, score] of Object.entries(a.topics)) {
                if (!p.topicScores[topic]) p.topicScores[topic] = [];
                p.topicScores[topic].push(score);
            }
        }
        if (a.trajectory) {
            p.trajectoryCounts[a.trajectory] = (p.trajectoryCounts[a.trajectory] || 0) + 1;
        }
    }

    // Compute averages
    for (const p of Object.values(pairStats)) {
        p.depth = avg(p.depths);
        p.warmth = avg(p.warmths);
        p.energy = avg(p.energies);
        p.spirituality = avg(p.spiritualities);
    }

    // Determine sort value based on attribute type
    const getValue = (pair) => {
        if (['depth', 'warmth', 'energy', 'spirituality'].includes(rankingAttribute)) {
            return pair[rankingAttribute];
        } else if (rankingAttribute.startsWith('topic:')) {
            const topic = rankingAttribute.slice(6);
            return avg(pair.topicScores[topic] || []);
        } else if (rankingAttribute.startsWith('trajectory:')) {
            const trajectory = rankingAttribute.slice(11);
            return (pair.trajectoryCounts[trajectory] || 0) / pair.count;
        }
        return 0;
    };

    // Sort by selected attribute
    const sorted = Object.values(pairStats)
        .filter(p => p.count > 0)
        .map(p => ({ ...p, sortValue: getValue(p) }))
        .sort((a, b) => b.sortValue - a.sortValue);

    // Find max value for scaling bars
    const maxVal = Math.max(...sorted.map(p => p.sortValue), 0.01);

    // Determine display label
    const getLabel = () => {
        if (['depth', 'warmth', 'energy'].includes(rankingAttribute)) {
            return rankingAttribute;
        } else if (rankingAttribute.startsWith('topic:')) {
            return rankingAttribute.slice(6);
        } else if (rankingAttribute.startsWith('trajectory:')) {
            return rankingAttribute.slice(11);
        }
        return rankingAttribute;
    };

    const isPercentage = rankingAttribute.startsWith('topic:') || rankingAttribute.startsWith('trajectory:');

    let html = `
        <div class="ranking-controls">
            <label>Rank by:</label>
            <select id="ranking-select">
                <optgroup label="Metrics">
                    <option value="depth" ${rankingAttribute === 'depth' ? 'selected' : ''}>Depth</option>
                    <option value="warmth" ${rankingAttribute === 'warmth' ? 'selected' : ''}>Warmth</option>
                    <option value="energy" ${rankingAttribute === 'energy' ? 'selected' : ''}>Energy</option>
                    <option value="spirituality" ${rankingAttribute === 'spirituality' ? 'selected' : ''}>Spirituality</option>
                </optgroup>
                <optgroup label="Topics">
                    ${topicList.map(t => `<option value="topic:${t}" ${rankingAttribute === 'topic:' + t ? 'selected' : ''}>${t}</option>`).join('')}
                </optgroup>
                <optgroup label="Trajectory">
                    ${trajectoryList.map(t => `<option value="trajectory:${t}" ${rankingAttribute === 'trajectory:' + t ? 'selected' : ''}>${t}</option>`).join('')}
                </optgroup>
            </select>
            <span style="color: var(--text-muted); font-size: 12px;">${sorted.length} model pairs</span>
        </div>
        <div class="ranking-list">
    `;

    sorted.forEach((pair, idx) => {
        const position = idx + 1;
        const positionClass = position === 1 ? 'gold' : position === 2 ? 'silver' : position === 3 ? 'bronze' : '';
        const barWidth = (pair.sortValue / maxVal) * 100;
        const displayValue = isPercentage ? Math.round(pair.sortValue * 100) + '%' : pair.sortValue.toFixed(1);

        html += `
            <div class="ranking-item">
                <div class="ranking-position ${positionClass}">#${position}</div>
                <div class="ranking-info">
                    <div class="ranking-pair">
                        ${shortModel(pair.llm1)} <span style="color: var(--text-muted)">+</span> ${shortModel(pair.llm2)}
                    </div>
                    <div class="ranking-meta">
                        <span style="margin-right: 8px;">${pair.count} conv${pair.count !== 1 ? 's' : ''}</span>
                        <span class="metric-badge" style="background: ${metricColor('depth', pair.depth)}; color: ${metricTextColor('depth', pair.depth)};">D ${pair.depth.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor('warmth', pair.warmth)}; color: ${metricTextColor('warmth', pair.warmth)};">W ${pair.warmth.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor('energy', pair.energy)}; color: ${metricTextColor('energy', pair.energy)};">E ${pair.energy.toFixed(1)}</span>
                        <span class="metric-badge" style="background: ${metricColor('spirituality', pair.spirituality)}; color: ${metricTextColor('spirituality', pair.spirituality)};">S ${pair.spirituality.toFixed(1)}</span>
                    </div>
                </div>
                <div class="ranking-score">
                    <div class="ranking-value">${displayValue}</div>
                    <div class="ranking-label">${getLabel()}</div>
                    <div class="ranking-bar">
                        <div class="ranking-bar-fill" style="width: ${barWidth}%"></div>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;

    // Setup attribute selector handler
    document.getElementById('ranking-select').addEventListener('change', (e) => {
        rankingAttribute = e.target.value;
        render();
    });
}

function shortModel(model) {
    // Shorten model names for display
    return model
        .replace('claude-', '')
        .replace('mistralai/', '')
        .replace('-20250514', '')
        .replace('-20250929', '')
        .replace('-20251001', '')
        .replace('-20251101', '')
        .replace('-20240229', '')
        .replace('-20241022', '')
        .replace('-20240307', '')
        .replace('-20250219', '')
        .replace('-20250805', '');
}

function avg(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function metricColor(type, value, maxValue = 10) {
    // Harmonious pastel palette with saturation varying by value
    // Depth: blue (220°), Warmth: coral (15°), Energy: teal (165°), Spirituality: purple (280°)
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;

    // Normalize value to 0-1 range (assuming max ~10)
    const normalized = Math.min(value / maxValue, 1);

    // Saturation: 8% (low values) to 45% (high values) - subtle range
    const saturation = 8 + (normalized * 37);

    // Lightness: 95% (low) to 88% (high) - stays pastel but gets richer
    const lightness = 95 - (normalized * 7);

    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function metricTextColor(type, value, maxValue = 10) {
    // Darker text color that matches the metric hue
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;
    const normalized = Math.min(value / maxValue, 1);

    // More saturated and darker for text
    const saturation = 30 + (normalized * 30);
    const lightness = 45 - (normalized * 15);

    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function togglePartnerConvs(partnerId) {
    const convs = document.getElementById('convs-' + partnerId);
    const toggle = document.getElementById('toggle-' + partnerId);
    const count = toggle.dataset.count;
    if (convs.classList.contains('collapsed')) {
        convs.classList.remove('collapsed');
        toggle.textContent = 'Hide';
    } else {
        convs.classList.add('collapsed');
        toggle.textContent = `Show ${count} convs`;
    }
}

init();
'''


def write_dashboard(output_path: Path, config: Config, storage: ConversationStorage) -> None:
    """Generate and write the dashboard HTML file."""
    html = generate_html(config, storage)
    output_path.write_text(html)
