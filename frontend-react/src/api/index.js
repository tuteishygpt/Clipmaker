import { supabase, isSupabaseConfigured } from '../lib/supabase'

export const BASE_URL = import.meta.env.VITE_API_BASE ?? ''

/**
 * Get the current authentication token from Supabase session.
 * Returns null if not authenticated or Supabase is not configured.
 */
async function getAuthToken() {
    if (!isSupabaseConfigured()) return null

    try {
        // Timeout auth check after 2 seconds to prevent blocking UI
        const sessionPromise = supabase.auth.getSession()
        const timeoutPromise = new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Auth check timed out')), 2000)
        )

        const { data: { session } } = await Promise.race([sessionPromise, timeoutPromise])
        return session?.access_token || null
    } catch (error) {
        console.warn('Failed to get auth token:', error)
        return null
    }
}

/**
 * Build headers with optional authentication.
 */
async function buildHeaders(options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    }

    // Add auth token if available
    const token = await getAuthToken()
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    return headers
}

async function fetchJSON(url, options = {}) {
    const headers = await buildHeaders(options)

    const controller = new AbortController()
    const id = setTimeout(() => controller.abort(), 15000) // 15s timeout

    try {
        const response = await fetch(`${BASE_URL}${url}`, {
            ...options,
            headers,
            signal: controller.signal
        })
        clearTimeout(id)

        if (!response.ok) {
            // Parse error response for billing errors
            let errorMessage = `HTTP error! status: ${response.status}`
            try {
                const errorData = await response.json()
                if (errorData.detail) {
                    errorMessage = errorData.detail
                }
            } catch (e) {
                // Ignore JSON parse errors
            }

            const error = new Error(errorMessage)
            error.status = response.status
            throw error
        }

        return response.json()
    } catch (error) {
        clearTimeout(id)
        if (error.name === 'AbortError') {
            throw new Error('Request timed out')
        }
        throw error
    }
}

// Projects
export async function getProjects() {
    return fetchJSON('/projects')
}

export async function getProject(projectId) {
    return fetchJSON(`/projects/${projectId}`)
}

export async function createProject(data) {
    return fetchJSON('/projects', {
        method: 'POST',
        body: JSON.stringify(data)
    })
}

// Audio
export async function uploadAudio(projectId, file) {
    const formData = new FormData()
    formData.append('audio', file)

    // Get auth token for uploads too
    const token = await getAuthToken()
    const headers = {}
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }

    const response = await fetch(`${BASE_URL}/projects/${projectId}/upload`, {
        method: 'POST',
        body: formData,
        headers
    })

    if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`)
    }

    return response.json()
}

// Pipeline (requires credits)
export async function runPipeline(projectId) {
    return fetchJSON(`/projects/${projectId}/run`, { method: 'POST' })
}

// Render (free, but authenticated)
export async function renderVideo(projectId) {
    return fetchJSON(`/projects/${projectId}/render`, { method: 'POST' })
}

export async function recalculateTimings(projectId) {
    return fetchJSON(`/projects/${projectId}/recalculate-timings`, { method: 'POST' })
}

// Jobs
export async function getJobs(projectId) {
    return fetchJSON(`/projects/${projectId}/jobs`)
}

// Analysis
export async function getAnalysis(projectId) {
    return fetchJSON(`/projects/${projectId}/analysis?t=${Date.now()}`)
}

// Segments
export async function getSegments(projectId) {
    return fetchJSON(`/projects/${projectId}/segments`)
}

export async function updateSegment(projectId, segmentId, payload) {
    return fetchJSON(`/projects/${projectId}/segments/${segmentId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
    })
}

// Regenerate segment (requires 1 credit)
export async function regenerateSegment(projectId, segmentId) {
    return fetchJSON(`/projects/${projectId}/segments/${segmentId}/regenerate`, {
        method: 'POST'
    })
}

// Utils
export function getAudioUrl(projectId) {
    return `${BASE_URL}/projects/${projectId}/audio?t=${Date.now()}`
}

export function getDownloadUrl(projectId) {
    return `${BASE_URL}/projects/${projectId}/download?t=${Date.now()}`
}

// Cabinet API (authenticated endpoints)
export async function getAccountStatus() {
    return fetchJSON('/cabinet/status')
}

export async function getCreditBalance() {
    return fetchJSON('/cabinet/credits')
}

export async function getSubscriptionStatus() {
    return fetchJSON('/cabinet/subscription')
}

export async function getTransactions(limit = 50, offset = 0) {
    return fetchJSON(`/cabinet/transactions?limit=${limit}&offset=${offset}`)
}

export async function updateProfile(payload) {
    return fetchJSON('/cabinet/profile', {
        method: 'POST',
        body: JSON.stringify(payload)
    })
}

export async function getUserProjects() {
    return fetchJSON('/cabinet/projects')
}

