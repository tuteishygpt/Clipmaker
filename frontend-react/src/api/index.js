const BASE_URL = ''

async function fetchJSON(url, options = {}) {
    const response = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    })

    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
    }

    return response.json()
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

    const response = await fetch(`${BASE_URL}/projects/${projectId}/upload`, {
        method: 'POST',
        body: formData
    })

    if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`)
    }

    return response.json()
}

// Pipeline
export async function runPipeline(projectId) {
    return fetchJSON(`/projects/${projectId}/run`, { method: 'POST' })
}

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
