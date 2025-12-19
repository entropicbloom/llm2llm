// Insights view

import { scrollToInsightSection } from '../ui.js';

export function renderInsights(container) {
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

    html += `
            </div>
        </div>
    `;

    container.innerHTML = html;
}
