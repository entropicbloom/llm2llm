// Maps view - 2D scatter plots of conversations

import { state } from '../state.js';
import { getFilteredAnalyses } from '../data.js';
import { shortModel, avg, metricColor, metricTextColor } from '../utils.js';

// Color palettes by provider
const PROVIDER_COLORS = {
    anthropic: ['#8B6914', '#A67C00', '#C9A227', '#D4AF37', '#E6C55B', '#F0D77B'], // bronze/gold
    mistral: ['#CC5500', '#E86A17', '#FF7F2A', '#FF944D', '#FFAA70', '#FFBF94'],   // orange
    openai: ['#10A37F', '#1DBF8E', '#3DD9A5', '#5EEDB8', '#7FFFD4', '#A0FFE0'],    // teal/green
    google: ['#1E40AF', '#2563EB', '#3B82F6', '#60A5FA', '#93C5FD', '#BFDBFE'],    // blue (gemini)
    default: ['#6B7280', '#9CA3AF', '#D1D5DB', '#E5E7EB', '#F3F4F6', '#F9FAFB'],   // gray
};

function getProvider(model) {
    if (model.startsWith('claude-')) return 'anthropic';
    if (model.startsWith('mistralai/')) return 'mistral';
    if (model.startsWith('gpt-')) return 'openai';
    if (model.startsWith('google/')) return 'google';
    return 'default';
}

function showPairModal(pair, modelColorMap) {
    const modal = document.getElementById('modal');
    const modalBody = document.getElementById('modal-body');

    // Calculate average metrics from the pair's conversation data
    const analyses = getFilteredAnalyses().filter(a =>
        a.llm1_model === pair.llm1_model && a.llm2_model === pair.llm2_model
    );

    const depth = avg(analyses.map(a => a.depth ?? 0));
    const warmth = avg(analyses.map(a => a.warmth ?? 0));
    const energy = avg(analyses.map(a => a.energy ?? 0));
    const spirituality = avg(analyses.map(a => a.spirituality ?? 0));

    const color1 = modelColorMap[pair.llm1_model];
    const color2 = modelColorMap[pair.llm2_model];

    modalBody.innerHTML = `
        <div style="margin-bottom: 20px;">
            <h2 style="font-size: 18px; margin-bottom: 8px;">
                <span style="color: ${color1}">${shortModel(pair.llm1_model)}</span>
                <span style="color: var(--text-muted); margin: 0 8px;">+</span>
                <span style="color: ${color2}">${shortModel(pair.llm2_model)}</span>
            </h2>
            <div style="color: var(--text-muted); font-size: 13px;">
                ${pair.conversations.length} conversation${pair.conversations.length > 1 ? 's' : ''}
            </div>
        </div>

        <div class="stats-grid" style="margin-bottom: 20px;">
            <div class="stat-card" style="background: ${metricColor('depth', depth)};">
                <div class="stat-value" style="color: ${metricTextColor('depth', depth)};">${depth.toFixed(2)}</div>
                <div class="stat-label">Depth</div>
            </div>
            <div class="stat-card" style="background: ${metricColor('warmth', warmth)};">
                <div class="stat-value" style="color: ${metricTextColor('warmth', warmth)};">${warmth.toFixed(2)}</div>
                <div class="stat-label">Warmth</div>
            </div>
            <div class="stat-card" style="background: ${metricColor('energy', energy)};">
                <div class="stat-value" style="color: ${metricTextColor('energy', energy)};">${energy.toFixed(2)}</div>
                <div class="stat-label">Energy</div>
            </div>
            <div class="stat-card" style="background: ${metricColor('spirituality', spirituality)};">
                <div class="stat-value" style="color: ${metricTextColor('spirituality', spirituality)};">${spirituality.toFixed(2)}</div>
                <div class="stat-label">Spirituality</div>
            </div>
        </div>

        <div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 8px;">Conversations</div>
            ${pair.conversations.map(c => `
                <div class="mini-card" onclick="openConversation('${c.id}')" style="margin-bottom: 6px;">
                    ${c.title || 'Untitled'}
                </div>
            `).join('')}
        </div>
    `;

    modal.classList.remove('hidden');
}

