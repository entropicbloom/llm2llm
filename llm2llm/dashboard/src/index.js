// Dashboard entry point

import { state } from './state.js';
import { openConversation, closePanel, toggleConvs, scrollToInsightSection } from './ui.js';
import { buildSegmentOptions } from './segment.js';
import { renderConversations, togglePreview } from './views/conversations.js';
import { renderModels } from './views/models.js';
import { renderPairs } from './views/pairs.js';
import { renderMaps } from './views/maps.js';
import { renderInsights } from './views/insights.js';

// Expose functions to global scope for onclick handlers
window.openConversation = openConversation;
window.closePanel = closePanel;
window.toggleConvs = toggleConvs;
window.scrollToInsightSection = scrollToInsightSection;
window.togglePreview = togglePreview;

function init() {
    buildSegmentOptions(); // set default segment
    setupNavigation();
    setupPanel();
    setupThemeToggle();
    document.addEventListener('segment-change', () => render());
    render();
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

function setupPanel() {
    const panel = document.getElementById('detail-panel');
    panel.querySelector('.panel-close').addEventListener('click', closePanel);

    // ESC key closes panel
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closePanel();
        }
    });
}

function setupThemeToggle() {
    const toggle = document.getElementById('theme-toggle');
    const root = document.documentElement;

    // Check saved preference (default is light)
    const saved = localStorage.getItem('theme');
    if (saved === 'dark') {
        root.removeAttribute('data-theme');
        toggle.textContent = '◐';
    }

    toggle.addEventListener('click', () => {
        const isLight = root.getAttribute('data-theme') === 'light';
        if (isLight) {
            root.removeAttribute('data-theme');
            toggle.textContent = '◐';
            localStorage.setItem('theme', 'dark');
        } else {
            root.setAttribute('data-theme', 'light');
            toggle.textContent = '◑';
            localStorage.setItem('theme', 'light');
        }
        // Re-render to update metric colors
        render();
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
    } else if (state.currentView === 'maps') {
        if (!document.getElementById('map-container')) main.innerHTML = '';
        renderMaps(main);
    } else if (state.currentView === 'insights') {
        main.innerHTML = '';
        renderInsights(main);
    }
}

// Initialize when DOM is ready
init();
