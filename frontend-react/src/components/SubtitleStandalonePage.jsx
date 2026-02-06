import { useState, useRef, useCallback } from 'react'
import Header from './Header'
import SubtitleEditor from './SubtitleEditor'
import './SubtitleStandalonePage.css'

import { BASE_URL as API_BASE } from '../api'

export default function SubtitleStandalonePage() {
    const [videoFile, setVideoFile] = useState(null)
    const [videoUrl, setVideoUrl] = useState(null)
    const [projectId, setProjectId] = useState(null)
    const [status, setStatus] = useState('idle') // idle, uploading, processing, ready, rendering, done, error
    const [error, setError] = useState(null)
    const [progress, setProgress] = useState(0)
    const [outputUrl, setOutputUrl] = useState(null)
    const [showEditor, setShowEditor] = useState(false)
    const [subtitleUrl, setSubtitleUrl] = useState(null)
    const [format, setFormat] = useState('9:16')
    const fileInputRef = useRef(null)

    // Load subtitles for preview
    const loadSubtitles = useCallback(async () => {
        if (!projectId) return
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`)
            if (res.ok) {
                const data = await res.json()
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
            }
        } catch (err) {
            console.error("Failed to load subtitles for preview:", err)
        }
    }, [projectId])

    // Reload subtitles when editor closes or status becomes ready
    useEffect(() => {
        if (status === 'ready' && !showEditor) {
            loadSubtitles()
        }
    }, [status, showEditor, loadSubtitles])

    const handleFileDrop = useCallback((e) => {
        e.preventDefault()
        const file = e.dataTransfer?.files[0] || e.target?.files[0]

        if (file && file.type.startsWith('video/')) {
            setVideoFile(file)
            setVideoUrl(URL.createObjectURL(file))
            setError(null)
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

    const getVideoDimensions = (file) => {
        return new Promise((resolve) => {
            const video = document.createElement('video');
            video.preload = 'metadata';
            video.onloadedmetadata = () => {
                resolve({ width: video.videoWidth, height: video.videoHeight });
            };
            video.onerror = () => resolve({ width: 0, height: 0 }); // Fallback
            video.src = URL.createObjectURL(file);
        });
    };

    const uploadVideo = async () => {
        if (!videoFile) return

        setStatus('uploading')
        setError(null)
        setProgress(0)

        try {
            // Detect format
            const dim = await getVideoDimensions(videoFile)
            const isHorizontal = dim.width > dim.height
            const detectedFormat = isHorizontal ? '16:9' : '9:16'
            setFormat(detectedFormat)

            // Create a standalone project for subtitles
            const createRes = await fetch(`${API_BASE}/projects`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: 'Standalone Subtitles',
                    format: detectedFormat,
                    style: 'default'
                })
            })

            if (!createRes.ok) throw new Error('Failed to create project')
            const { id } = await createRes.json()
            setProjectId(id)

            // Upload video as source
            const formData = new FormData()
            formData.append('video', videoFile)

            const uploadRes = await fetch(`${API_BASE}/projects/${id}/upload-video`, {
                method: 'POST',
                body: formData
            })

            if (!uploadRes.ok) throw new Error('Failed to upload video')

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

        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/render-standalone`, {
                method: 'POST'
            })

            if (!res.ok) throw new Error('Render failed')

            // Poll for completion
            const pollRender = async () => {
                const jobsRes = await fetch(`${API_BASE}/projects/${projectId}/jobs`)
                const { jobs } = await jobsRes.json()

                if (jobs.render?.status === 'DONE') {
                    setStatus('done')
                    setOutputUrl(`${API_BASE}/projects/${projectId}/download`)
                } else if (jobs.render?.status === 'ERROR') {
                    throw new Error(jobs.render.message || 'Render failed')
                } else {
                    setProgress(jobs.render?.progress || 0)
                    setTimeout(pollRender, 1000)
                }
            }

            setTimeout(pollRender, 1000)

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
