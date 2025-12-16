// Conversations view

import { state } from '../state.js';
import { getFilteredAnalyses } from '../data.js';
import { shortModel } from '../utils.js';
import { openConversation } from '../ui.js';

export function renderConversations(container) {
    // Only create controls once
    if (!document.getElementById('search-input')) {
        container.innerHTML = `
            <div class="filters">
                <input type="text" placeholder="Search titles..." id="search-input" value="${state.searchTerm}">
                <select id="model-filter">
                    <option value="">All models</option>
                    ${DATA.models.map(m => `<option value="${m}" ${state.filterModel === m ? 'selected' : ''}>${shortModel(m)}</option>`).join('')}
                </select>
            </div>
            <div id="conversation-list"></div>
        `;

        document.getElementById('search-input').addEventListener('input', (e) => {
            state.searchTerm = e.target.value;
            renderConversationList();
        });
        document.getElementById('model-filter').addEventListener('change', (e) => {
            state.filterModel = e.target.value;
            renderConversationList();
        });
    }

    renderConversationList();
}

function renderConversationList() {
    const listContainer = document.getElementById('conversation-list');
    if (!listContainer) return;

    const analyses = getFilteredAnalyses();
    const analysisMap = new Map(analyses.map(a => [a.conversation_id, a]));
    let convs = DATA.conversations.filter(c => analysisMap.has(c.id));

    // Apply filters
    if (state.searchTerm) {
        const term = state.searchTerm.toLowerCase();
        convs = convs.filter(c => (c.title || '').toLowerCase().includes(term));
    }
    if (state.filterModel) {
        convs = convs.filter(c => c.llm1_model === state.filterModel || c.llm2_model === state.filterModel);
    }

    let html = '';
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

    listContainer.innerHTML = html;
}
