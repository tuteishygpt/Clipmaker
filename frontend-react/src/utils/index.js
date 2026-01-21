/**
 * Parse time string (e.g. "1:30" or "1:30:00") to seconds
 */
export function parseTimeToSeconds(t) {
    if (typeof t === 'number') return t
    if (!t) return 0

    const parts = t.split(':').map(parseFloat)

    if (parts.length === 1) return parts[0]
    if (parts.length === 2) return parts[0] * 60 + parts[1]
    if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2]

    return 0
}

/**
 * Format seconds to time string (e.g. 90 -> "1:30")
 */
export function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return '0:00'

    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)

    return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Ensures image URL matches Vite proxy rules (starts with /static if applicable)
 */
export function fixImageUrl(path) {
    if (!path) return null;
    if (path.startsWith('http')) return path;

    // Convert relative static path to absolute for proxy
    if (path.startsWith('static/')) return '/' + path;
    if (path.startsWith('./static/')) return path.substring(1);

    return path;
}
