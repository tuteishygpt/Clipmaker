import { useState, useRef, useCallback, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import Header from './Header'
import SubtitleEditor from './SubtitleEditor'
import './SubtitleStandalonePage.css'
import * as api from '../api'
import { useProjectStore } from '../stores/projectStore'

export default function SubtitleStandalonePage() {
    const [searchParams] = useSearchParams()
    const projectIdParam = searchParams.get('project')

    const [videoFile, setVideoFile] = useState(null)
    const [videoUrl, setVideoUrl] = useState(null)
    const [projectId, setProjectId] = useState(null)
    const [status, setStatus] = useState('idle') // idle, loading, uploading, processing, ready, rendering, done, error
    const [error, setError] = useState(null)
    const [progress, setProgress] = useState(0)
    const [outputUrl, setOutputUrl] = useState(null)
    const [showEditor, setShowEditor] = useState(false)
    const [subtitleUrl, setSubtitleUrl] = useState(null)
    const [format, setFormat] = useState('9:16')
    const fileInputRef = useRef(null)
    const pollTimerRef = useRef(null)

    // Helper to start polling render progress
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
                    setOutputUrl(api.getDownloadUrl(id))
                } else if (renderJob?.status === 'ERROR') {
                    clearInterval(pollTimerRef.current)
                    pollTimerRef.current = null
                    setError(renderJob.message || 'Render failed')
                    setStatus('error')
                } else if (renderJob?.progress !== undefined) {
                    setProgress(renderJob.progress)
                }
            } catch (err) {
                console.error('Polling error:', err)
            }
        }, 1000)
    }, [])

    // Clean up timer on unmount
    useEffect(() => {
        return () => {
            if (pollTimerRef.current) {
                clearInterval(pollTimerRef.current)
                pollTimerRef.current = null
            }
        }
    }, [])

    // Open existing project if ?project=<id> is present in URL
    useEffect(() => {
        if (!projectIdParam) return

        let isCancelled = false

        const loadExistingProject = async () => {
            setStatus('loading')
            setError(null)
            try {
                const proj = await api.getProject(projectIdParam)
                if (isCancelled) return

                setProjectId(proj.id)
                setFormat(proj.format || '9:16')
                setVideoUrl(api.getVideoUrl(proj.id))

                // Check jobs status to resume rendering or show done
                try {
                    const jobsData = await api.getJobs(proj.id)
                    const renderJob = jobsData.jobs?.render

                    if (renderJob?.status === 'DONE') {
                        setStatus('done')
                        setOutputUrl(api.getDownloadUrl(proj.id))
                    } else if (renderJob?.status === 'RUNNING') {
                        setStatus('rendering')
                        setProgress(renderJob.progress || 0)
                        startPolling(proj.id)
                    } else {
                        setStatus('ready')
                    }
                } catch (_) {
                    setStatus('ready')
                }
            } catch (err) {
                if (!isCancelled) {
                    console.error('Failed to load existing project:', err)
                    setError('Failed to load project: ' + err.message)
                    setStatus('error')
                }
            }
        }

        loadExistingProject()

        return () => {
            isCancelled = true
        }
    }, [projectIdParam, startPolling])

    // Load subtitles for preview
    const loadSubtitles = useCallback(async () => {
        if (!projectId) return
        try {
            const data = await api.getSubtitles(projectId)
            const entries = data.entries || []

            if (entries.length === 0) {
                setSubtitleUrl(null)
                return
            }

            // Convert to WebVTT format for <track>
            const vttContent = "WEBVTT\n\n" + entries.map(e => {
                // Start and end times: Replace comma with dot (SRT -> VTT)
                const start = e.start_time.replace(',', '.')
                const end = e.end_time.replace(',', '.')
                return `${start} --> ${end}\n${e.text}`
            }).join('\n\n')

            const blob = new Blob([vttContent], { type: 'text/vtt' })
            const url = URL.createObjectURL(blob)
            setSubtitleUrl(url)
        } catch (err) {
            console.error("Failed to load subtitles for preview:", err)
        }
    }, [projectId])

    // Revoke object URLs on change or unmount to avoid memory leaks
    useEffect(() => {
        return () => {
            if (videoUrl && videoUrl.startsWith('blob:')) {
                URL.revokeObjectURL(videoUrl)
            }
        }
    }, [videoUrl])

    useEffect(() => {
        return () => {
            if (subtitleUrl && subtitleUrl.startsWith('blob:')) {
                URL.revokeObjectURL(subtitleUrl)
            }
        }
    }, [subtitleUrl])

    // Reload subtitles when editor closes or status becomes ready
    useEffect(() => {
        if (status === 'ready' && !showEditor) {
            loadSubtitles()
        }
    }, [status, showEditor, loadSubtitles])

    const getVideoMetadata = (file) => {
        return new Promise((resolve) => {
            const video = document.createElement('video');
            video.preload = 'metadata';
            const url = URL.createObjectURL(file);
            video.onloadedmetadata = () => {
                const data = {
                    width: video.videoWidth,
                    height: video.videoHeight,
                    duration: video.duration
                };
                URL.revokeObjectURL(url);
                resolve(data);
            };
            video.onerror = () => {
                URL.revokeObjectURL(url);
                resolve({ width: 0, height: 0, duration: 0 });
            };
            video.src = url;
        });
    };

    const handleFileDrop = useCallback(async (e) => {
        e.preventDefault()
        e.currentTarget?.classList?.remove('drag-over')
        const file = e.dataTransfer?.files[0] || e.target?.files[0]

        if (file && file.type.startsWith('video/')) {
            setError(null)
            const meta = await getVideoMetadata(file)
            if (meta.duration && meta.duration > 900) {
                const mins = Math.floor(meta.duration / 60)
                const secs = Math.round(meta.duration % 60)
                setError(`⚠️ Video is too long (${mins}m ${secs}s). Maximum allowed limit is 15 minutes.`)
                return
            }
            setVideoFile(file)
            setVideoUrl(URL.createObjectURL(file))
            setOutputUrl(null)
            setProjectId(null)
            setStatus('idle')
        } else {
            setError('Please upload a valid video file')
        }
    }, [])

    const handleDragOver = (e) => {
        e.preventDefault()
        e.currentTarget.classList.add('drag-over')
    }

    const handleDragLeave = (e) => {
        e.currentTarget.classList.remove('drag-over')
    }

    const uploadVideo = async () => {
        if (!videoFile) return

        setStatus('uploading')
        setError(null)
        setProgress(0)

        try {
            // Detect format & duration
            const meta = await getVideoMetadata(videoFile)
            if (meta.duration && meta.duration > 900) {
                const mins = Math.floor(meta.duration / 60)
                const secs = Math.round(meta.duration % 60)
                throw new Error(`Video is too long (${mins}m ${secs}s). Maximum allowed limit is 15 minutes.`)
            }

            const isHorizontal = meta.width > meta.height
            const detectedFormat = isHorizontal ? '16:9' : '9:16'
            setFormat(detectedFormat)

            // Create a standalone project preserving the video filename
            const project = await api.createProject({
                title: videoFile.name,
                format: detectedFormat,
                style: 'default',
                standalone_mode: true
            })

            const id = project.id
            setProjectId(id)

            // Upload video as source
            await api.uploadVideoStandalone(id, videoFile)

            // Refresh project store
            useProjectStore.getState().loadProjects()

            setStatus('ready')
            setShowEditor(true)

        } catch (err) {
            setError(err.message)
            setStatus('error')
        }
    }

    const renderWithSubtitles = async () => {
        if (!projectId) return

        setStatus('rendering')
        setProgress(0)
        setError(null)

        try {
            await api.renderStandaloneVideo(projectId)
            startPolling(projectId)
        } catch (err) {
            setError(err.message)
            setStatus('error')
        }
    }

    return (
        <div className="standalone-page">
            <Header />

            <main className="standalone-main">
                <div className="standalone-hero">
                    <h1>Add Subtitles to Your Video</h1>
                    <p>Upload a video, generate or import subtitles, and download with burned-in captions</p>
                </div>

                <div className="standalone-content">
                    {/* Upload Zone */}
                    {!videoUrl && (
                        <div
                            className="upload-zone"
                            onDrop={handleFileDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                            onClick={() => fileInputRef.current?.click()}
                        >
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept="video/*"
                                hidden
                                onChange={handleFileDrop}
                            />
                            <div className="upload-icon">🎬</div>
                            <h2>Drop your video here</h2>
                            <p>or click to browse</p>
                            <span className="upload-formats">MP4, MOV, WebM, AVI supported</span>
                        </div>
                    )}

                    {/* Video Preview */}
                    {videoUrl && (
                        <div className="video-preview-section">
                            <div className="video-container">
                                <video
                                    src={videoUrl}
                                    controls
                                    className="standalone-video-player"
                                >
                                    {subtitleUrl && (
                                        <track
                                            kind="subtitles"
                                            src={subtitleUrl}
                                            srcLang="en"
                                            label="English"
                                            default
                                        />
                                    )}
                                </video>
                            </div>

                            <div className="video-actions">
                                {status === 'loading' && (
                                    <div className="status-message">
                                        <div className="spinner"></div>
                                        <span>Loading project...</span>
                                    </div>
                                )}

                                {status === 'idle' && (
                                    <>
                                        <button className="btn-primary" onClick={uploadVideo}>
                                            📤 Upload & Start
                                        </button>
                                        <button
                                            className="btn-secondary"
                                            onClick={() => {
                                                setVideoFile(null)
                                                setVideoUrl(null)
                                            }}
                                        >
                                            ✕ Choose Different Video
                                        </button>
                                    </>
                                )}

                                {status === 'uploading' && (
                                    <div className="status-message">
                                        <div className="spinner"></div>
                                        <span>Uploading video...</span>
                                    </div>
                                )}

                                {status === 'ready' && (
                                    <>
                                        <button
                                            className="btn-primary"
                                            onClick={() => setShowEditor(true)}
                                        >
                                            📝 Edit Subtitles
                                        </button>
                                        <button
                                            className="btn-accent"
                                            onClick={renderWithSubtitles}
                                        >
                                            🎬 Render with Subtitles
                                        </button>
                                    </>
                                )}

                                {status === 'rendering' && (
                                    <div className="status-message">
                                        <div className="progress-bar">
                                            <div
                                                className="progress-fill"
                                                style={{ width: `${progress}%` }}
                                            />
                                        </div>
                                        <span>Rendering... {progress}%</span>
                                    </div>
                                )}

                                {status === 'done' && outputUrl && (
                                    <div className="done-section">
                                        <div className="success-icon">✅</div>
                                        <h3>Your video is ready!</h3>
                                        <a
                                            href={outputUrl}
                                            download
                                            className="btn-download"
                                        >
                                            ⬇️ Download Video
                                        </a>
                                        <button
                                            className="btn-secondary"
                                            onClick={() => {
                                                setVideoFile(null)
                                                setVideoUrl(null)
                                                setProjectId(null)
                                                setStatus('idle')
                                                setOutputUrl(null)
                                            }}
                                        >
                                            Process Another Video
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {error && (
                        <div className="error-message">
                            ⚠️ {error}
                            <button onClick={() => setError(null)}>×</button>
                        </div>
                    )}
                </div>

                {/* Features Section */}
                <div className="features-section">
                    <div className="feature">
                        <span className="feature-icon">🎤</span>
                        <h3>AI Transcription</h3>
                        <p>Generate subtitles automatically using Gemini 3.0 Flash</p>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">📄</span>
                        <h3>Import SRT</h3>
                        <p>Upload your existing subtitle files</p>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">🎨</span>
                        <h3>60+ Fonts</h3>
                        <p>Style your subtitles with professional fonts</p>
                    </div>
                    <div className="feature">
                        <span className="feature-icon">✨</span>
                        <h3>Animations</h3>
                        <p>Add fade, pop, or karaoke effects</p>
                    </div>
                </div>
            </main>

            {/* Subtitle Editor Modal */}
            {showEditor && projectId && (
                <>
                    <div
                        className="subtitle-editor-overlay"
                        onClick={() => setShowEditor(false)}
                    />
                    <SubtitleEditor
                        projectId={projectId}
                        format={format}
                        onClose={() => setShowEditor(false)}
                    />
                </>
            )}
        </div>
    )
}
