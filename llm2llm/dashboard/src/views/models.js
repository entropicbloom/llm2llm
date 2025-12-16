// Models view

import { state } from '../state.js';
import { getFilteredAnalyses, createEmptyStats, addAnalysisToStats, computeAverages } from '../data.js';
import { shortModel, avg, metricColor, metricTextColor } from '../utils.js';

export function renderModels(container) {
    // Only create controls once
    if (!document.getElementById('model-sort-select')) {
        container.innerHTML = `
            <div class="ranking-controls">
                <label>Sort by:</label>
                <select id="model-sort-select">
                    <option value="count">Conversations</option>
                    <option value="depth">Depth</option>
                    <option value="warmth">Warmth</option>
                    <option value="energy">Energy</option>
                    <option value="spirituality">Spirituality</option>
                </select>
                <span id="model-count" style="color: var(--text-muted); font-size: 12px;"></span>
            </div>
            <div id="model-list"></div>
        `;

        document.getElementById('model-sort-select').addEventListener('change', (e) => {
            state.modelSortAttribute = e.target.value;
            renderModelList();
        });
    }

    renderModelList();
}

function renderModelList() {
    const listContainer = document.getElementById('model-list');
    const countSpan = document.getElementById('model-count');
    if (!listContainer) return;

    const analyses = getFilteredAnalyses();
    const modelStats = {};

    for (const a of analyses) {
        const models = a.llm1_model === a.llm2_model ? [a.llm1_model] : [a.llm1_model, a.llm2_model];

        for (const model of models) {
            if (!modelStats[model]) {
                modelStats[model] = { ...createEmptyStats(), partners: {} };
            }
            modelStats[model].count++;
            addAnalysisToStats(modelStats[model], a);

            // Track partners
            const partner = model === a.llm1_model ? a.llm2_model : a.llm1_model;
            if (!modelStats[model].partners[partner]) {
                modelStats[model].partners[partner] = { ...createEmptyStats(), convs: [], convIds: new Set() };
            }
            const pStats = modelStats[model].partners[partner];
            if (!pStats.convIds.has(a.conversation_id)) {
                pStats.convIds.add(a.conversation_id);
                pStats.convs.push({ id: a.conversation_id, title: a.title || 'Untitled' });
            }
            addAnalysisToStats(pStats, a);
        }
    }

    // Compute averages
    for (const stats of Object.values(modelStats)) {
        computeAverages(stats);
    }

    // Sort
    const getSortValue = (stats) => state.modelSortAttribute === 'count' ? stats.count : (stats[state.modelSortAttribute] || 0);
    const sortedModels = Object.entries(modelStats).sort((a, b) => getSortValue(b[1]) - getSortValue(a[1]));

    countSpan.textContent = `${sortedModels.length} models`;

    let html = '';

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
                                <div class="partner-header" onclick="toggleConvs('${partnerId}')" style="cursor: pointer;">
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

    listContainer.innerHTML = html;
}
