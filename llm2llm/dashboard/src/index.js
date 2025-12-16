// Dashboard entry point

import { state } from './state.js';
import { openConversation, closeModal, toggleConvs, scrollToInsightSection } from './ui.js';
import { renderConversations } from './views/conversations.js';
import { renderModels } from './views/models.js';
import { renderPairs } from './views/pairs.js';
import { renderInsights } from './views/insights.js';

// Expose functions to global scope for onclick handlers
window.openConversation = openConversation;
window.closeModal = closeModal;
window.toggleConvs = toggleConvs;
window.scrollToInsightSection = scrollToInsightSection;

function init() {
    setupNavigation();
    setupModal();
    setupSegmentSelector();
    render();
}

function setupSegmentSelector() {
    const select = document.getElementById('segment-select');

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

    for (const [value, label] of segments) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        select.appendChild(option);
    }

    if (segments.size > 1) {
        const firstSegment = Array.from(segments.keys())[1];
        select.value = firstSegment;
        state.selectedSegment = firstSegment;
    }

    select.addEventListener('change', (e) => {
        state.selectedSegment = e.target.value;
        render();
    });
}

function setupNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentView = btn.dataset.view;
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

function render() {
    const main = document.getElementById('main-content');

    // Clear container when switching views to ensure fresh render
    if (state.currentView === 'conversations') {
        if (!document.getElementById('search-input')) main.innerHTML = '';
        renderConversations(main);
    } else if (state.currentView === 'models') {
        if (!document.getElementById('model-sort-select')) main.innerHTML = '';
        renderModels(main);
    } else if (state.currentView === 'pairs') {
        main.innerHTML = '';
        renderPairs(main);
    } else if (state.currentView === 'insights') {
        main.innerHTML = '';
        renderInsights(main);
    }
}

// Initialize when DOM is ready
init();
