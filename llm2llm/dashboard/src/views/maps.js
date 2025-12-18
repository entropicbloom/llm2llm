// Maps view - 2D scatter plots of conversations

import { state } from '../state.js';
import { getFilteredAnalyses } from '../data.js';
import { shortModel } from '../utils.js';

// Color palette for models
const MODEL_COLORS = [
    '#4285f4', '#ea4335', '#fbbc04', '#34a853', '#ff6d01',
    '#46bdc6', '#7baaf7', '#f07b72', '#fcd04f', '#81c995',
    '#ff9e80', '#78d9ec', '#aecbfa', '#f6aea9', '#fde293'
];

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

    // Build model color map
    const allModels = new Set();
    for (const a of analyses) {
        allModels.add(a.llm1_model);
        allModels.add(a.llm2_model);
    }
    const modelList = [...allModels].sort();
    const modelColorMap = {};
    modelList.forEach((model, i) => {
        modelColorMap[model] = MODEL_COLORS[i % MODEL_COLORS.length];
    });

    // Find data range dynamically with padding
    const xValues = analyses.map(a => a[xAxis] ?? 0);
    const yValues = analyses.map(a => a[yAxis] ?? 0);

    const dataXMin = Math.min(...xValues);
    const dataXMax = Math.max(...xValues);
    const dataYMin = Math.min(...yValues);
    const dataYMax = Math.max(...yValues);

    const xPadding = (dataXMax - dataXMin) * 0.15 || 0.1;
    const yPadding = (dataYMax - dataYMin) * 0.15 || 0.1;

    const xMin = Math.max(0, dataXMin - xPadding);
    const xMax = dataXMax + xPadding;
    const yMin = Math.max(0, dataYMin - yPadding);
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

    // Grid lines - calculate nice tick intervals
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

    // Plot points
    const points = [];
    for (const a of analyses) {
        const xVal = a[xAxis] ?? 0;
        const yVal = a[yAxis] ?? 0;
        const cx = scaleX(xVal);
        const cy = scaleY(yVal);

        // Determine color based on models involved
        // For now, use llm1 color, but show both on hover
        const color1 = modelColorMap[a.llm1_model];
        const color2 = modelColorMap[a.llm2_model];

        // Determine opacity based on highlight
        let opacity = 0.7;
        let radius = 6;
        if (highlightModel) {
            if (a.llm1_model === highlightModel || a.llm2_model === highlightModel) {
                opacity = 1;
                radius = 8;
            } else {
                opacity = 0.15;
                radius = 5;
            }
        }

        points.push({
            analysis: a,
            cx, cy,
            color1, color2,
            opacity, radius
        });
    }

    // Sort so highlighted points are on top
    points.sort((a, b) => a.opacity - b.opacity);

    for (const pt of points) {
        const a = pt.analysis;
        // Use a split circle to show both models
        if (a.llm1_model === a.llm2_model) {
            // Same model - solid circle
            svgContent += `<circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}"
                data-id="${a.conversation_id}" class="map-point" style="cursor: pointer;" />`;
        } else {
            // Different models - split circle using clip paths
            const id = a.conversation_id.slice(0, 8);
            svgContent += `
                <defs>
                    <clipPath id="left-${id}">
                        <rect x="${pt.cx - pt.radius}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                    <clipPath id="right-${id}">
                        <rect x="${pt.cx}" y="${pt.cy - pt.radius}" width="${pt.radius}" height="${pt.radius * 2}" />
                    </clipPath>
                </defs>
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color1}" opacity="${pt.opacity}" clip-path="url(#left-${id})"
                    data-id="${a.conversation_id}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="${pt.color2}" opacity="${pt.opacity}" clip-path="url(#right-${id})"
                    data-id="${a.conversation_id}" class="map-point" style="cursor: pointer;" />
                <circle cx="${pt.cx}" cy="${pt.cy}" r="${pt.radius}" fill="none" stroke="var(--border)" stroke-width="0.5" opacity="${pt.opacity}"
                    data-id="${a.conversation_id}" class="map-point" style="cursor: pointer;" />
            `;
        }
    }

    svg.innerHTML = svgContent;

    // Add event listeners for tooltips and clicks
    svg.querySelectorAll('.map-point').forEach(point => {
        point.addEventListener('mouseenter', (e) => {
            const id = e.target.dataset.id;
            const analysis = analyses.find(a => a.conversation_id === id);
            if (analysis) {
                tooltip.innerHTML = `
                    <div class="tooltip-title">${analysis.title || 'Untitled'}</div>
                    <div class="tooltip-models">
                        <span style="color: ${modelColorMap[analysis.llm1_model]}">${shortModel(analysis.llm1_model)}</span>
                        <span>↔</span>
                        <span style="color: ${modelColorMap[analysis.llm2_model]}">${shortModel(analysis.llm2_model)}</span>
                    </div>
                    <div class="tooltip-metrics">
                        D: ${(analysis.depth ?? 0).toFixed(2)} |
                        W: ${(analysis.warmth ?? 0).toFixed(2)} |
                        E: ${(analysis.energy ?? 0).toFixed(2)} |
                        S: ${(analysis.spirituality ?? 0).toFixed(2)}
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
            const id = e.target.dataset.id;
            if (id && window.openConversation) {
                window.openConversation(id);
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
