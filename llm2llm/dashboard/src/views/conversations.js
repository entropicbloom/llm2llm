// Conversations view

import { state } from '../state.js';
import { getFilteredAnalyses } from '../data.js';
import { shortModel, truncateText } from '../utils.js';

/** Toggle conversation preview (accordion-style) */
export function togglePreview(convId, event) {
    event.stopPropagation();
    state.expandedConvId = state.expandedConvId === convId ? null : convId;
    renderConversationList();
}

/** Generate preview HTML for a conversation */
function renderPreview(convId) {
    const preview = DATA.previews?.[convId] || [];
    if (preview.length < 2) return '';

    const conv = DATA.conversations.find(c => c.id === convId);
    const totalTurns = conv?.turn_count || preview.length;

    const maxChars = 200;
    // Preview contains first 2 + last 2 messages (4 total, or less for short convs)
    const firstTwo = preview.slice(0, 2);
    const lastTwo = preview.length >= 4 ? preview.slice(-2) : [];
    const skipped = Math.max(0, totalTurns - 4);

    const renderSnippet = (msg, fromEnd = false) => {
        const role = msg.participant_role || 'unknown';
        const roleClass = role === 'initiator' ? 'initiator' : 'responder';
        const text = truncateText(msg.content, maxChars, fromEnd);
        return `<div class="preview-msg ${roleClass}">${text}</div>`;
    };

    const separatorText = skipped > 0 ? `${skipped} messages later` : '···';

    return `
        <div class="conv-preview">
            <div class="preview-section">
                ${firstTwo.map(m => renderSnippet(m, false)).join('')}
            </div>
            <div class="preview-separator">${separatorText}</div>
            <div class="preview-section">
                ${lastTwo.map(m => renderSnippet(m, true)).join('')}
            </div>
        </div>
    `;
}

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
        const isExpanded = state.expandedConvId === conv.id;
        const hasPreview = DATA.previews?.[conv.id]?.length >= 2;

        html += `
            <div class="card" onclick="openConversation('${conv.id}')">
                <div class="card-title">${conv.title || 'Untitled'}</div>
                <div class="card-meta">
                    <span class="model-name">${shortModel(conv.llm1_model)}</span>
                    <span>+</span>
                    <span class="model-name">${shortModel(conv.llm2_model)}</span>
                    <span>${conv.turn_count} turns</span>
                </div>
                <div class="card-tags">
                    ${topTopics.map(([t]) => `<span class="tag">${t}</span>`).join('')}
                    ${analysis?.trajectory ? `<span class="tag trajectory">${analysis.trajectory}</span>` : ''}
                </div>
                ${hasPreview ? `
                    <div class="preview-area${isExpanded ? ' expanded' : ''}" onclick="togglePreview('${conv.id}', event)">
                        <div class="preview-toggle">
                            <span class="preview-toggle-text">${isExpanded ? 'hide preview' : 'show preview'}</span>
                            <span class="preview-toggle-icon">${isExpanded ? '▲' : '▼'}</span>
                        </div>
                        ${isExpanded ? renderPreview(conv.id) : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

    listContainer.innerHTML = html;
}
