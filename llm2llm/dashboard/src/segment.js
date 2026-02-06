// Segment selector helpers

import { state } from './state.js';

let segmentOptions = null;

export function buildSegmentOptions() {
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

    // Set default segment on first call
    if (state.selectedSegment === 'all' && segments.size > 1) {
        state.selectedSegment = Array.from(segments.keys())[1];
    }

    segmentOptions = segments;
    return segments;
}

export function getSegmentSelectorHTML() {
    const segments = segmentOptions || buildSegmentOptions();
    if (segments.size <= 1) return '';

    const options = Array.from(segments).map(([value, label]) =>
        `<option value="${value}" ${state.selectedSegment === value ? 'selected' : ''}>${label}</option>`
    ).join('');

    return `
        <div class="segment-selector">
            <label>Analyzed segment:</label>
            <select id="segment-select">${options}</select>
        </div>
    `;
}

export function attachSegmentListener() {
    const select = document.getElementById('segment-select');
    if (!select) return;
    select.addEventListener('change', (e) => {
        state.selectedSegment = e.target.value;
        document.dispatchEvent(new CustomEvent('segment-change'));
    });
}
