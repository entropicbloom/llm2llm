// Utility functions

export function shortModel(model) {
    return model
        .replace('claude-', '')
        .replace('mistralai/', '')
        .replace('-20250514', '')
        .replace('-20250929', '')
        .replace('-20251001', '')
        .replace('-20251101', '')
        .replace('-20240229', '')
        .replace('-20241022', '')
        .replace('-20240307', '')
        .replace('-20250219', '')
        .replace('-20250805', '');
}

export function avg(arr) {
    if (!arr.length) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

export function metricColor(type, value, maxValue = 10) {
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;
    const normalized = Math.min(value / maxValue, 1);
    const saturation = 8 + (normalized * 37);
    const lightness = 95 - (normalized * 7);
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

export function metricTextColor(type, value, maxValue = 10) {
    const hues = { depth: 220, warmth: 15, energy: 165, spirituality: 280 };
    const hue = hues[type] || 220;
    const normalized = Math.min(value / maxValue, 1);
    const saturation = 30 + (normalized * 30);
    const lightness = 45 - (normalized * 15);
    return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

export function renderMarkdown(text) {
    if (!text) return '';
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
    return marked.parse(text);
}