export function renderMaps(container) {
    // Build controls and canvas once
    if (!document.getElementById('map-container')) {
        container.innerHTML = `
            <div class="map-controls">
                <div class="axis-selectors">
                    <label>X axis:</label>
                    <select id="x-axis-select">
                        <option value="depth">Depth</option>
                        <option value="warmth">Warmth</option>
                        <option value="energy">Energy</option>
                        <option value="spirituality">Spirituality</option>
                    </select>
                    <label>Y axis:</label>
                    <select id="y-axis-select">
                        <option value="warmth">Warmth</option>
                        <option value="depth">Depth</option>
                        <option value="energy">Energy</option>
                        <option value="spirituality">Spirituality</option>
                    </select>
                </div>
                <div class="model-selector">
                    <label>Highlight model:</label>
                    <select id="highlight-model-select">
                        <option value="">All models</option>
                    </select>
                </div>
            </div>
            <div id="map-container">
                <svg id="scatter-plot"></svg>
                <div id="map-tooltip" class="map-tooltip hidden"></div>
            </div>
            <div id="map-legend" class="map-legend"></div>
        `;

        // Populate model selector
        const modelSelect = document.getElementById('highlight-model-select');
        const models = new Set();
        for (const a of DATA.analyses) {
            models.add(a.llm1_model);
            models.add(a.llm2_model);
        }
        for (const model of [...models].sort()) {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = shortModel(model);
            modelSelect.appendChild(option);
        }

        // Set initial state
        state.mapXAxis = 'depth';
        state.mapYAxis = 'warmth';
        state.mapHighlightModel = '';

        // Add event listeners
        document.getElementById('x-axis-select').addEventListener('change', (e) => {
            state.mapXAxis = e.target.value;
            renderScatterPlot();
        });
        document.getElementById('y-axis-select').addEventListener('change', (e) => {
            state.mapYAxis = e.target.value;
            renderScatterPlot();
        });
        document.getElementById('highlight-model-select').addEventListener('change', (e) => {
            state.mapHighlightModel = e.target.value;
            renderScatterPlot();
        });
    }

    renderScatterPlot();
}

