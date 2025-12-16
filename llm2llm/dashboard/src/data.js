// Data helpers for aggregation and filtering

import { state } from './state.js';
import { avg } from './utils.js';

/** Create empty stats object for aggregation */
export function createEmptyStats() {
    return {
        count: 0,
        depths: [],
        warmths: [],
        energies: [],
        spiritualities: [],
        topics: {},
    };
}

/** Aggregate metrics from an analysis into a stats object */
export function addAnalysisToStats(stats, analysis) {
    if (analysis.depth !== undefined) stats.depths.push(analysis.depth);
    if (analysis.warmth !== undefined) stats.warmths.push(analysis.warmth);
    if (analysis.energy !== undefined) stats.energies.push(analysis.energy);
    if (analysis.spirituality !== undefined) stats.spiritualities.push(analysis.spirituality);
    for (const [topic, score] of Object.entries(analysis.topics || {})) {
        if (!stats.topics[topic]) stats.topics[topic] = [];
        stats.topics[topic].push(score);
    }
}

/** Compute averages from collected arrays */
export function computeAverages(stats) {
    stats.depth = avg(stats.depths);
    stats.warmth = avg(stats.warmths);
    stats.energy = avg(stats.energies);
    stats.spirituality = avg(stats.spiritualities);
}

/** Get analyses filtered by selected segment */
export function getFilteredAnalyses() {
    if (state.selectedSegment === 'all') {
        const seen = new Set();
        return DATA.analyses.filter(a => {
            if (seen.has(a.conversation_id)) return false;
            seen.add(a.conversation_id);
            return true;
        });
    }

    const [start, end] = state.selectedSegment.split(':');
    const segStart = parseInt(start);
    const segEnd = end === '' ? null : parseInt(end);

    return DATA.analyses.filter(a =>
        a.segment_start === segStart &&
        a.segment_end === segEnd
    );
}
