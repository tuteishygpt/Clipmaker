import { create } from 'zustand'
import * as api from '../api'
import { BASE_URL } from '../api'
import { useBillingStore } from './billingStore'
import { useAuthStore } from './authStore'

export const useProjectStore = create((set, get) => ({
    // State
    projectId: null,
    projects: [],
    project: null,
    segments: [],
    jobs: {},
    analysis: null,
    videoOutput: null,
    audioUploaded: false,
    pollingInterval: null,
    isLoading: false,
    error: null,

    // Current Workflow Step: 'setup' | 'upload' | 'generate' | 'render' | 'complete'
    currentStep: 'setup',

    // Toast notifications
    toasts: [],

    addToast: (message, type = 'info') => {
        const id = Date.now()
        set(state => ({
            toasts: [...state.toasts, { id, message, type }]
        }))
        setTimeout(() => {
            set(state => ({
                toasts: state.toasts.filter(t => t.id !== id)
            }))
        }, 4000)
    },

    removeToast: (id) => {
        set(state => ({
            toasts: state.toasts.filter(t => t.id !== id)
        }))
    },

    // Lightbox
    lightboxSrc: null,
    showLightbox: (src) => set({ lightboxSrc: src }),
    hideLightbox: () => set({ lightboxSrc: null }),

    // Set current step
    setStep: (step) => set({ currentStep: step }),

    // Calculate current step based on project state
    updateStep: () => {
        const { projectId, audioUploaded, segments, videoOutput } = get()
        console.log('Updating step state:', { projectId, audioUploaded, segmentsLen: segments.length, videoOutput })

        if (!projectId) {
            set({ currentStep: 'setup' })
            return
        }

        // Check status in reverse order of priority
        if (videoOutput) {
            set({ currentStep: 'complete' })
            return
        }

        if (segments.length > 0) {
            set({ currentStep: 'render' })
            return
        }

        if (audioUploaded) {
            set({ currentStep: 'generate' })
            return
        }

        set({ currentStep: 'upload' })
    },

    // Project Actions
    loadProjects: async (search = '') => {
        try {
            const projects = await api.getProjects(search)
            set({ projects })
        } catch (error) {
            console.error('Failed to load projects:', error)
        }
    },

    openProject: async (projectId) => {
        if (!projectId) return

        set({ isLoading: true, error: null })
        try {
            const project = await api.getProject(projectId)
            set({
                projectId: project.id,
                project,
                videoOutput: project.video_output
                    ? `${BASE_URL}${project.video_output}?t=${Date.now()}`
                    : null,
                audioUploaded: !!project.audio_file
            })

            // Load related data
            await Promise.all([
                get().refreshJobs(),
                get().loadAnalysis(),
                get().loadSegments()
            ])

            // Resilience: If we have segments, we must have had audio
            if (get().segments.length > 0) {
                set({ audioUploaded: true })
            }

            get().updateStep()
            get().addToast(`Project loaded: ${project.id.slice(0, 8)}...`, 'success')
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to load project', 'error')
        } finally {
            set({ isLoading: false })
        }
    },

    createProject: async (data) => {
        set({ isLoading: true })
        try {
            const project = await api.createProject(data)
            set({
                projectId: project.id,
                project,
                videoOutput: null,
                segments: [],
                analysis: null,
                audioUploaded: false,
                currentStep: 'upload'
            })
            await get().loadProjects()
            get().addToast('Project created successfully!', 'success')
            return project
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to create project', 'error')
            return null
        } finally {
            set({ isLoading: false })
        }
    },

    // Audio
    uploadAudio: async (file) => {
        const { projectId } = get()
        if (!projectId || !file) return null

        set({ isLoading: true })
        try {
            const result = await api.uploadAudio(projectId, file)
            set({ audioUploaded: true, currentStep: 'generate' })
            get().addToast('Audio uploaded successfully!', 'success')
            return result
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to upload audio', 'error')
            return null
        } finally {
            set({ isLoading: false })
        }
    },

    // Pipeline
    runPipeline: async () => {
        const { projectId } = get()
        if (!projectId) return

        set({ isLoading: true })
        try {
            const result = await api.runPipeline(projectId)
            await get().refreshJobs()
            get().startPolling()
            get().addToast(result.message || 'Scene generation started...', 'info')

            // Refresh billing data after credits are deducted
            const { user } = useAuthStore.getState()
            if (user) {
                useBillingStore.getState().loadBillingData(user.id)
            }

            return result
        } catch (error) {
            set({ error: error.message })

            // Check if it's a billing error (402 Payment Required)
            if (error.status === 402) {
                get().addToast(error.message || 'Insufficient credits or subscription required', 'error')
                // Refresh billing data to show current status
                const { user } = useAuthStore.getState()
                if (user) {
                    useBillingStore.getState().loadBillingData(user.id)
                }
            } else if (error.status === 401) {
                get().addToast('Please log in to generate content', 'error')
            } else {
                get().addToast('Failed to start generation', 'error')
            }
        } finally {
            set({ isLoading: false })
        }
    },

    renderVideo: async () => {
        const { projectId } = get()
        if (!projectId) return

        set({ isLoading: true })
        try {
            const result = await api.renderVideo(projectId)
            await get().refreshJobs()
            get().startPolling()
            get().addToast('Video rendering started...', 'info')
            return result
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to start render', 'error')
        } finally {
            set({ isLoading: false })
        }
    },

    recalculateTimings: async () => {
        const { projectId } = get()
        if (!projectId) return

        try {
            const result = await api.recalculateTimings(projectId)
            await get().loadSegments()
            get().addToast('Timings recalculated!', 'success')
            return result
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to recalculate', 'error')
        }
    },

    // Jobs & Polling
    refreshJobs: async () => {
        const { projectId } = get()
        if (!projectId) return

        try {
            const data = await api.getJobs(projectId)
            const jobs = data.jobs || {}

            let videoOutput = get().videoOutput
            const pipeJob = jobs.pipeline
            const renderJob = jobs.render

            if (pipeJob?.status === 'DONE' && pipeJob.output) {
                const parts = pipeJob.output.split(/[\\/]/)
                const filename = parts[parts.length - 1]
                const baseUrl = `${BASE_URL}/projects/${projectId}/renders/${filename}`

                // Only update if currently different (ignoring query params)
                const currentUrlBase = get().videoOutput?.split('?')[0]
                if (currentUrlBase !== baseUrl) {
                    videoOutput = `${baseUrl}?t=${Date.now()}`
                } else {
                    videoOutput = get().videoOutput
                }
            }

            if (renderJob?.status === 'DONE' && renderJob.output) {
                const parts = renderJob.output.split(/[\\/]/)
                const filename = parts[parts.length - 1]
                const baseUrl = `${BASE_URL}/projects/${projectId}/renders/${filename}`

                const currentUrlBase = get().videoOutput?.split('?')[0]
                if (currentUrlBase !== baseUrl) {
                    videoOutput = `${baseUrl}?t=${Date.now()}`
                    // Show completion toast once
                    if (!get().videoOutput) {
                        get().addToast('🎉 Video render complete!', 'success')
                    }
                } else {
                    videoOutput = get().videoOutput
                }
            }

            // Only update state if something changed to avoid re-renders
            if (JSON.stringify(jobs) !== JSON.stringify(get().jobs) || videoOutput !== get().videoOutput) {
                set({ jobs, videoOutput })
            }

            // Load analysis during pipeline run to show live data
            const pipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'
            if (pipelineRunning) {
                await get().loadAnalysis()
            }

            // Only load segments if pipeline is running (to see new thumbnails) 
            // or if we just finished some job that might update segments
            if (pipelineRunning) {
                await get().loadSegments()
            }

            get().updateStep()

            const anyRunning = Object.values(jobs).some(
                j => j.status === 'RUNNING' || j.status === 'RETRYING'
            )

            if (anyRunning) {
                get().startPolling()
            } else {
                get().stopPolling()
                if (pipeJob?.status === 'DONE') {
                    // One final load
                    await get().loadAnalysis()
                    await get().loadSegments()
                }
            }

            return jobs
        } catch (error) {
            console.error('Failed to refresh jobs:', error)
        }
    },

    startPolling: () => {
        const { pollingInterval } = get()
        if (pollingInterval) return

        const interval = setInterval(() => {
            get().refreshJobs()
        }, 5000)

        set({ pollingInterval: interval })
    },

    stopPolling: () => {
        const { pollingInterval } = get()
        if (pollingInterval) {
            clearInterval(pollingInterval)
            set({ pollingInterval: null })
        }
    },

    // Analysis
    loadAnalysis: async () => {
        const { projectId } = get()
        if (!projectId) return

        try {
            const analysis = await api.getAnalysis(projectId)
            set({ analysis })
        } catch (error) {
            set({ analysis: null })
        }
    },

    // Segments
    loadSegments: async () => {
        const { projectId } = get()
        if (!projectId) return []

        try {
            const data = await api.getSegments(projectId)
            const segments = data.segments || []
            set({ segments })
            return segments
        } catch (error) {
            set({ segments: [] })
            return []
        }
    },

    updateSegment: async (segmentId, payload) => {
        const { projectId, segments } = get()
        if (!projectId) return null

        const neighborUpdates = []
        const currentIndex = segments.findIndex(s => s.id === segmentId)

        if (currentIndex !== -1) {
            const currentSegment = segments[currentIndex]

            // Check if Start Time changed -> Update Prev Segment End Time
            // Use loose equality to handle string/number differences
            if (payload.start_time !== undefined && payload.start_time != currentSegment.start_time) {
                const prevSegment = segments[currentIndex - 1]
                if (prevSegment) {
                    neighborUpdates.push({
                        id: prevSegment.id,
                        payload: { end_time: payload.start_time }
                    })
                }
            }

            // Check if End Time changed -> Update Next Segment Start Time
            if (payload.end_time !== undefined && payload.end_time != currentSegment.end_time) {
                const nextSegment = segments[currentIndex + 1]
                if (nextSegment) {
                    neighborUpdates.push({
                        id: nextSegment.id,
                        payload: { start_time: payload.end_time }
                    })
                }
            }
        }

        try {
            const result = await api.updateSegment(projectId, segmentId, payload)

            // Update neighbors if needed
            if (neighborUpdates.length > 0) {
                await Promise.all(neighborUpdates.map(u =>
                    api.updateSegment(projectId, u.id, u.payload)
                ))
                get().addToast('Scene and neighbors synced!', 'success')
            } else {
                get().addToast('Scene saved!', 'success')
            }

            await get().loadSegments()
            return result
        } catch (error) {
            set({ error: error.message })
            get().addToast('Failed to save scene', 'error')
            return null
        }
    },

    regenerateSegment: async (segmentId) => {
        const { projectId } = get()
        if (!projectId) return

        try {
            const result = await api.regenerateSegment(projectId, segmentId)
            // Start polling anyway for resilience
            get().startPolling()

            // IMMEDIATE update: reload segments to get the new version info
            await get().loadSegments()

            // Show credits used if returned
            if (result.credits_used) {
                get().addToast(`Regenerating image (${result.credits_used} credit used)...`, 'info')
            } else {
                get().addToast('Regenerating image...', 'info')
            }

            // Refresh billing data after credits are deducted
            const { user } = useAuthStore.getState()
            if (user) {
                useBillingStore.getState().loadBillingData(user.id)
            }
        } catch (error) {
            set({ error: error.message })

            // Check if it's a billing error (402 Payment Required)
            if (error.status === 402) {
                get().addToast(error.message || 'Insufficient credits', 'error')
                // Refresh billing data
                const { user } = useAuthStore.getState()
                if (user) {
                    useBillingStore.getState().loadBillingData(user.id)
                }
            } else if (error.status === 401) {
                get().addToast('Please log in to regenerate', 'error')
            } else {
                get().addToast('Failed to regenerate', 'error')
            }
        }
    },

    regeneratePrompt: async (segmentId) => {
        const { projectId } = get()
        if (!projectId) return

        try {
            await api.regeneratePrompt(projectId, segmentId)

            // Reload segments to get the new prompt text
            await get().loadSegments()

            get().addToast('Prompt regenerated', 'success')
        } catch (error) {
            console.error('Prompt regeneration error:', error);
            set({ error: error.message })
            const msg = error.message.includes('timed out')
                ? 'Regeneration timed out. The server might still be working, please refresh in a minute.'
                : `Failed to regenerate prompt: ${error.message}`;
            get().addToast(msg, 'error')
        }
    },

    regenerateImage: async (segmentId) => {
        const { projectId } = get()
        if (!projectId) return

        try {
            const result = await api.regenerateImage(projectId, segmentId)

            // Start polling 
            get().startPolling()

            // IMMEDIATE update: reload segments
            await get().loadSegments()

            if (result && result.credits_used) {
                get().addToast(`Regenerating image (${result.credits_used} credit)...`, 'info')
            } else {
                get().addToast('Regenerating image...', 'info')
            }

            // Refresh billing data
            const { user } = useAuthStore.getState()
            if (user) {
                useBillingStore.getState().loadBillingData(user.id)
            }
        } catch (error) {
            set({ error: error.message })

            if (error.status === 402) {
                get().addToast(error.message || 'Insufficient credits', 'error')
                const { user } = useAuthStore.getState()
                if (user) {
                    useBillingStore.getState().loadBillingData(user.id)
                }
            } else if (error.status === 401) {
                get().addToast('Please log in to regenerate', 'error')
            } else {
                get().addToast('Failed to regenerate image', 'error')
            }
        }
    },

    // Reset project
    resetProject: () => {
        set({
            projectId: null,
            project: null,
            segments: [],
            jobs: {},
            analysis: null,
            videoOutput: null,
            audioUploaded: false,
            currentStep: 'setup'
        })
    }
}))
