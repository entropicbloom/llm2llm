// UI helper functions

import { state } from './state.js';
import { shortModel, metricColor, metricTextColor, renderMarkdown } from './utils.js';

/** Toggle collapsed state for conversation lists */
export function toggleConvs(id) {
    const convs = document.getElementById('convs-' + id);
    const toggle = document.getElementById('toggle-' + id);
    const count = toggle.dataset.count;
    if (convs.classList.contains('collapsed')) {
        convs.classList.remove('collapsed');
        toggle.textContent = 'Hide';
    } else {
        convs.classList.add('collapsed');
        toggle.textContent = `Show ${count} convs`;
    }
}

/** Check if we should use mobile mode (full-screen overlay) */
function isMobileMode() {
    return window.innerWidth <= 1024;
}

/** Open conversation in detail panel */
export async function openConversation(convId, scrollToTurn = null) {
    const conv = DATA.conversations.find(c => c.id === convId);
    const analysis = DATA.analyses.find(a => a.conversation_id === convId);

    if (!conv) return;

    // Update state
    state.selectedConversationId = convId;

    // Update card selection
    updateSelectedCard(convId);

    // Determine target container
    const panel = document.getElementById('detail-panel');
    const body = document.getElementById('panel-body');
    const appBody = document.getElementById('app-body');

    // Show panel with loading state
    panel.classList.add('visible');
    appBody.classList.add('panel-open');
    document.getElementById('app').classList.add('panel-open');
    body.innerHTML = '<div style="padding: 40px; text-align: center;">Loading transcript...</div>';

    // Fetch transcript from conversations folder
    let transcript = [];
    try {
        const response = await fetch(`/conversations/${convId}.json`);
        if (response.ok) {
            const data = await response.json();
            transcript = data.messages || [];
        }
    } catch (e) {
        console.warn('Could not load transcript:', e);
    }

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

    if (scrollToTurn) {
        setTimeout(() => {
            const turnEl = document.getElementById(`turn-${scrollToTurn}`);
            if (turnEl) {
                turnEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 100);
    }
}

/** Close detail panel */
export function closePanel() {
    const panel = document.getElementById('detail-panel');
    const appBody = document.getElementById('app-body');

    panel.classList.remove('visible');
    appBody.classList.remove('panel-open');
    document.getElementById('app').classList.remove('panel-open');

    // Clear selection
    state.selectedConversationId = null;
    updateSelectedCard(null);
}

/** Update selected card highlighting */
function updateSelectedCard(selectedId) {
    // Remove existing selection
    document.querySelectorAll('.card.selected').forEach(card => {
        card.classList.remove('selected');
    });

    // Add selection to new card
    if (selectedId) {
        const cards = document.querySelectorAll('.card');
        cards.forEach(card => {
            if (card.getAttribute('onclick')?.includes(selectedId)) {
                card.classList.add('selected');
            }
        });
    }
}


/** Scroll to insight section */
export function scrollToInsightSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}
