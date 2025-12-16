// Pairs view

import { state } from '../state.js';
import { getFilteredAnalyses } from '../data.js';
import { shortModel, avg, metricColor, metricTextColor } from '../utils.js';

export function renderPairs(container) {
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
        if (['depth', 'warmth', 'energy', 'spirituality'].includes(state.rankingAttribute)) {
            return pair[state.rankingAttribute];
        } else if (state.rankingAttribute.startsWith('topic:')) {
            const topic = state.rankingAttribute.slice(6);
            return avg(pair.topicScores[topic] || []);
        } else if (state.rankingAttribute.startsWith('trajectory:')) {
            const trajectory = state.rankingAttribute.slice(11);
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
        if (['depth', 'warmth', 'energy', 'spirituality'].includes(state.rankingAttribute)) {
            return state.rankingAttribute;
        } else if (state.rankingAttribute.startsWith('topic:')) {
            return state.rankingAttribute.slice(6);
        } else if (state.rankingAttribute.startsWith('trajectory:')) {
            return state.rankingAttribute.slice(11);
        }
        return state.rankingAttribute;
    };

    const isPercentage = state.rankingAttribute.startsWith('topic:') || state.rankingAttribute.startsWith('trajectory:');

    let html = `
        <div class="ranking-controls">
            <label>Sort by:</label>
            <select id="ranking-select">
                <optgroup label="Metrics">
                    <option value="depth" ${state.rankingAttribute === 'depth' ? 'selected' : ''}>Depth</option>
                    <option value="warmth" ${state.rankingAttribute === 'warmth' ? 'selected' : ''}>Warmth</option>
                    <option value="energy" ${state.rankingAttribute === 'energy' ? 'selected' : ''}>Energy</option>
                    <option value="spirituality" ${state.rankingAttribute === 'spirituality' ? 'selected' : ''}>Spirituality</option>
                </optgroup>
                <optgroup label="Topics">
                    ${topicList.map(t => `<option value="topic:${t}" ${state.rankingAttribute === 'topic:' + t ? 'selected' : ''}>${t}</option>`).join('')}
                </optgroup>
                <optgroup label="Trajectory">
                    ${trajectoryList.map(t => `<option value="trajectory:${t}" ${state.rankingAttribute === 'trajectory:' + t ? 'selected' : ''}>${t}</option>`).join('')}
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
                    <span class="toggle-btn" id="toggle-${pairId}" data-count="${pair.count}" onclick="toggleConvs('${pairId}')" style="cursor: pointer;">Show ${pair.count} convs</span>
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
        state.rankingAttribute = e.target.value;
        renderPairs(container);
    });
}
