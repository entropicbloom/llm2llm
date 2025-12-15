let currentView = 'conversations';
let searchTerm = '';
let filterModel = '';
let rankingAttribute = 'depth';
let modelSortAttribute = 'count';
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

function openConversation(convId, scrollToTurn = null) {
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
        const roleLabel = role === 'initiator' ? shortModel(conv.llm1_model) : shortModel(conv.llm2_model);
        const isHighlighted = scrollToTurn && msg.turn_number >= scrollToTurn && msg.turn_number < scrollToTurn + 5;
        html += `
            <div class="message ${roleClass}${isHighlighted ? ' highlighted' : ''}" id="turn-${msg.turn_number}" data-turn="${msg.turn_number}">
                <div class="message-header">Turn ${msg.turn_number} - ${roleLabel}</div>
                <div class="message-content">${renderMarkdown(msg.content)}</div>
            </div>
        `;
    }

    html += '</div>';
    body.innerHTML = html;
    modal.classList.remove('hidden');

    // Scroll to the specific turn if provided
    if (scrollToTurn) {
        setTimeout(() => {
            const turnEl = document.getElementById(`turn-${scrollToTurn}`);
            if (turnEl) {
                turnEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 100);
    }
}

function render() {
    const main = document.getElementById('main-content');

    if (currentView === 'conversations') {
        renderConversations(main);
    } else if (currentView === 'models') {
        renderModels(main);
    } else if (currentView === 'pairs') {
        renderPairs(main);
    } else if (currentView === 'insights') {
        renderInsights(main);
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

    // Compute averages for all models
    for (const [model, stats] of Object.entries(modelStats)) {
        stats.depth = avg(stats.depths);
        stats.warmth = avg(stats.warmths);
        stats.energy = avg(stats.energies);
        stats.spirituality = avg(stats.spiritualities);
    }

    // Sort models by selected attribute
    const getSortValue = (stats) => {
        if (modelSortAttribute === 'count') return stats.count;
        return stats[modelSortAttribute] || 0;
    };

    const sortedModels = Object.entries(modelStats)
        .sort((a, b) => getSortValue(b[1]) - getSortValue(a[1]));

    let html = `
        <div class="ranking-controls">
            <label>Sort by:</label>
            <select id="model-sort-select">
                <option value="count" ${modelSortAttribute === 'count' ? 'selected' : ''}>Conversations</option>
                <option value="depth" ${modelSortAttribute === 'depth' ? 'selected' : ''}>Depth</option>
                <option value="warmth" ${modelSortAttribute === 'warmth' ? 'selected' : ''}>Warmth</option>
                <option value="energy" ${modelSortAttribute === 'energy' ? 'selected' : ''}>Energy</option>
                <option value="spirituality" ${modelSortAttribute === 'spirituality' ? 'selected' : ''}>Spirituality</option>
            </select>
            <span style="color: var(--text-muted); font-size: 12px;">${sortedModels.length} models</span>
        </div>
    `;

    for (const [model, stats] of sortedModels) {
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
                    <div class="stat-card" style="background: ${metricColor('depth', stats.depth)};">
                        <div class="stat-value" style="color: ${metricTextColor('depth', stats.depth)};">${stats.depth.toFixed(1)}</div>
                        <div class="stat-label">Depth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('warmth', stats.warmth)};">
                        <div class="stat-value" style="color: ${metricTextColor('warmth', stats.warmth)};">${stats.warmth.toFixed(1)}</div>
                        <div class="stat-label">Warmth</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('energy', stats.energy)};">
                        <div class="stat-value" style="color: ${metricTextColor('energy', stats.energy)};">${stats.energy.toFixed(1)}</div>
                        <div class="stat-label">Energy</div>
                    </div>
                    <div class="stat-card" style="background: ${metricColor('spirituality', stats.spirituality)};">
                        <div class="stat-value" style="color: ${metricTextColor('spirituality', stats.spirituality)};">${stats.spirituality.toFixed(1)}</div>
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

    // Setup sort selector handler
    document.getElementById('model-sort-select').addEventListener('change', (e) => {
        modelSortAttribute = e.target.value;
        render();
    });
}

function renderPairs(container) {
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

    // Build pairs with stats from filtered analyses
    const pairsMap = {};
    for (const a of analyses) {
        const key = `${a.llm1_model}|${a.llm2_model}`;
        if (!pairsMap[key]) {
            pairsMap[key] = {
                llm1: a.llm1_model,
                llm2: a.llm2_model,
                conversations: [],
                convIds: new Set(),
                depths: [],
                warmths: [],
                energies: [],
                spiritualities: [],
                topicScores: {},
                trajectoryCounts: {}
            };
        }
        const p = pairsMap[key];

        // Deduplicate conversations
        if (!p.convIds.has(a.conversation_id)) {
            p.convIds.add(a.conversation_id);
            p.conversations.push({
                id: a.conversation_id,
                title: a.title || 'Untitled',
                turn_count: a.turn_count || 0
            });
        }

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
    for (const p of Object.values(pairsMap)) {
        p.depth = avg(p.depths);
        p.warmth = avg(p.warmths);
        p.energy = avg(p.energies);
        p.spirituality = avg(p.spiritualities);
        p.count = p.conversations.length;
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
            return (pair.trajectoryCounts[trajectory] || 0) / Math.max(pair.count, 1);
        }
        return 0;
    };

    // Sort by selected attribute
    const sorted = Object.values(pairsMap)
        .filter(p => p.count > 0)
        .map(p => ({ ...p, sortValue: getValue(p) }))
        .sort((a, b) => b.sortValue - a.sortValue);

    // Find max value for scaling bars
    const maxVal = Math.max(...sorted.map(p => p.sortValue), 0.01);

    // Determine display label
    const getLabel = () => {
        if (['depth', 'warmth', 'energy', 'spirituality'].includes(rankingAttribute)) {
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
            <label>Sort by:</label>
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
            <span style="color: var(--text-muted); font-size: 12px;">${sorted.length} pairs</span>
        </div>
        <div class="ranking-list">
    `;

    sorted.forEach((pair, idx) => {
        const position = idx + 1;
        const positionClass = position === 1 ? 'gold' : position === 2 ? 'silver' : position === 3 ? 'bronze' : '';
        const barWidth = (pair.sortValue / maxVal) * 100;
        const displayValue = isPercentage ? Math.round(pair.sortValue * 100) + '%' : pair.sortValue.toFixed(1);
        const pairId = `pair-${idx}`;

        html += `
            <div class="ranking-item" style="flex-wrap: wrap;">
                <div class="ranking-position ${positionClass}">#${position}</div>
                <div class="ranking-info">
                    <div class="ranking-pair">
                        ${shortModel(pair.llm1)} <span style="color: var(--text-muted)">+</span> ${shortModel(pair.llm2)}
                    </div>
                    <div class="ranking-meta">
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
                <div style="width: 100%; margin-top: 12px; padding-left: 56px;">
                    <span class="toggle-btn" id="toggle-${pairId}" data-count="${pair.count}" onclick="togglePairConvs('${pairId}')" style="cursor: pointer;">Show ${pair.count} convs</span>
                    <div class="partner-convs collapsed" id="convs-${pairId}" style="margin-top: 8px;">
                        ${pair.conversations.map(c => `
                            <div class="mini-card" onclick="event.stopPropagation(); openConversation('${c.id}')">
                                ${c.title}
                                <span style="color: var(--text-muted); margin-left: 8px;">${c.turn_count} turns</span>
                            </div>
                        `).join('')}
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

function renderInsights(container) {
    const insights = INSIGHTS_DATA;

    // Group dynamics by type
    const dynamicTypes = ['Compassion', 'Co-Discovery', 'World-Building', 'Asymmetry', 'Mirroring', 'Tension'];
    const typeLabels = {
        'Compassion': 'Compassion & Care',
        'Co-Discovery': 'Co-Discovery',
        'World-Building': 'World-Building',
        'Asymmetry': 'Asymmetric Dynamics',
        'Mirroring': 'Mirroring & Convergence',
        'Tension': 'Tension & Resolution'
    };

    // Build sidebar items
    const sidebarItems = [];
    dynamicTypes.forEach(type => {
        const items = insights.dynamics.filter(d => d.type === type);
        if (items.length > 0) {
            sidebarItems.push({ id: `section-${type.toLowerCase()}`, label: typeLabels[type] || type, count: items.length });
        }
    });
    if (insights.patterns && insights.patterns.length > 0) {
        sidebarItems.push({ id: 'section-patterns', label: 'Cross-Cutting Patterns', count: insights.patterns.length });
    }
    if (insights.modelDifferences && insights.modelDifferences.length > 0) {
        sidebarItems.push({ id: 'section-model-diff', label: 'Model Differences', count: insights.modelDifferences.length });
    }

    let html = `
        <div class="insights-layout">
            <aside class="insights-sidebar">
                <nav class="insights-nav">
                    ${sidebarItems.map(item => `
                        <a href="#${item.id}" class="insights-nav-item" onclick="scrollToInsightSection('${item.id}')">
                            <span>${item.label}</span>
                            <span class="insights-nav-count">${item.count}</span>
                        </a>
                    `).join('')}
                </nav>
            </aside>
            <div class="insights-content">
                <div class="insights-intro">
                    <h2>Relational Dynamics</h2>
                    <p class="insights-subtitle">How LLMs relate to each other: compassion, co-discovery, world-building, and more</p>
                    ${insights.note ? `<p class="insights-disclaimer">${insights.note}</p>` : ''}
                </div>
    `;

    dynamicTypes.forEach(type => {
        const items = insights.dynamics.filter(d => d.type === type);
        if (items.length === 0) return;

        html += `
            <div class="insight-section" id="section-${type.toLowerCase()}">
                <h3 class="insight-section-title">${typeLabels[type] || type}</h3>
                ${items.map(d => `
                    <div class="insight-card dynamic dynamic-${type.toLowerCase()}">
                        <div class="insight-card-title">${d.title}</div>
                        <div class="insight-card-description">${d.description}</div>
                        <div class="excerpt-container">
                            ${d.excerpt.map(turn => `
                                <div class="excerpt-turn">
                                    <span class="excerpt-speaker">${turn.speaker}:</span>
                                    <span class="excerpt-text">${turn.text}</span>
                                </div>
                            `).join('')}
                            ${d.conversationId ? `
                                <a href="#" class="excerpt-link" onclick="event.preventDefault(); openConversation('${d.conversationId}', ${d.turnStart || 1})">
                                    View in context &rarr;
                                </a>
                            ` : ''}
                        </div>
                        <div class="insight-analysis">${d.analysis}</div>
                    </div>
                `).join('')}
            </div>
        `;
    });

    // Patterns section
    if (insights.patterns && insights.patterns.length > 0) {
        html += `
            <div class="insight-section" id="section-patterns">
                <h3 class="insight-section-title">Cross-Cutting Patterns</h3>
                <div class="patterns-grid">
                    ${insights.patterns.map(p => `
                        <div class="pattern-card">
                            <div class="pattern-title">${p.title}</div>
                            <div class="pattern-description">${p.description}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Model differences section
    if (insights.modelDifferences && insights.modelDifferences.length > 0) {
        html += `
            <div class="insight-section" id="section-model-diff">
                <h3 class="insight-section-title">Model Personality Differences</h3>
                <div class="model-diff-grid">
                    ${insights.modelDifferences.map(m => `
                        <div class="model-diff-card">
                            <div class="model-diff-name">${m.model}</div>
                            <ul class="model-diff-traits">
                                ${m.traits.map(t => `<li>${t}</li>`).join('')}
                            </ul>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Close the layout divs
    html += `
            </div>
        </div>
    `;

    container.innerHTML = html;
}

function scrollToInsightSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
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

function renderMarkdown(text) {
    if (!text) return '';
    // Configure marked for safe rendering
    marked.setOptions({
        breaks: true,  // Convert \n to <br>
        gfm: true,     // GitHub Flavored Markdown
    });
    return marked.parse(text);
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

function togglePairConvs(pairId) {
    const convs = document.getElementById('convs-' + pairId);
    const toggle = document.getElementById('toggle-' + pairId);
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
