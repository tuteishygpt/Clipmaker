import { useState, useRef, useCallback, useEffect } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import Header from './Header'
import SubtitleVideoPlayer, { parseSrtTimeToSeconds } from './SubtitleVideoPlayer'
import SubtitleTimeline from './SubtitleTimeline'
import SubtitlePresetsGallery, { STUDIO_PRESETS } from './SubtitlePresetsGallery'
import SubtitleEntryCard, { formatSecondsToSrt, sanitizeHighlightTags } from './SubtitleEntryCard'
import { useTranslation } from '../i18n'
import './SubtitleStudio.css'
import * as api from '../api'
import { useProjectStore } from '../stores/projectStore'

const FONT_CATEGORIES = {
    'Sans-serif': [
        'Montserrat', 'Inter', 'Roboto', 'Open Sans', 'Lato', 'Poppins',
        'Nunito', 'Raleway', 'Ubuntu', 'Oswald', 'Outfit', 'Manrope'
    ],
    'Display & Viral': [
        'Impact', 'Bebas Neue', 'Anton', 'Righteous', 'Permanent Marker',
        'Russo One', 'Bangers', 'Black Ops One'
    ],
    'Serif': [
        'Playfair Display', 'Merriweather', 'Lora', 'PT Serif'
    ],
    'Monospace': [
        'Fira Code', 'JetBrains Mono', 'Roboto Mono'
    ]
}

const DEFAULT_STYLING = {
    font_family: 'Montserrat',
    font_size: 48,
    font_weight: '900',
    font_color: '#FFE600',
    stroke_color: '#000000',
    stroke_width: 4,
    background_enabled: false,
    background_color: '#000000',
    background_opacity: 0.75,
    background_padding: 10,
    background_radius: 8,
    position: 'bottom',
    margin_y: 60,
    text_align: 'center',
    max_width_percent: 90,
    uppercase: true,
    animation: 'pop',
    highlight_active_word: true,
    highlight_font_color: '#FFFFFF',
    highlight_bg_color: '#FF0000',
    highlight_bg_padding: 8,
    highlight_bg_radius: 8
}

