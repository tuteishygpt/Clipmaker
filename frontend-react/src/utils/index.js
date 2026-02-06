/**
 * Parse time string (e.g. "1:30" or "1:30:00") to seconds
 */
export function parseTimeToSeconds(t) {
    if (typeof t === 'number') {
        return isNaN(t) ? 0 : t
    }
    if (!t) return 0

    try {
        // Handle comma as decimal separator
        const normalized = String(t).trim().replace(',', '.')

        // Handle HH:MM:SS or MM:SS or SS
        if (normalized.includes(':')) {
            const parts = normalized.split(':').map(p => {
                const val = parseFloat(p)
                return isNaN(val) ? 0 : val
            })

            let seconds = 0
            if (parts.length === 1) seconds = parts[0]
            else if (parts.length === 2) seconds = parts[0] * 60 + parts[1]
            else if (parts.length === 3) seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]

            return seconds
        }

        // Direct number string
        const val = parseFloat(normalized)
        return isNaN(val) ? 0 : val
    } catch (e) {
        console.error('Time parsing error:', e)
        return 0
    }
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
 * Ensures image URL matches Vite proxy rules (starts with /api/static if applicable)
 */
export function fixImageUrl(path) {
    if (!path) return null;
    if (path.startsWith('http')) return path;

    const base = import.meta.env.VITE_API_BASE ?? '';

    // Convert relative static path to absolute for proxy
    if (path.startsWith('static/')) return base + '/' + path;
    if (path.startsWith('./static/')) return base + '/' + path.substring(2);

    // If it's already absolute but missing the base, add it
    if (path.startsWith('/') && base && !path.startsWith(base)) {
        return base + path;
    }

    return (path.startsWith('/') || !base) ? path : base + '/' + path;
}
