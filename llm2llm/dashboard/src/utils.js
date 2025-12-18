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

export function truncateText(text, maxChars, fromEnd = false) {
    if (!text) return '';
    // Strip markdown formatting for cleaner preview
    const clean = text
        .replace(/^#+\s*/gm, '')      // headers
        .replace(/\*\*([^*]+)\*\*/g, '$1')  // bold
        .replace(/\*([^*]+)\*/g, '$1')      // italic
        .replace(/`([^`]+)`/g, '$1')        // inline code
        .replace(/\n+/g, ' ')               // newlines to spaces
        .trim();
    if (clean.length <= maxChars) return escapeHtml(clean);

    if (fromEnd) {
        // Truncate from start - find first sentence end after cut point
        const cut = clean.slice(-maxChars);
        const sentenceMatch = cut.match(/^[^.!?]*[.!?]\s*/);
        if (sentenceMatch && sentenceMatch[0].length < cut.length * 0.7) {
            // Found a sentence boundary, skip to after it
            return '...' + escapeHtml(cut.slice(sentenceMatch[0].length).trim());
        }
        // Fall back to word boundary
        const firstSpace = cut.indexOf(' ');
        const trimmed = firstSpace > 0 ? cut.slice(firstSpace + 1) : cut;
        return '...' + escapeHtml(trimmed.trim());
    }

    // Truncate from end - find last sentence end before cut point
    const cut = clean.slice(0, maxChars);
    const lastSentenceEnd = Math.max(
        cut.lastIndexOf('. '),
        cut.lastIndexOf('! '),
        cut.lastIndexOf('? ')
    );
    if (lastSentenceEnd > maxChars * 0.3) {
        // Found a sentence boundary
        return escapeHtml(cut.slice(0, lastSentenceEnd + 1).trim());
    }
    // Fall back to word boundary
    const lastSpace = cut.lastIndexOf(' ');
    const trimmed = lastSpace > 0 ? cut.slice(0, lastSpace) : cut;
    return escapeHtml(trimmed.trim()) + '...';
}

export function renderMarkdown(text) {
    if (!text) return '';
    marked.setOptions({
        breaks: true,
        gfm: true,
    });
    return marked.parse(text);
}
