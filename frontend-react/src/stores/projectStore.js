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
    loadProjects: async () => {
        try {
            const projects = await api.getProjects()
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
                videoOutput: project.video_output || null,
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
                videoOutput = `${BASE_URL}/projects/${projectId}/renders/${filename}`
            }

            if (renderJob?.status === 'DONE' && renderJob.output) {
                const parts = renderJob.output.split(/[\\/]/)
                const filename = parts[parts.length - 1]
                videoOutput = `${BASE_URL}/projects/${projectId}/renders/${filename}`

                // Show completion toast once
                if (!get().videoOutput && videoOutput) {
                    get().addToast('🎉 Video render complete!', 'success')
                }
            }

            set({ jobs, videoOutput })

            await get().loadSegments()
            get().updateStep()

            const anyRunning = Object.values(jobs).some(
                j => j.status === 'RUNNING' || j.status === 'RETRYING'
            )

            if (anyRunning) {
                get().startPolling()
            } else {
                get().stopPolling()
                if (pipeJob?.status === 'DONE') {
                    await get().loadAnalysis()
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
        }, 3000)

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
        const { projectId } = get()
        if (!projectId) return null

        try {
            const result = await api.updateSegment(projectId, segmentId, payload)
            await get().loadSegments()
            get().addToast('Scene saved!', 'success')
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
            get().startPolling()

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