export default function SubtitleStandalonePage() {
    const { t } = useTranslation()
    const [searchParams, setSearchParams] = useSearchParams()
    const projectIdParam = searchParams.get('project')

    // Project & Video State
    const [projectId, setProjectId] = useState(projectIdParam || null)
    const [projectTitle, setProjectTitle] = useState('My Video')
    const [videoFile, setVideoFile] = useState(null)
    const [videoUrl, setVideoUrl] = useState(projectIdParam ? api.getVideoUrl(projectIdParam) : null)
    const [format, setFormat] = useState('9:16')
    const [status, setStatus] = useState('idle') // idle, uploading, transcribing, ready, rendering, done, error
    const [error, setError] = useState(null)
    const [progress, setProgress] = useState(0)
    const [transcribingSeconds, setTranscribingSeconds] = useState(0)

    // Subtitle Data
    const [entries, setEntries] = useState([])
    const [styling, setStyling] = useState(DEFAULT_STYLING)
    const [activeTab, setActiveTab] = useState('captions') // captions, styling, presets
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedLanguage, setSelectedLanguage] = useState('auto')
    const [autosaveStatus, setAutosaveStatus] = useState('saved') // saved, saving, unsaved

    // Video Player & Timeline Tracking
    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [activeEntryId, setActiveEntryId] = useState(null)

    // Existing Projects List & Switcher State
    const [projectsList, setProjectsList] = useState([])
    const [isDropdownOpen, setIsDropdownOpen] = useState(false)
    const [projectSearchQuery, setProjectSearchQuery] = useState('')

    // Render & Export Dropdown State
    const [isRenderDirty, setIsRenderDirty] = useState(false)
    const [isExportDropdownOpen, setIsExportDropdownOpen] = useState(false)

    // Refs
    const playerRef = useRef(null)
    const fileInputRef = useRef(null)
    const pollTimerRef = useRef(null)
    const transcribingTimerRef = useRef(null)
    const autosaveTimerRef = useRef(null)
    const isUserTypingRef = useRef(false)
    const activeEntryIdRef = useRef(null)
    const entriesListRef = useRef(null)
    const projectDropdownRef = useRef(null)
    const exportDropdownRef = useRef(null)
    const autoDownloadOnFinishRef = useRef(false)

    // Helper: Trigger browser file download
    const triggerFileDownload = (url, filename) => {
        if (!url) return
        const a = document.createElement('a')
        a.href = url
        if (filename) a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
    }

    // Helper: Flush pending autosave immediately
    const flushPendingAutosave = useCallback(async (currentEntries = entries, currentStyling = styling) => {
        if (!projectId) return
        if (autosaveTimerRef.current) {
            clearTimeout(autosaveTimerRef.current)
            autosaveTimerRef.current = null
        }
        setAutosaveStatus('saving')
        try {
            await api.updateSubtitles(projectId, {
                entries: currentEntries,
                styling: currentStyling
            })
            setAutosaveStatus('saved')
        } catch (err) {
            console.error('Failed to save subtitles:', err)
            setAutosaveStatus('unsaved')
        }
    }, [projectId, entries, styling])

    // Helper: Trigger debounced autosave
    const triggerAutosave = useCallback((newEntries, newStyling) => {
        setIsRenderDirty(true)
        if (!projectId) return
        setAutosaveStatus('saving')
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)

        autosaveTimerRef.current = setTimeout(async () => {
            try {
                await api.updateSubtitles(projectId, {
                    entries: newEntries,
                    styling: newStyling
                })
                setAutosaveStatus('saved')
            } catch (err) {
                console.error('Autosave error:', err)
                setAutosaveStatus('unsaved')
            }
        }, 600)
    }, [projectId])

    // Load Subtitles from backend
    const loadSubtitles = useCallback(async (id = projectId) => {
        if (!id) return
        try {
            const data = await api.getSubtitles(id)
            setEntries(data.entries || [])
            if (data.styling) {
                setStyling(prev => ({ ...prev, ...data.styling }))
            }
        } catch (err) {
            console.error('Failed to load subtitles:', err)
        }
    }, [projectId])

    // Poll render progress
    const startPolling = useCallback((id) => {
        if (pollTimerRef.current) clearInterval(pollTimerRef.current)

        pollTimerRef.current = setInterval(async () => {
            try {
                const jobsRes = await api.getJobs(id)
                const renderJob = jobsRes.jobs?.render

                if (renderJob?.status === 'DONE') {
                    clearInterval(pollTimerRef.current)
                    pollTimerRef.current = null
                    setStatus('done')
                    setIsRenderDirty(false)
                    loadSubtitles(id)
                    if (autoDownloadOnFinishRef.current) {
                        autoDownloadOnFinishRef.current = false
                        const url = api.getDownloadUrl(id)
                        triggerFileDownload(url, `${projectTitle || 'video'}.mp4`)
                    }
                } else if (renderJob?.status === 'ERROR') {
                    clearInterval(pollTimerRef.current)
                    pollTimerRef.current = null
                    autoDownloadOnFinishRef.current = false
                    setError(renderJob.message || 'Render failed')
                    setStatus('ready')
                } else if (renderJob?.progress !== undefined) {
                    setProgress(renderJob.progress)
                }
            } catch (err) {
                console.error('Polling error:', err)
            }
        }, 1000)
    }, [loadSubtitles, projectTitle])

    // Load list of all projects
    const loadProjectsList = useCallback(async () => {
        try {
            const data = await api.getProjects()
            if (Array.isArray(data)) {
                setProjectsList(data)
            }
        } catch (err) {
            console.warn('Failed to load projects list:', err)
        }
    }, [])

    useEffect(() => {
        loadProjectsList()
    }, [loadProjectsList])

    // Close dropdowns when clicking outside or pressing Escape
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (projectDropdownRef.current && !projectDropdownRef.current.contains(e.target)) {
                setIsDropdownOpen(false)
                setProjectSearchQuery('')
            }
            if (exportDropdownRef.current && !exportDropdownRef.current.contains(e.target)) {
                setIsExportDropdownOpen(false)
            }
        }
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                setIsDropdownOpen(false)
                setProjectSearchQuery('')
                setIsExportDropdownOpen(false)
            }
        }
        if (isDropdownOpen || isExportDropdownOpen) {
            document.addEventListener('mousedown', handleClickOutside)
            document.addEventListener('keydown', handleKeyDown)
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
            document.removeEventListener('keydown', handleKeyDown)
        }
    }, [isDropdownOpen, isExportDropdownOpen])

    // Clean up timers on unmount
    useEffect(() => {
        return () => {
            if (pollTimerRef.current) clearInterval(pollTimerRef.current)
            if (transcribingTimerRef.current) clearInterval(transcribingTimerRef.current)
            if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current)
        }
    }, [])

    // Switch to another project
    const handleSwitchProject = useCallback(async (targetId) => {
        if (!targetId || targetId === projectId) {
            setIsDropdownOpen(false)
            setProjectSearchQuery('')
            return
        }
        setIsDropdownOpen(false)
        setProjectSearchQuery('')
        await flushPendingAutosave(entries, styling)

        if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
        }
        if (transcribingTimerRef.current) {
            clearInterval(transcribingTimerRef.current)
            transcribingTimerRef.current = null
        }

        setCurrentTime(0)
        setDuration(0)
        setSearchParams({ project: targetId })
    }, [projectId, entries, styling, flushPendingAutosave, setSearchParams])

    // Start a new video (clean reset)
    const handleStartNewVideo = useCallback(async () => {
        setIsDropdownOpen(false)
        setIsExportDropdownOpen(false)
        setIsRenderDirty(false)
        autoDownloadOnFinishRef.current = false
        await flushPendingAutosave(entries, styling)

        if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current)
            pollTimerRef.current = null
        }
        if (transcribingTimerRef.current) {
            clearInterval(transcribingTimerRef.current)
            transcribingTimerRef.current = null
        }

        setProjectId(null)
        setProjectTitle('My Video')
        setVideoFile(null)
        setVideoUrl(null)
        setEntries([])
        setStatus('idle')
        setProgress(0)
        setError(null)
        setCurrentTime(0)
        setDuration(0)
        setSearchParams({})
        loadProjectsList()
    }, [entries, styling, flushPendingAutosave, setSearchParams, loadProjectsList])

    // Load existing project if URL param ?project=<id> is present, or reset if absent
    useEffect(() => {
        if (!projectIdParam) {
            setProjectId(null)
            setProjectTitle('My Video')
            setVideoFile(null)
            setVideoUrl(null)
            setEntries([])
            setStatus('idle')
            setProgress(0)
            setError(null)
            setIsRenderDirty(false)
            return
        }
        let isCancelled = false

        const loadExistingProject = async () => {
            setStatus('loading')
            setError(null)
            try {
                const proj = await api.getProject(projectIdParam)
                if (isCancelled) return

                setProjectId(proj.id)
                setProjectTitle(proj.title || 'Project')
                setFormat(proj.format || '9:16')
                setVideoUrl(api.getVideoUrl(proj.id))
                await loadSubtitles(proj.id)

                // Check render status
                try {
                    const jobsData = await api.getJobs(proj.id)
                    const renderJob = jobsData.jobs?.render
                    if (renderJob?.status === 'DONE') {
                        setStatus('done')
                        setIsRenderDirty(false)
                    } else if (renderJob?.status === 'RUNNING') {
                        setStatus('rendering')
                        setProgress(renderJob.progress || 0)
                        startPolling(proj.id)
                    } else {
                        setStatus('ready')
                        setIsRenderDirty(true)
                    }
                } catch (_) {
                    setStatus('ready')
                    setIsRenderDirty(true)
                }
            } catch (err) {
                if (!isCancelled) {
                    setError('Failed to load project: ' + err.message)
                    setStatus('error')
                }
            }
        }

        loadExistingProject()
        return () => { isCancelled = true }
    }, [projectIdParam, startPolling, loadSubtitles])

    // Video duration and time synchronization
    const handleTimeUpdate = useCallback((time) => {
        setCurrentTime(time)

        // Find active entry
        const match = entries.find(e => {
            const s = parseSrtTimeToSeconds(e.start_time)
            const end = parseSrtTimeToSeconds(e.end_time)
            return time >= s && time <= end
        })

        if (match) {
            setActiveEntryId(match.id)
            if (activeEntryIdRef.current !== match.id) {
                activeEntryIdRef.current = match.id
                // Auto-scroll list only when active entry changes and user is not actively typing
                if (!isUserTypingRef.current && entriesListRef.current) {
                    const cardEl = entriesListRef.current.querySelector(`[data-entry-id="${match.id}"]`)
                    if (cardEl) {
                        cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
                    }
                }
            }
        } else {
            setActiveEntryId(null)
            activeEntryIdRef.current = null
        }
    }, [entries])

    // Video metadata
    const getVideoMetadata = (file) => {
        return new Promise((resolve) => {
            const v = document.createElement('video')
            v.preload = 'metadata'
            const url = URL.createObjectURL(file)
            v.onloadedmetadata = () => {
                const data = { width: v.videoWidth, height: v.videoHeight, duration: v.duration }
                URL.revokeObjectURL(url)
                resolve(data)
            }
            v.onerror = () => {
                URL.revokeObjectURL(url)
                resolve({ width: 0, height: 0, duration: 0 })
            }
            v.src = url
        })
    }

    // Video Upload & Auto-Transcribe flow
    const handleFileSelect = async (file) => {
        if (!file || !file.type.startsWith('video/')) {
            setError('Please upload a valid video file (MP4, MOV, WebM)')
            return
        }

        setError(null)
        const meta = await getVideoMetadata(file)
        if (meta.duration && meta.duration > 900) {
            setError(`Video duration is too long (${Math.floor(meta.duration / 60)}m). Limit is 15 minutes.`)
            return
        }

        setDuration(meta.duration || 0)
        const isHorizontal = meta.width > meta.height
        const detectedFormat = isHorizontal ? '16:9' : '9:16'
        setFormat(detectedFormat)
        setVideoFile(file)
        setVideoUrl(URL.createObjectURL(file))
        setProjectTitle(file.name)

        // Start upload & automatic transcription
        setStatus('uploading')
        try {
            const project = await api.createProject({
                title: file.name,
                format: detectedFormat,
                style: 'default',
                standalone_mode: true
            })

            const id = project.id
            setProjectId(id)
            setSearchParams({ project: id })

            await api.uploadVideoStandalone(id, file)

            // Start AI Transcription
            setStatus('transcribing')
            setTranscribingSeconds(0)
            if (transcribingTimerRef.current) clearInterval(transcribingTimerRef.current)
            transcribingTimerRef.current = setInterval(() => {
                setTranscribingSeconds(s => s + 1)
            }, 1000)

            try {
                const genRes = await api.generateSubtitles(id, {
                    language: selectedLanguage,
                    min_words: 1,
                    max_words: detectedFormat === '9:16' ? 5 : 8
                })

                if (genRes.entries && genRes.entries.length > 0) {
                    setEntries(genRes.entries)
                    if (genRes.styling) {
                        setStyling(prev => ({ ...prev, ...genRes.styling }))
                    }
                }
            } catch (transcribeErr) {
                console.warn('Auto transcription fallback:', transcribeErr)
                // If transcription fails (e.g. no speech), still open studio
            } finally {
                if (transcribingTimerRef.current) {
                    clearInterval(transcribingTimerRef.current)
                    transcribingTimerRef.current = null
                }
            }

            // Refresh project store and list
            useProjectStore.getState().loadProjects()
            loadProjectsList()

            setStatus('ready')

        } catch (err) {
            setError(err.message || 'Upload failed')
            setStatus('error')
        }
    }

    // Manual transcription trigger
    const handleTranscribeAgain = async () => {
        if (!projectId) return
        setStatus('transcribing')
        setTranscribingSeconds(0)
        if (transcribingTimerRef.current) clearInterval(transcribingTimerRef.current)
        transcribingTimerRef.current = setInterval(() => {
            setTranscribingSeconds(s => s + 1)
        }, 1000)

        try {
            const genRes = await api.generateSubtitles(projectId, {
                language: selectedLanguage,
                min_words: 1,
                max_words: format === '9:16' ? 5 : 8
            })
            setEntries(genRes.entries || [])
            if (genRes.styling) {
                setStyling(prev => ({ ...prev, ...genRes.styling }))
            }
            setStatus('ready')
        } catch (err) {
            setError(err.message || 'Transcription error')
            setStatus('ready')
        } finally {
            if (transcribingTimerRef.current) {
                clearInterval(transcribingTimerRef.current)
                transcribingTimerRef.current = null
            }
        }
    }

    // Update entry text or timestamps
    const handleUpdateEntry = (id, field, val) => {
        setEntries(prev => {
            const updated = prev.map(e => e.id === id ? { ...e, [field]: val } : e)
            triggerAutosave(updated, styling)
            return updated
        })
    }

    // Delete entry
    const handleDeleteEntry = (id) => {
        setEntries(prev => {
            const updated = prev.filter(e => e.id !== id)
            triggerAutosave(updated, styling)
            return updated
        })
    }

    // Split entry into two at cursor position or midpoint
    const handleSplitEntry = (id, cursorPosition = null) => {
        const entryIdx = entries.findIndex(e => e.id === id)
        if (entryIdx === -1) return
        const entry = entries[entryIdx]
        const text = entry.text || ''

        const startSec = parseSrtTimeToSeconds(entry.start_time)
        const endSec = parseSrtTimeToSeconds(entry.end_time)
        const duration = Math.max(0.6, endSec - startSec)

        // Split text on a clean word boundary
        let splitIdx = -1
        if (cursorPosition !== null && cursorPosition > 0 && cursorPosition < text.length) {
            const nextSpace = text.indexOf(' ', cursorPosition)
            const prevSpace = text.lastIndexOf(' ', cursorPosition)

            if (nextSpace !== -1 && prevSpace !== -1) {
                splitIdx = (nextSpace - cursorPosition < cursorPosition - prevSpace) ? nextSpace : prevSpace
            } else if (nextSpace !== -1) {
                splitIdx = nextSpace
            } else if (prevSpace !== -1) {
                splitIdx = prevSpace
            }
        }

        // Fallback: split by words halfway
        if (splitIdx === -1) {
            const words = text.trim().split(/\s+/)
            if (words.length > 1) {
                const midWord = Math.ceil(words.length / 2)
                const part1 = words.slice(0, midWord).join(' ')
                splitIdx = part1.length
            }
        }

        let part1Text = text
        let part2Text = ''
        let ratio = 0.5

        if (splitIdx > 0 && splitIdx < text.length) {
            part1Text = text.slice(0, splitIdx).trim()
            part2Text = text.slice(splitIdx).trim()
            const totalChars = (part1Text.length + part2Text.length) || 1
            ratio = Math.max(0.2, Math.min(0.8, part1Text.length / totalChars))
        }

        part1Text = sanitizeHighlightTags(part1Text)
        part2Text = sanitizeHighlightTags(part2Text)

        const midSec = Math.max(startSec + 0.3, Math.min(endSec - 0.3, startSec + duration * ratio))
        const midTimeStr = formatSecondsToSrt(midSec)

        const newId = entries.length > 0 ? Math.max(...entries.map(e => e.id)) + 1 : 1

        const updatedEntry1 = {
            ...entry,
            end_time: midTimeStr,
            text: part1Text
        }

        const newEntry2 = {
            id: newId,
            start_time: midTimeStr,
            end_time: entry.end_time,
            text: part2Text
        }

        const updatedList = [
            ...entries.slice(0, entryIdx),
            updatedEntry1,
            newEntry2,
            ...entries.slice(entryIdx + 1)
        ]

        setEntries(updatedList)
        triggerAutosave(updatedList, styling)
    }

    // Merge entry with the next entry
    const handleMergeEntry = (id) => {
        const entryIdx = entries.findIndex(e => e.id === id)
        if (entryIdx === -1 || entryIdx >= entries.length - 1) return

        const currentEntry = entries[entryIdx]
        const nextEntry = entries[entryIdx + 1]

        const mergedText = sanitizeHighlightTags(`${currentEntry.text.trim()} ${nextEntry.text.trim()}`.trim())

        const mergedEntry = {
            ...currentEntry,
            end_time: nextEntry.end_time,
            text: mergedText
        }

        const updatedList = [
            ...entries.slice(0, entryIdx),
            mergedEntry,
            ...entries.slice(entryIdx + 2)
        ]

        setEntries(updatedList)
        triggerAutosave(updatedList, styling)
    }

    // Add new entry
    const handleAddEntry = () => {
        const last = entries[entries.length - 1]
        const newId = entries.length > 0 ? Math.max(...entries.map(e => e.id)) + 1 : 1

        const newEntry = {
            id: newId,
            start_time: last ? last.end_time : '00:00:00,000',
            end_time: last ? incrementSrtTime(last.end_time, 3) : '00:00:03,000',
            text: ''
        }

        const updated = [...entries, newEntry]
        setEntries(updated)
        triggerAutosave(updated, styling)

        // Seek video to new entry
        const startTime = parseSrtTimeToSeconds(newEntry.start_time)
        playerRef.current?.seekTo(startTime)
    }

    const incrementSrtTime = (srtTime, sec) => {
        const t = parseSrtTimeToSeconds(srtTime) + sec
        return formatSecondsToSrt(t)
    }

    // Update styling
    const handleUpdateStyling = (key, val) => {
        setStyling(prev => {
            const updated = { ...prev, [key]: val }
            triggerAutosave(entries, updated)
            return updated
        })
    }

    // Apply Preset
    const handleApplyPreset = (presetStyling) => {
        setStyling(prev => {
            const updated = { ...prev, ...presetStyling }
            triggerAutosave(entries, updated)
            return updated
        })
    }

    // Import SRT
    const handleImportSrt = async (e) => {
        const file = e.target.files?.[0]
        if (!file || !projectId) return
        try {
            const res = await api.importSubtitles(projectId, file)
            setEntries(res.entries || [])
            if (res.styling) setStyling(prev => ({ ...prev, ...res.styling }))
            setIsRenderDirty(true)
        } catch (err) {
            setError(err.message || 'Failed to import SRT')
        }
    }

    // Render Video
    const handleRenderVideo = async () => {
        if (!projectId) return
        // Flush any pending changes to backend
        await flushPendingAutosave(entries, styling)

        setStatus('rendering')
        setProgress(0)
        setError(null)

        try {
            await api.renderStandaloneVideo(projectId)
            startPolling(projectId)
        } catch (err) {
            setError(err.message || 'Render failed')
            setStatus('ready')
            autoDownloadOnFinishRef.current = false
        }
    }

    // Export Video: triggers render automatically if modified/not rendered, then downloads
    const handleExportVideo = async () => {
        setIsExportDropdownOpen(false)
        if (!projectId || status === 'rendering') return

        // If video is already rendered and no edits were made, download directly
        if (status === 'done' && !isRenderDirty && downloadVideoUrl) {
            triggerFileDownload(downloadVideoUrl, `${projectTitle || 'video'}.mp4`)
            return
        }

        // Otherwise automatically start render, and autoDownloadOnFinish will download when complete
        autoDownloadOnFinishRef.current = true
        await handleRenderVideo()
    }

    // Export SRT file
    const handleExportSrt = async () => {
        setIsExportDropdownOpen(false)
        if (!projectId) return
        await flushPendingAutosave(entries, styling)
        if (srtDownloadUrl) {
            triggerFileDownload(srtDownloadUrl, `${projectTitle || 'subtitles'}.srt`)
        }
    }

    // Keyboard Shortcuts (Space to play/pause, arrows to seek)
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (isUserTypingRef.current) return
            if (status !== 'ready' && status !== 'done') return

            if (e.code === 'Space') {
                e.preventDefault()
                const videoEl = playerRef.current?.getVideoElement()
                if (videoEl) {
                    if (videoEl.paused) videoEl.play()
                    else videoEl.pause()
                }
            } else if (e.code === 'ArrowLeft') {
                e.preventDefault()
                const videoEl = playerRef.current?.getVideoElement()
                if (videoEl) videoEl.currentTime = Math.max(0, videoEl.currentTime - 3)
            } else if (e.code === 'ArrowRight') {
                e.preventDefault()
                const videoEl = playerRef.current?.getVideoElement()
                if (videoEl) videoEl.currentTime = Math.min(videoEl.duration || 0, videoEl.currentTime + 3)
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [status])

    // Filtered entries for search
    const filteredEntries = entries.filter(e =>
        !searchQuery || e.text.toLowerCase().includes(searchQuery.toLowerCase())
    )

    // Download URLs
    const downloadVideoUrl = projectId ? api.getDownloadUrl(projectId) : null
    const srtDownloadUrl = projectId ? api.getSubtitleDownloadUrl(projectId) : null

    // ==================== VIEW 1: UPLOAD DROPZONE ====================
    if (status === 'idle' || (!videoUrl && status !== 'uploading' && status !== 'transcribing')) {
        return (
            <div className="subtitle-studio-root">
                <Header />
                <main className="studio-upload-screen">
                    <div className="upload-screen-hero">
                        <h1>{t('subtitles.heroTitle')}</h1>
                        <p>{t('subtitles.heroSubtitle')}</p>
                    </div>

                    <div
                        className="studio-dropzone"
                        onDrop={(e) => {
                            e.preventDefault()
                            e.currentTarget.classList.remove('drag-over')
                            const f = e.dataTransfer?.files[0]
                            if (f) handleFileSelect(f)
                        }}
                        onDragOver={(e) => { e.preventDefault(); e.currentTarget.classList.add('drag-over') }}
                        onDragLeave={(e) => { e.currentTarget.classList.remove('drag-over') }}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="video/*"
                            hidden
                            onChange={(e) => {
                                const f = e.target.files?.[0]
                                if (f) handleFileSelect(f)
                            }}
                        />
                        <div className="dropzone-icon">🎬</div>
                        <div className="dropzone-text">
                            <h2>{t('subtitles.dropzoneTitle')}</h2>
                            <p>{t('subtitles.dropzoneSubtitle')}</p>
                        </div>
                    </div>

                    <div className="upload-options-row">
                        <div className="upload-lang-picker">
                            <span>🌐 {t('subtitles.speechLanguage')}</span>
                            <select
                                value={selectedLanguage}
                                onChange={(e) => setSelectedLanguage(e.target.value)}
                            >
                                <option value="auto">{t('subtitles.langAuto')}</option>
                                <option value="be">{t('subtitles.langBe')}</option>
                                <option value="en">{t('subtitles.langEn')}</option>
                                <option value="ru">{t('subtitles.langRu')}</option>
                                <option value="uk">{t('subtitles.langUk')}</option>
                                <option value="pl">{t('subtitles.langPl')}</option>
                            </select>
                        </div>

                        <label className="btn-studio-secondary">
                            📄 {t('subtitles.haveSrt')}
                            <input
                                type="file"
                                accept=".srt"
                                hidden
                                onChange={handleImportSrt}
                            />
                        </label>
                    </div>

                    {error && (
                        <div className="error-message" style={{ marginTop: '20px' }}>
                            ⚠️ {error}
                            <button onClick={() => setError(null)}>×</button>
                        </div>
                    )}

                    {/* Recent Videos Section */}
                    {projectsList && projectsList.length > 0 && (
                        <div className="recent-videos-section">
                            <div className="recent-videos-header">
                                <h3>
                                    <span>📂</span>
                                    <span>{t('subtitles.recentVideos')}</span>
                                </h3>
                                <span style={{ fontSize: '12px', color: 'rgba(255,255,255,0.45)' }}>
                                    {t('subtitles.videoCount', { current: projectsList.length, total: projectsList.length })}
                                </span>
                            </div>
                            <div className="recent-videos-grid">
                                {projectsList.slice(0, 8).map((proj) => {
                                    const dateStr = proj.updated_at
                                        ? new Date(proj.updated_at).toLocaleDateString()
                                        : (proj.created_at ? new Date(proj.created_at).toLocaleDateString() : '')
                                    const isStandalone = Boolean(proj.standalone_mode)
                                    return (
                                        <div
                                            key={proj.id}
                                            className="recent-video-card"
                                            onClick={() => handleSwitchProject(proj.id)}
                                            title={proj.title || proj.id}
                                        >
                                            <div className="recent-card-top">
                                                <span className="recent-card-icon">{isStandalone ? '📝' : '🎬'}</span>
                                                <span className="recent-card-title">{proj.title || `Project ${proj.id.slice(0, 8)}`}</span>
                                            </div>
                                            <div className="recent-card-meta">
                                                <span className="recent-card-format">{proj.format || '9:16'}</span>
                                                <span className={`status-tag status-${(proj.status || '').toLowerCase()}`} style={{ fontSize: '10px' }}>
                                                    {proj.status === 'DONE' ? '✓ DONE' : (proj.status || 'READY')}
                                                </span>
                                                {dateStr && <span className="recent-card-date">{dateStr}</span>}
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>
                    )}
                </main>
            </div>
        )
    }

    // ==================== VIEW 2: TRANSCRIBING LOADER ====================
    if (status === 'uploading' || status === 'transcribing') {
        return (
            <div className="subtitle-studio-root">
                <Header />
                <main className="transcription-screen">
                    <div className="transcription-soundwave">
                        <div className="soundwave-bar"></div>
                        <div className="soundwave-bar"></div>
                        <div className="soundwave-bar"></div>
                        <div className="soundwave-bar"></div>
                        <div className="soundwave-bar"></div>
                        <div className="soundwave-bar"></div>
                    </div>

                    <h2>
                        {status === 'uploading' ? t('subtitles.uploadingTitle') : t('subtitles.transcribingTitle')}
                    </h2>
                    <p>
                        {status === 'uploading'
                            ? t('subtitles.uploadingDesc')
                            : t('subtitles.transcribingDesc')}
                    </p>

                    {status === 'transcribing' && (
                        <div className="transcription-timer">
                            ⏱️ {transcribingSeconds} {t('subtitles.card.secShort')}
                        </div>
                    )}

                    <button
                        className="btn-studio-secondary"
                        style={{ marginTop: '16px' }}
                        onClick={() => {
                            setStatus('ready')
                            if (transcribingTimerRef.current) clearInterval(transcribingTimerRef.current)
                        }}
                    >
                        {t('subtitles.skipToEditor')}
                    </button>
                </main>
            </div>
        )
    }

    // ==================== VIEW 3: FULL SUBTITLE STUDIO WORKSPACE ====================
    return (
        <div className="subtitle-studio-root">
            {/* Top Bar */}
            <header className="studio-top-bar">
                <div className="studio-top-left">
                    <button
                        type="button"
                        className="studio-brand-logo"
                        onClick={handleStartNewVideo}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                        title={t('subtitles.returnToDropzone')}
                    >
                        <span>🎬</span>
                        <span>{t('subtitles.title')}</span>
                    </button>

                    <div className="studio-project-nav-wrapper" ref={projectDropdownRef}>
                        {/* Interactive Project Title Badge */}
                        <div
                            className={`studio-project-title-badge clickable ${isDropdownOpen ? 'active' : ''}`}
                            role="button"
                            tabIndex={0}
                            aria-expanded={isDropdownOpen}
                            aria-haspopup="true"
                            onClick={() => setIsDropdownOpen(prev => !prev)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault()
                                    setIsDropdownOpen(prev => !prev)
                                }
                            }}
                            title={t('subtitles.switchVideo')}
                        >
                            <span className="project-title-text" title={projectTitle}>
                                {projectTitle}
                            </span>
                            <span className="project-format-tag">{format}</span>
                            <span className={`dropdown-caret ${isDropdownOpen ? 'open' : ''}`}>▼</span>
                        </div>

                        {/* Project Switcher Dropdown */}
                        {isDropdownOpen && (
                            <div className="studio-project-dropdown-menu">
                                <div className="dropdown-menu-header">
                                    <span className="dropdown-menu-title">📂 {t('subtitles.myVideos')}</span>
                                    <button
                                        type="button"
                                        className="dropdown-footer-btn"
                                        onClick={() => setIsDropdownOpen(false)}
                                        style={{ fontSize: '13px', padding: '2px 6px' }}
                                    >
                                        ✕
                                    </button>
                                </div>

                                <div className="dropdown-search-wrapper">
                                    <input
                                        type="text"
                                        className="dropdown-search-input"
                                        placeholder={t('subtitles.searchVideosPlaceholder')}
                                        value={projectSearchQuery}
                                        onChange={(e) => setProjectSearchQuery(e.target.value)}
                                        autoFocus
                                    />
                                </div>

                                <div className="dropdown-project-list">
                                    {projectsList
                                        .filter(p => !projectSearchQuery || (p.title || p.id).toLowerCase().includes(projectSearchQuery.toLowerCase()))
                                        .map(proj => {
                                            const isActive = proj.id === projectId
                                            const dateStr = proj.updated_at
                                                ? new Date(proj.updated_at).toLocaleDateString()
                                                : (proj.created_at ? new Date(proj.created_at).toLocaleDateString() : '')
                                            return (
                                                <button
                                                    key={proj.id}
                                                    type="button"
                                                    className={`dropdown-project-item ${isActive ? 'active' : ''}`}
                                                    onClick={() => handleSwitchProject(proj.id)}
                                                >
                                                    <span className="dropdown-item-icon">{proj.standalone_mode ? '📝' : '🎬'}</span>
                                                    <div className="dropdown-item-info">
                                                        <span className="dropdown-item-title">{proj.title || proj.id.slice(0, 8)}</span>
                                                        <div className="dropdown-item-meta">
                                                            <span className="dropdown-item-badge">{proj.format || '9:16'}</span>
                                                            <span>{proj.status === 'DONE' ? '✓ DONE' : (proj.status || '')}</span>
                                                            {dateStr && <span>• {dateStr}</span>}
                                                        </div>
                                                    </div>
                                                    {isActive && <span className="dropdown-item-check">✓</span>}
                                                </button>
                                            )
                                        })}
                                    {projectsList.length === 0 && (
                                        <div className="dropdown-empty-hint">
                                            {t('subtitles.noRecentVideos')}
                                        </div>
                                    )}
                                </div>

                                <div className="dropdown-menu-footer">
                                    <button
                                        type="button"
                                        className="dropdown-footer-btn"
                                        onClick={handleStartNewVideo}
                                        style={{ color: '#a5b4fc', fontWeight: 700 }}
                                    >
                                        ➕ {t('subtitles.newVideo')}
                                    </button>
                                    <Link
                                        to="/cabinet"
                                        className="dropdown-footer-btn"
                                        onClick={() => setIsDropdownOpen(false)}
                                    >
                                        {t('subtitles.allProjectsInCabinet')} →
                                    </Link>
                                </div>
                            </div>
                        )}

                        {/* Direct Button: + New Video */}
                        <button
                            type="button"
                            className="btn-studio-new-video"
                            onClick={handleStartNewVideo}
                            title={t('subtitles.newVideo')}
                        >
                            <span>➕</span>
                            <span>{t('subtitles.newVideo')}</span>
                        </button>
                    </div>

                    <div className={`autosave-indicator ${autosaveStatus}`}>
                        {autosaveStatus === 'saving' ? `⏳ ${t('subtitles.autosaveSaving')}` : `✓ ${t('subtitles.autosaveSaved')}`}
                    </div>
                </div>

                <div className="studio-top-right">
                    {/* Unified Export Dropdown */}
                    <div className="studio-export-wrapper" ref={exportDropdownRef}>
                        <button
                            type="button"
                            className={`btn-studio-export ${isExportDropdownOpen ? 'active' : ''}`}
                            onClick={() => {
                                if (status === 'rendering') return
                                setIsExportDropdownOpen(prev => !prev)
                            }}
                            disabled={status === 'rendering'}
                            title={t('subtitles.exportMenu')}
                        >
                            {status === 'rendering' ? (
                                <>⏳ {t('subtitles.rendering', { progress })}</>
                            ) : (
                                <>
                                    <span>🚀</span>
                                    <span>{t('subtitles.exportMenu')}</span>
                                    <span className={`dropdown-caret ${isExportDropdownOpen ? 'open' : ''}`}>▼</span>
                                </>
                            )}
                        </button>

                        {isExportDropdownOpen && (
                            <div className="studio-export-dropdown-menu">
                                <button
                                    type="button"
                                    className="export-dropdown-item"
                                    onClick={handleExportVideo}
                                >
                                    <span className="export-item-icon">🎬</span>
                                    <div className="export-item-info">
                                        <span className="export-item-title">{t('subtitles.exportVideo')}</span>
                                        <span className="export-item-desc">
                                            {status === 'done' && !isRenderDirty
                                                ? `✓ ${t('subtitles.exportVideoReadyDesc')}`
                                                : `⚡ ${t('subtitles.exportVideoDesc')}`}
                                        </span>
                                    </div>
                                    {status === 'done' && !isRenderDirty && (
                                        <span className="export-item-badge">MP4</span>
                                    )}
                                </button>

                                {srtDownloadUrl && (
                                    <button
                                        type="button"
                                        className="export-dropdown-item"
                                        onClick={handleExportSrt}
                                    >
                                        <span className="export-item-icon">📄</span>
                                        <div className="export-item-info">
                                            <span className="export-item-title">{t('subtitles.exportSrt')}</span>
                                            <span className="export-item-desc">{t('subtitles.exportSrtDesc')}</span>
                                        </div>
                                        <span className="export-item-badge">SRT</span>
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
            </header>

            {error && (
                <div className="error-message" style={{ margin: '14px 28px 0', borderRadius: '8px' }}>
                    ⚠️ {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}

            {/* Studio Body: Split View */}
            <div className="studio-workspace">
                {/* Left Panel: Sidebar (Tabs: Captions, Styling, Presets) */}
                <aside className="studio-sidebar">
                    <div className="studio-sidebar-tabs">
                        <button
                            className={`studio-tab-btn ${activeTab === 'captions' ? 'active' : ''}`}
                            onClick={() => setActiveTab('captions')}
                        >
                            <span>📝</span>
                            <span>{t('subtitles.tabs.captions', { count: entries.length })}</span>
                        </button>
                        <button
                            className={`studio-tab-btn ${activeTab === 'styling' ? 'active' : ''}`}
                            onClick={() => setActiveTab('styling')}
                        >
                            <span>🎨</span>
                            <span>{t('subtitles.tabs.styling')}</span>
                        </button>
                        <button
                            className={`studio-tab-btn ${activeTab === 'presets' ? 'active' : ''}`}
                            onClick={() => setActiveTab('presets')}
                        >
                            <span>⚡</span>
                            <span>{t('subtitles.tabs.presets')}</span>
                        </button>
                    </div>

                    <div className="studio-sidebar-content" ref={entriesListRef}>
                        {/* TAB 1: CAPTIONS */}
                        {activeTab === 'captions' && (
                            <>
                                <div className="captions-toolbar">
                                    <div className="captions-search-box">
                                        <span className="search-icon-placeholder">🔍</span>
                                        <input
                                            type="text"
                                            placeholder={t('subtitles.searchPlaceholder')}
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                        />
                                    </div>
                                    <button
                                        className="btn-add-caption"
                                        onClick={handleAddEntry}
                                    >
                                        {t('subtitles.addCaption')}
                                    </button>
                                </div>

                                {filteredEntries.length === 0 ? (
                                    <div className="no-entries" style={{ padding: '30px 10px', textAlign: 'center' }}>
                                        <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: '13px' }}>
                                            {t('subtitles.noEntries')}
                                        </p>
                                        <button
                                            className="btn-studio-secondary"
                                            style={{ margin: '12px auto' }}
                                            onClick={handleTranscribeAgain}
                                        >
                                            🎤 {t('subtitles.transcribeAgain')}
                                        </button>
                                    </div>
                                ) : (
                                    <div className="captions-list">
                                        {filteredEntries.map((entry, idx) => {
                                            const isActive = entry.id === activeEntryId
                                            const originalIdx = entries.findIndex(e => e.id === entry.id)
                                            const hasNext = originalIdx !== -1 && originalIdx < entries.length - 1
                                            return (
                                                <SubtitleEntryCard
                                                    key={entry.id}
                                                    entry={entry}
                                                    idx={originalIdx !== -1 ? originalIdx : idx}
                                                    isActive={isActive}
                                                    styling={styling}
                                                    onUpdate={handleUpdateEntry}
                                                    onDelete={handleDeleteEntry}
                                                    onSeek={(time) => playerRef.current?.seekTo(time)}
                                                    onSplit={handleSplitEntry}
                                                    onMergeNext={handleMergeEntry}
                                                    hasNext={hasNext}
                                                    isUserTypingRef={isUserTypingRef}
                                                />
                                            )
                                        })}
                                    </div>
                                )}
                            </>
                        )}

                        {/* TAB 2: STYLING */}
                        {activeTab === 'styling' && (
                            <>
                                <div className="style-accordion-section">
                                    <h4 className="style-accordion-title">{t('subtitles.fontAndText')}</h4>
                                    <div className="style-control-row">
                                        <label>{t('subtitles.fontFamily')}</label>
                                        <select
                                            value={styling.font_family}
                                            onChange={(e) => handleUpdateStyling('font_family', e.target.value)}
                                        >
                                            {Object.entries(FONT_CATEGORIES).map(([cat, fonts]) => (
                                                <optgroup key={cat} label={cat}>
                                                    {fonts.map(f => (
                                                        <option key={f} value={f}>{f}</option>
                                                    ))}
                                                </optgroup>
                                            ))}
                                        </select>
                                    </div>

                                    <div className="style-control-row">
                                        <div className="style-label-group">
                                            <label>{t('subtitles.fontSize')}</label>
                                            <span className="slider-badge">{styling.font_size}px</span>
                                        </div>
                                        <input
                                            type="range"
                                            min="18"
                                            max="96"
                                            value={styling.font_size}
                                            onChange={(e) => handleUpdateStyling('font_size', parseInt(e.target.value))}
                                        />
                                    </div>

                                    <div className="style-control-row">
                                        <label>{t('subtitles.fontWeight')}</label>
                                        <select
                                            value={styling.font_weight}
                                            onChange={(e) => handleUpdateStyling('font_weight', e.target.value)}
                                        >
                                            <option value="normal">{t('subtitles.weightNormal')}</option>
                                            <option value="bold">{t('subtitles.weightBold')}</option>
                                            <option value="900">{t('subtitles.weightBlack')}</option>
                                        </select>
                                    </div>

                                    <div className="style-control-row checkbox-row">
                                        <input
                                            type="checkbox"
                                            id="uppercase_check"
                                            checked={styling.uppercase}
                                            onChange={(e) => handleUpdateStyling('uppercase', e.target.checked)}
                                        />
                                        <label htmlFor="uppercase_check">{t('subtitles.uppercase')}</label>
                                    </div>
                                </div>

                                <div className="style-accordion-section">
                                    <h4 className="style-accordion-title">{t('subtitles.colorsAndStroke')}</h4>
                                    <div className="style-control-row">
                                        <label>{t('subtitles.textColor')}</label>
                                        <input
                                            type="color"
                                            value={styling.font_color}
                                            onChange={(e) => handleUpdateStyling('font_color', e.target.value)}
                                        />
                                    </div>

                                    <div className="style-control-row">
                                        <label>{t('subtitles.strokeColor')}</label>
                                        <input
                                            type="color"
                                            value={styling.stroke_color}
                                            onChange={(e) => handleUpdateStyling('stroke_color', e.target.value)}
                                        />
                                    </div>

                                    <div className="style-control-row">
                                        <div className="style-label-group">
                                            <label>{t('subtitles.strokeWidth')}</label>
                                            <span className="slider-badge">{styling.stroke_width}px</span>
                                        </div>
                                        <input
                                            type="range"
                                            min="0"
                                            max="10"
                                            value={styling.stroke_width}
                                            onChange={(e) => handleUpdateStyling('stroke_width', parseInt(e.target.value))}
                                        />
                                    </div>
                                </div>

                                <div className="style-accordion-section">
                                    <h4 className="style-accordion-title">{t('subtitles.backgroundPlate')}</h4>
                                    <div className="style-control-row checkbox-row">
                                        <input
                                            type="checkbox"
                                            id="bg_enable_check"
                                            checked={styling.background_enabled}
                                            onChange={(e) => handleUpdateStyling('background_enabled', e.target.checked)}
                                        />
                                        <label htmlFor="bg_enable_check">{t('subtitles.enableBackground')}</label>
                                    </div>

                                    {styling.background_enabled && (
                                        <>
                                            <div className="style-control-row">
                                                <label>{t('subtitles.backgroundColor')}</label>
                                                <input
                                                    type="color"
                                                    value={styling.background_color}
                                                    onChange={(e) => handleUpdateStyling('background_color', e.target.value)}
                                                />
                                            </div>
                                            <div className="style-control-row">
                                                <div className="style-label-group">
                                                    <label>{t('subtitles.opacity')}</label>
                                                    <span className="slider-badge">{Math.round(styling.background_opacity * 100)}%</span>
                                                </div>
                                                <input
                                                    type="range"
                                                    min="0"
                                                    max="100"
                                                    value={styling.background_opacity * 100}
                                                    onChange={(e) => handleUpdateStyling('background_opacity', parseInt(e.target.value) / 100)}
                                                />
                                            </div>
                                        </>
                                    )}
                                </div>

                                <div className="style-accordion-section">
                                    <h4 className="style-accordion-title">{t('subtitles.positioning')}</h4>
                                    <div className="style-control-row">
                                        <label>{t('subtitles.position')}</label>
                                        <select
                                            value={styling.position}
                                            onChange={(e) => handleUpdateStyling('position', e.target.value)}
                                        >
                                            <option value="bottom">{t('subtitles.posBottom')}</option>
                                            <option value="middle">{t('subtitles.posMiddle')}</option>
                                            <option value="top">{t('subtitles.posTop')}</option>
                                        </select>
                                    </div>

                                    <div className="style-control-row">
                                        <div className="style-label-group">
                                            <label>{t('subtitles.marginY')}</label>
                                            <span className="slider-badge">{styling.margin_y}px</span>
                                        </div>
                                        <input
                                            type="range"
                                            min="0"
                                            max="250"
                                            value={styling.margin_y}
                                            onChange={(e) => handleUpdateStyling('margin_y', parseInt(e.target.value))}
                                        />
                                    </div>
                                </div>

                                <div className="style-accordion-section">
                                    <h4 className="style-accordion-title">{t('subtitles.karaokeAndAnimation')}</h4>
                                    <div className="style-control-row checkbox-row">
                                        <input
                                            type="checkbox"
                                            id="karaoke_enable_check"
                                            checked={Boolean(styling.highlight_active_word)}
                                            onChange={(e) => handleUpdateStyling('highlight_active_word', e.target.checked)}
                                        />
                                        <label htmlFor="karaoke_enable_check">{t('subtitles.karaokeHighlight')}</label>
                                    </div>

                                    {styling.highlight_active_word && (
                                        <div className="style-control-row">
                                            <label>{t('subtitles.badgeColor')}</label>
                                            <input
                                                type="color"
                                                value={styling.highlight_bg_color || '#FF0000'}
                                                onChange={(e) => handleUpdateStyling('highlight_bg_color', e.target.value)}
                                            />
                                        </div>
                                    )}
                                </div>
                            </>
                        )}

                        {/* TAB 3: PRESETS */}
                        {activeTab === 'presets' && (
                            <SubtitlePresetsGallery
                                currentStyling={styling}
                                onApplyPreset={handleApplyPreset}
                            />
                        )}
                    </div>
                </aside>

                {/* Right Stage: Maximized Video Player & Timeline */}
                <main className="studio-stage">
                    {/* Centered Video Player Box - Maximized Live Preview */}
                    <div className="studio-player-box">
                        <SubtitleVideoPlayer
                            key={`preview-${projectId}-${videoUrl}`}
                            ref={playerRef}
                            videoUrl={videoUrl}
                            entries={entries}
                            styling={styling}
                            format={format}
                            isRendered={false}
                            badgeText={null}
                            onTimeChange={handleTimeUpdate}
                            onDurationChange={setDuration}
                        />
                    </div>

                    {/* Timeline */}
                    <div className="studio-timeline-wrapper">
                        <SubtitleTimeline
                            currentTime={currentTime}
                            duration={duration || playerRef.current?.getVideoElement()?.duration || 0}
                            entries={entries}
                            activeEntryId={activeEntryId}
                            onSeek={(targetSec) => {
                                playerRef.current?.seekTo(targetSec)
                            }}
                            onSelectEntry={(entry) => {
                                setActiveEntryId(entry.id)
                            }}
                        />
                    </div>
                </main>
            </div>
        </div>
    )
}
