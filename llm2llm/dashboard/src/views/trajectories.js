// Trajectories view - 2D semantic paths through embedding space

import { state } from '../state.js';
import { shortModel, buildModelColorMap } from '../utils.js';

// Viewport transform (persists across re-renders)
let vt = { x: 0, y: 0, scale: 1 };

// Golden angle stepping for max hue separation between conversations
function convHue(index) {
    return (index * 137.508) % 360;
}

function getPairKey(conv) {
    return `${conv.llm1_model}|${conv.llm2_model}`;
}

function getPairLabel(conv) {
    return `${shortModel(conv.llm1_model)} + ${shortModel(conv.llm2_model)}`;
}

function isSelfTalk(conv) {
    return conv.llm1_model === conv.llm2_model;
}

// Get all pair keys
function getAllPairKeys() {
    const keys = new Set();
    for (const conv of Object.values(TRAJECTORY_DATA)) {
        keys.add(getPairKey(conv));
    }
    return keys;
}

// Get cross-model pair keys (non self-talk)
function getCrossModelPairKeys() {
    const keys = new Set();
    for (const conv of Object.values(TRAJECTORY_DATA)) {
        if (!isSelfTalk(conv)) keys.add(getPairKey(conv));
    }
    return keys;
}

// Check if self-talk mode is active (button state)
function _isSelfMode() {
    const btn = document.querySelector('.traj-mode-btn[data-mode="self"]');
    return btn && btn.classList.contains('active');
}

function isPairVisible(pairKey) {
    const hidden = state.trajHiddenPairs;
    if (!hidden || hidden.size === 0) return true;
    return !hidden.has(pairKey);
}

export function renderTrajectories(container) {
    if (typeof TRAJECTORY_DATA === 'undefined' || !TRAJECTORY_DATA || Object.keys(TRAJECTORY_DATA).length === 0) {
        container.innerHTML = `
            <div style="padding: 40px; text-align: center; color: var(--text-muted);">
                <p>No trajectory data available.</p>
                <p style="font-size: 12px; margin-top: 8px;">
                    Run <code>llm2llm embed</code> then <code>llm2llm trajectories</code> to generate.
                </p>
            </div>
        `;
        return;
    }

    // Build controls once
    if (!document.getElementById('traj-container')) {
        container.innerHTML = `
            <div class="traj-controls">
                <div class="traj-mode-tabs">
                    <button class="traj-mode-btn active" data-mode="all">All</button>
                    <button class="traj-mode-btn" data-mode="self">Self-talk</button>
                </div>
                <div class="traj-mode-tabs traj-range-tabs">
                    <button class="traj-mode-btn active" data-range="all">All</button>
                    <button class="traj-mode-btn" data-range="first5">First 5</button>
                    <button class="traj-mode-btn" data-range="last5">Last 5</button>
                </div>
                <div class="traj-toggle traj-slider-group">
                    <label for="traj-dot-size">Size</label>
                    <input type="range" id="traj-dot-size" min="1" max="8" step="0.5" value="3" class="traj-slider-wide">
                    <label for="traj-zoom">Zoom</label>
                    <input type="range" id="traj-zoom" min="0.5" max="10" step="0.1" value="1" class="traj-slider-wide">
                    <span class="legend-reset" id="traj-reset-sliders">Reset</span>
                </div>
            </div>
            <div id="traj-container">
                <svg id="traj-svg"></svg>
                <div id="traj-tooltip" class="traj-tooltip hidden"></div>
            </div>
            <div id="traj-legend" class="traj-legend"></div>
        `;

        // Mode tabs
        container.querySelectorAll('.traj-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.traj-mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                if (btn.dataset.mode === 'self') {
                    state.trajHiddenPairs = getCrossModelPairKeys();
                } else {
                    state.trajHiddenPairs = new Set();
                }
                renderTrajectorySVG();
            });
        });

        // Range tabs
        container.querySelectorAll('.traj-range-tabs .traj-mode-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('.traj-range-tabs .traj-mode-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                state.trajPointRange = btn.dataset.range;
                renderTrajectorySVG();
            });
        });

        document.getElementById('traj-zoom').addEventListener('input', (e) => {
            const newScale = parseFloat(e.target.value);
            const svg = document.getElementById('traj-svg');
            // Zoom centered on SVG midpoint
            const rect = svg.getBoundingClientRect();
            const cx = rect.width / 2;
            const cy = rect.height / 2;
            const ratio = newScale / vt.scale;
            vt.x = cx - ratio * (cx - vt.x);
            vt.y = cy - ratio * (cy - vt.y);
            vt.scale = newScale;
            applyViewTransform(svg);
        });

        document.getElementById('traj-reset-sliders').addEventListener('click', () => {
            state.trajDotSize = 3;
            vt = { x: 0, y: 0, scale: 1 };
            document.getElementById('traj-dot-size').value = 3;
            document.getElementById('traj-zoom').value = 1;
            const svg = document.getElementById('traj-svg');
            if (svg) applyViewTransform(svg);
        });

        document.getElementById('traj-dot-size').addEventListener('input', (e) => {
            state.trajDotSize = parseFloat(e.target.value);
            const svg = document.getElementById('traj-svg');
            if (svg) {
                const r = state.trajDotSize / vt.scale;
                svg.querySelectorAll('.traj-point').forEach(p => p.setAttribute('r', r));
            }
        });
    }

    renderTrajectorySVG();
}