function renderScatterPlot() {
    const svg = document.getElementById('scatter-plot');
    const container = document.getElementById('map-container');
    const tooltip = document.getElementById('map-tooltip');
    const legend = document.getElementById('map-legend');
    if (!svg || !container) return;

    const analyses = getFilteredAnalyses();
    const xAxis = state.mapXAxis || 'depth';
    const yAxis = state.mapYAxis || 'warmth';
    const highlightModel = state.mapHighlightModel || '';

    // Dimensions
    const width = container.clientWidth || 800;
    const height = 500;
    const margin = { top: 20, right: 20, bottom: 50, left: 50 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;

    svg.setAttribute('width', width);
    svg.setAttribute('height', height);

    // Build model color map from ALL analyses (not filtered) for consistent colors
    const allModels = new Set();
    for (const a of DATA.analyses) {
        allModels.add(a.llm1_model);
        allModels.add(a.llm2_model);
    }
    const modelList = [...allModels].sort();

    // Group models by provider and assign colors within each group
    const modelColorMap = {};
    const providerCounts = {};
    modelList.forEach(model => {
        const provider = getProvider(model);
        const colors = PROVIDER_COLORS[provider] || PROVIDER_COLORS.default;
        const idx = providerCounts[provider] || 0;
        modelColorMap[model] = colors[idx % colors.length];
        providerCounts[provider] = idx + 1;
    });

    // Aggregate by model pair first
    const pairMap = {};
    for (const a of analyses) {
        const pairKey = `${a.llm1_model}|${a.llm2_model}`;
        if (!pairMap[pairKey]) {
            pairMap[pairKey] = {
                llm1_model: a.llm1_model,
                llm2_model: a.llm2_model,
                conversations: [],
                xValues: [],
                yValues: [],
            };
        }
        pairMap[pairKey].conversations.push({ id: a.conversation_id, title: a.title });
        pairMap[pairKey].xValues.push(a[xAxis] ?? 0);
        pairMap[pairKey].yValues.push(a[yAxis] ?? 0);
    }

    // Calculate pair averages first
    const pairAverages = Object.values(pairMap).map(pair => ({
        pair,
        avgX: pair.xValues.reduce((a, b) => a + b, 0) / pair.xValues.length,
        avgY: pair.yValues.reduce((a, b) => a + b, 0) / pair.yValues.length,
    }));

    // Find data range from pair averages
    const xValues = pairAverages.map(p => p.avgX);
    const yValues = pairAverages.map(p => p.avgY);

    const dataXMin = Math.min(...xValues);
    const dataXMax = Math.max(...xValues);
    const dataYMin = Math.min(...yValues);
    const dataYMax = Math.max(...yValues);

    const xPadding = (dataXMax - dataXMin) * 0.15 || 0.1;
    const yPadding = (dataYMax - dataYMin) * 0.15 || 0.1;

    const xMin = dataXMin - xPadding;
    const xMax = dataXMax + xPadding;
    const yMin = dataYMin - yPadding;
    const yMax = dataYMax + yPadding;

    // Scale functions
    const scaleX = (v) => margin.left + ((v - xMin) / (xMax - xMin)) * plotWidth;
    const scaleY = (v) => margin.top + plotHeight - ((v - yMin) / (yMax - yMin)) * plotHeight;

    // Build SVG content
    let svgContent = '';

    // Axes
    svgContent += `<line x1="${margin.left}" y1="${margin.top + plotHeight}" x2="${margin.left + plotWidth}" y2="${margin.top + plotHeight}" stroke="var(--border)" />`;
    svgContent += `<line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${margin.top + plotHeight}" stroke="var(--border)" />`;

    // Axis labels
    svgContent += `<text x="${margin.left + plotWidth / 2}" y="${height - 10}" text-anchor="middle" fill="var(--text-muted)" font-size="12">${xAxis.charAt(0).toUpperCase() + xAxis.slice(1)}</text>`;
    svgContent += `<text x="15" y="${margin.top + plotHeight / 2}" text-anchor="middle" fill="var(--text-muted)" font-size="12" transform="rotate(-90, 15, ${margin.top + plotHeight / 2})">${yAxis.charAt(0).toUpperCase() + yAxis.slice(1)}</text>`;

    // Grid lines
    const nTicks = 5;
    const xStep = (xMax - xMin) / nTicks;
    const yStep = (yMax - yMin) / nTicks;

    for (let i = 0; i <= nTicks; i++) {
        const xVal = xMin + i * xStep;
        const yVal = yMin + i * yStep;
        const x = scaleX(xVal);
        const y = scaleY(yVal);
        svgContent += `<line x1="${x}" y1="${margin.top}" x2="${x}" y2="${margin.top + plotHeight}" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.5" />`;
        svgContent += `<line x1="${margin.left}" y1="${y}" x2="${margin.left + plotWidth}" y2="${y}" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.5" />`;
        svgContent += `<text x="${x}" y="${margin.top + plotHeight + 15}" text-anchor="middle" fill="var(--text-muted)" font-size="10">${xVal.toFixed(2)}</text>`;
        svgContent += `<text x="${margin.left - 8}" y="${y + 4}" text-anchor="end" fill="var(--text-muted)" font-size="10">${yVal.toFixed(2)}</text>`;
    }

    // Build points with positions
    const points = [];
    for (const { pair, avgX, avgY } of pairAverages) {
        const cx = scaleX(avgX);
        const cy = scaleY(avgY);

        const color1 = modelColorMap[pair.llm1_model];
        const color2 = modelColorMap[pair.llm2_model];

        // Determine opacity based on highlight
        let opacity = 0.9;
        let radius = 6 + Math.min(pair.conversations.length, 10); // Size by conversation count
        if (highlightModel) {
            if (pair.llm1_model === highlightModel || pair.llm2_model === highlightModel) {
                opacity = 1;
                radius += 2;
            } else {
                opacity = 0.15;
                radius = Math.max(radius - 2, 4);
            }
        }

        points.push({
            pair,
            avgX, avgY,
            cx, cy,
            color1, color2,
            opacity, radius
        });
    }

    // Sort so highlighted points are on top
    points.sort((a, b) => a.opacity - b.opacity);

    for (const pt of points) {
        const pair = pt.pair;
        const pairId = `${pair.llm1_model}-${pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, '_');
        // Use a split circle to show both models
        if (pair.llm1_model === pair.llm2_model) {
            // Same model - solid circle
            svgContent += `<circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}"
                data-pair="${pairId}" class="map-point" style="cursor: pointer;" />`;
        } else {
            // Different models - split circle using clip paths
            svgContent += `
                <defs>
                    <clipPath id="left-${pairId}">
                        <rect x="${pt.cx - pt.radius}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                    <clipPath id="right-${pairId}">
                        <rect x="${pt.cx}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                </defs>
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}" clip-path="url(#left-${pairId})"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color2}" opacity="${pt.opacity}" clip-path="url(#right-${pairId})"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="none" stroke="var(--border)" stroke-width="0.5" opacity="${pt.opacity}"
                    data-pair="${pairId}" class="map-point" style="cursor: pointer;" />
            `;
        }
    }

    svg.innerHTML = svgContent;

    // Add event listeners for tooltips and clicks
    svg.querySelectorAll('.map-point').forEach(point => {
        point.addEventListener('mouseenter', (e) => {
            const pairId = e.target.dataset.pair;
            const pt = points.find(p => `${p.pair.llm1_model}-${p.pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, '_') === pairId);
            if (pt) {
                const pair = pt.pair;
                tooltip.innerHTML = `
                    <div class="tooltip-models" style="margin-bottom: 8px;">
                        <span style="color: ${pt.color1}; font-weight: 600;">${shortModel(pair.llm1_model)}</span>
                        <span>↔</span>
                        <span style="color: ${pt.color2}; font-weight: 600;">${shortModel(pair.llm2_model)}</span>
                    </div>
                    <div class="tooltip-metrics" style="margin-bottom: 8px;">
                        ${xAxis}: ${pt.avgX.toFixed(2)} | ${yAxis}: ${pt.avgY.toFixed(2)}
                    </div>
                    <div style="font-size: 11px; color: var(--text-muted);">
                        ${pair.conversations.length} conversation${pair.conversations.length > 1 ? 's' : ''}
                    </div>
                `;
                tooltip.classList.remove('hidden');
                const rect = container.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 10) + 'px';
                tooltip.style.top = (e.clientY - rect.top - 10) + 'px';
            }
        });
        point.addEventListener('mouseleave', () => {
            tooltip.classList.add('hidden');
        });
        point.addEventListener('click', (e) => {
            const pairId = e.target.dataset.pair;
            const pt = points.find(p => `${p.pair.llm1_model}-${p.pair.llm2_model}`.replace(/[^a-zA-Z0-9]/g, '_') === pairId);
            if (pt) {
                showPairModal(pt.pair, modelColorMap);
            }
        });
    });

    // Render legend
    let legendHtml = '<div class="legend-title">Models</div><div class="legend-items">';
    for (const model of modelList) {
        const isHighlighted = !highlightModel || model === highlightModel;
        legendHtml += `
            <div class="legend-item ${isHighlighted ? '' : 'dimmed'}" data-model="${model}" style="cursor: pointer;">
                <span class="legend-color" style="background: ${modelColorMap[model]}"></span>
                <span class="legend-label">${shortModel(model)}</span>
            </div>
        `;
    }
    legendHtml += '</div>';
    legend.innerHTML = legendHtml;

    // Make legend items clickable to highlight
    legend.querySelectorAll('.legend-item').forEach(item => {
        item.addEventListener('click', () => {
            const model = item.dataset.model;
            const select = document.getElementById('highlight-model-select');
            if (state.mapHighlightModel === model) {
                state.mapHighlightModel = '';
                select.value = '';
            } else {
                state.mapHighlightModel = model;
                select.value = model;
            }
            renderScatterPlot();
        });
    });
}
