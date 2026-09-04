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
    setupPanelResizer();
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

/** Draggable divider between the list and the detail panel (desktop only). */
function setupPanelResizer() {
    const resizer = document.getElementById('panel-resizer');
    const appBody = document.getElementById('app-body');
    if (!resizer || !appBody) return;

    const MIN_PANEL = 360;
    const MIN_MAIN = 420;
    const root = document.documentElement;
    const KEY = 'llm2llm.panelWidth';

    const applyWidth = (px) => root.style.setProperty('--panel-width', `${Math.round(px)}px`);

    try {
        const saved = parseInt(localStorage.getItem(KEY), 10);
        if (saved > 0) applyWidth(saved);
    } catch (e) { /* storage unavailable */ }

    let dragging = false;

    const onMove = (e) => {
        if (!dragging) return;
        const rect = appBody.getBoundingClientRect();
        const maxPanel = Math.max(MIN_PANEL, rect.width - MIN_MAIN - resizer.offsetWidth);
        const width = Math.min(maxPanel, Math.max(MIN_PANEL, rect.right - e.clientX));
        applyWidth(width);
    };

    const onUp = () => {
        if (!dragging) return;
        dragging = false;
        document.body.classList.remove('resizing');
        window.removeEventListener('pointermove', onMove);
        window.removeEventListener('pointerup', onUp);
        try {
            const current = parseInt(root.style.getPropertyValue('--panel-width'), 10);
            if (current > 0) localStorage.setItem(KEY, String(current));
        } catch (e) { /* storage unavailable */ }
    };

    resizer.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        dragging = true;
        document.body.classList.add('resizing');
        window.addEventListener('pointermove', onMove);
        window.addEventListener('pointerup', onUp);
    });

    resizer.addEventListener('dblclick', () => {
        root.style.removeProperty('--panel-width');
        try { localStorage.removeItem(KEY); } catch (e) { /* storage unavailable */ }
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