function renderTrajectorySVG() {
    const svg = document.getElementById('traj-svg');
    const container = document.getElementById('traj-container');
    const tooltip = document.getElementById('traj-tooltip');
    const legend = document.getElementById('traj-legend');
    if (!svg || !container) return;

    // Track whether self-talk mode is active (for color scheme)
    const selfMode = _isSelfMode();

    // Provider colors only used in self-talk mode
    const modelColorMap = selfMode ? buildModelColorMap(
        new Set(Object.values(TRAJECTORY_DATA).flatMap(c => [c.llm1_model, c.llm2_model]))
    ) : null;

    // Dimensions
    const width = container.clientWidth || 800;
    const height = 550;
    const margin = { top: 20, right: 20, bottom: 20, left: 20 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;

    svg.setAttribute('width', width);
    svg.setAttribute('height', height);

    // Filter conversations by mode + visible pairs
    const convEntries = Object.entries(TRAJECTORY_DATA).filter(([, conv]) => {
        return isPairVisible(getPairKey(conv));
    });

    // Stable conversation index for golden-angle coloring (all mode)
    const allConvIds = Object.keys(TRAJECTORY_DATA).sort();
    const convIndex = {};
    allConvIds.forEach((id, i) => { convIndex[id] = i; });

    // Scale: data is normalized to [-1, 1]
    const scaleX = (v) => margin.left + ((v + 1) / 2) * plotWidth;
    const scaleY = (v) => margin.top + plotHeight - ((v + 1) / 2) * plotHeight;

    let svgContent = `<g id="traj-viewport" transform="translate(${vt.x},${vt.y}) scale(${vt.scale})">`;

    // Grid
    svgContent += `<rect x="${margin.left}" y="${margin.top}" width="${plotWidth}" height="${plotHeight}" fill="none" stroke="var(--border)" stroke-dasharray="2,2" opacity="0.3" />`;
    const ox = scaleX(0), oy = scaleY(0);
    svgContent += `<line x1="${margin.left}" y1="${oy}" x2="${margin.left + plotWidth}" y2="${oy}" stroke="var(--border)" stroke-dasharray="4,4" opacity="0.3" />`;
    svgContent += `<line x1="${ox}" y1="${margin.top}" x2="${ox}" y2="${margin.top + plotHeight}" stroke="var(--border)" stroke-dasharray="4,4" opacity="0.3" />`;

    // Point range filter
    const pointRange = state.trajPointRange || 'all';
    function filterRange(pts) {
        if (pointRange === 'first5') return pts.slice(0, 5);
        if (pointRange === 'last5') return pts.slice(-5);
        return pts;
    }

    // Draw points
    for (const [convId, conv] of convEntries) {
        const points = filterRange(conv.points);
        if (!points || points.length === 0) continue;
        const totalTurns = conv.points.length;

        if (selfMode && isSelfTalk(conv)) {
            const color = modelColorMap[conv.llm1_model];
            drawDots(points, convId, totalTurns, color);
        } else {
            const hue = convHue(convIndex[convId]);
            drawDotsHsl(points, convId, totalTurns, hue);
        }
    }

    function drawDots(pts, convId, totalTurns, color) {
        for (const pt of pts) {
            const opacity = 0.4 + 0.6 * (pt.turn / totalTurns);
            svgContent += `<circle cx="${scaleX(pt.x)}" cy="${scaleY(pt.y)}" r="${state.trajDotSize}" fill="${color}" opacity="${opacity.toFixed(2)}" class="traj-point"
                data-conv="${convId}" data-turn="${pt.turn}" data-role="${pt.role}" style="cursor: pointer;" />`;
        }
    }

    function drawDotsHsl(pts, convId, totalTurns, hue) {
        for (const pt of pts) {
            const progress = pt.turn / totalTurns;
            const lightness = 80 - progress * 40;
            const color = `hsl(${hue}, 65%, ${lightness}%)`;
            svgContent += `<circle cx="${scaleX(pt.x)}" cy="${scaleY(pt.y)}" r="${state.trajDotSize}" fill="${color}" class="traj-point"
                data-conv="${convId}" data-turn="${pt.turn}" data-role="${pt.role}" style="cursor: pointer;" />`;
        }
    }

    svgContent += '</g>';
    svg.innerHTML = svgContent;

    // Pan & zoom
    setupPanZoom(svg, container);

    // Hover: highlight trajectory, grey out the rest
    const allPoints = svg.querySelectorAll('.traj-point, .traj-start');

    allPoints.forEach(point => {
        point.addEventListener('mouseenter', (e) => {
            const hoveredConv = e.target.dataset.conv;
            const r = state.trajDotSize / vt.scale;
            const rHover = (state.trajDotSize + 1) / vt.scale;
            allPoints.forEach(p => {
                if (p.dataset.conv !== hoveredConv) {
                    p.classList.add('traj-dimmed');
                } else {
                    p.classList.add('traj-highlighted');
                    p.setAttribute('r', rHover);
                }
            });

            const conv = TRAJECTORY_DATA[hoveredConv];
            if (conv) {
                const turn = e.target.dataset.turn || '1';
                const role = e.target.dataset.role || '';
                const dataConv = typeof DATA !== 'undefined' && DATA.conversations
                    ? DATA.conversations.find(c => c.id === hoveredConv) : null;
                const title = dataConv && dataConv.title ? dataConv.title : hoveredConv.slice(0, 8) + '...';
                tooltip.innerHTML = `
                    <div class="tt-pair">${getPairLabel(conv)}</div>
                    <div class="tt-detail">Turn ${turn}${role ? ' \u00b7 ' + role : ''}</div>
                    <div class="tt-detail">${title}</div>
                `;
                tooltip.classList.remove('hidden');
                const rect = container.getBoundingClientRect();
                tooltip.style.left = (e.clientX - rect.left + 12) + 'px';
                tooltip.style.top = (e.clientY - rect.top - 12) + 'px';
            }
        });

        point.addEventListener('mouseleave', () => {
            const r = state.trajDotSize / vt.scale;
            allPoints.forEach(p => {
                p.classList.remove('traj-dimmed');
                p.classList.remove('traj-highlighted');
                p.setAttribute('r', r);
            });
            tooltip.classList.add('hidden');
        });

        point.addEventListener('click', (e) => {
            const convId = e.target.dataset.conv;
            const turn = parseInt(e.target.dataset.turn, 10);
            if (typeof window.openConversation === 'function') {
                window.openConversation(convId, turn);
            }
        });
    });

    // Legend — all pairs for current mode, togglable
    const allPairs = getAllPairKeys();
    const hidden = state.trajHiddenPairs || new Set();
    const hasFilter = hidden.size > 0;

    // Build pair info map (hide cross-model pairs from legend in self-talk mode)
    const pairInfo = new Map();
    for (const [convId, conv] of Object.entries(TRAJECTORY_DATA)) {
        if (selfMode && !isSelfTalk(conv)) continue;
        const pk = getPairKey(conv);
        if (!pairInfo.has(pk)) {
            pairInfo.set(pk, { label: getPairLabel(conv), convIds: [], conv });
        }
        pairInfo.get(pk).convIds.push(convId);
    }

    // Sort by label
    const sortedPairInfo = [...pairInfo.entries()].sort((a, b) => a[1].label.localeCompare(b[1].label));

    let legendHtml = `<div class="legend-header"><span class="legend-title">Pairs</span><span class="legend-actions">`;
    if (hasFilter) {
        legendHtml += `<span class="legend-reset" id="traj-reset-filter">Show all</span>`;
    }
    legendHtml += `<span class="legend-reset" id="traj-hide-all">Hide all</span>`;
    legendHtml += '</span></div><div class="legend-items">';

    for (const [key, info] of sortedPairInfo) {
        const isVisible = !hidden.has(key);

        // Color swatch
        let color;
        if (selfMode && isSelfTalk(info.conv)) {
            color = modelColorMap[info.conv.llm1_model];
        } else {
            const firstConvId = info.convIds[0];
            const hue = convHue(convIndex[firstConvId]);
            color = `hsl(${hue}, 65%, 60%)`;
        }

        const label = (selfMode && isSelfTalk(info.conv))
            ? `${shortModel(info.conv.llm1_model)} (${info.convIds.length})`
            : `${info.label} (${info.convIds.length})`;

        legendHtml += `
            <div class="legend-item ${isVisible ? '' : 'dimmed'}" data-pair="${key}" style="cursor: pointer;">
                <span class="legend-color" style="background: ${color}"></span>
                <span class="legend-label">${label}</span>
            </div>
        `;
    }
    legendHtml += '</div>';
    legend.innerHTML = legendHtml;

    // Toggle pairs on/off
    legend.querySelectorAll('.legend-item').forEach(item => {
        item.addEventListener('click', () => {
            const pair = item.dataset.pair;
            if (!state.trajHiddenPairs) state.trajHiddenPairs = new Set();

            if (state.trajHiddenPairs.has(pair)) {
                state.trajHiddenPairs.delete(pair);
            } else {
                state.trajHiddenPairs.add(pair);
            }

            renderTrajectorySVG();
        });
    });

    // Reset button
    const resetBtn = document.getElementById('traj-reset-filter');
    if (resetBtn) {
        resetBtn.addEventListener('click', () => {
            state.trajHiddenPairs = new Set();
            renderTrajectorySVG();
        });
    }

    // Hide all button
    const hideBtn = document.getElementById('traj-hide-all');
    if (hideBtn) {
        hideBtn.addEventListener('click', () => {
            state.trajHiddenPairs = new Set(allPairs);
            renderTrajectorySVG();
        });
    }

}

function applyViewTransform(svg) {
    const g = svg.getElementById('traj-viewport');
    if (g) g.setAttribute('transform', `translate(${vt.x},${vt.y}) scale(${vt.scale})`);
    // Keep dot sizes constant on screen
    const r = state.trajDotSize / vt.scale;
    svg.querySelectorAll('.traj-point').forEach(p => p.setAttribute('r', r));
    // Sync zoom slider
    const slider = document.getElementById('traj-zoom');
    if (slider) slider.value = vt.scale;
}

function setupPanZoom(svg, container) {
    let isPanning = false;
    let startX, startY, startVtX, startVtY;

    // Wheel zoom (centered on cursor)
    svg.addEventListener('wheel', (e) => {
        e.preventDefault();
        const rect = svg.getBoundingClientRect();
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;

        const factor = e.deltaY < 0 ? 1.15 : 1 / 1.15;
        const newScale = Math.min(Math.max(vt.scale * factor, 0.5), 10);
        const ratio = newScale / vt.scale;

        vt.x = mx - ratio * (mx - vt.x);
        vt.y = my - ratio * (my - vt.y);
        vt.scale = newScale;
        applyViewTransform(svg);
    }, { passive: false });

    // Mouse drag pan
    svg.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        isPanning = true;
        startX = e.clientX;
        startY = e.clientY;
        startVtX = vt.x;
        startVtY = vt.y;
        svg.style.cursor = 'grabbing';
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning) return;
        vt.x = startVtX + (e.clientX - startX);
        vt.y = startVtY + (e.clientY - startY);
        applyViewTransform(svg);
    });

    window.addEventListener('mouseup', () => {
        if (isPanning) {
            isPanning = false;
            svg.style.cursor = '';
        }
    });

    // Double-click to reset
    svg.addEventListener('dblclick', () => {
        vt = { x: 0, y: 0, scale: 1 };
        applyViewTransform(svg);
    });
}
