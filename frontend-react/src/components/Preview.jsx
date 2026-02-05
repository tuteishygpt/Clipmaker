import { useRef, useEffect, useState, useCallback } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { getDownloadUrl } from '../api'
import { fixImageUrl } from '../utils'
import Timeline from './Timeline'
import AnalysisVisualization from './AnalysisVisualization'

/**
 * Generates text-shadow CSS that mimics PILlow's stroke rendering.
 * PILlow draws stroke by rendering text at multiple offsets in a circular pattern.
 * This function creates similar effect with CSS text-shadow.
 */
function generateStrokeShadow(strokeWidth, strokeColor, scaleFactor) {
    if (strokeWidth <= 0) return 'none'

    const scaledWidth = strokeWidth * scaleFactor
    const shadows = []

    // PILlow uses circular pattern: for dx,dy in range where dx²+dy² <= radius²
    // We approximate this with 8 cardinal + 8 diagonal directions for smooth stroke
    const steps = Math.max(8, Math.ceil(scaledWidth * 4))

    for (let i = 0; i < steps; i++) {
        const angle = (2 * Math.PI * i) / steps
        const x = Math.cos(angle) * scaledWidth
        const y = Math.sin(angle) * scaledWidth
        shadows.push(`${x.toFixed(1)}px ${y.toFixed(1)}px 0 ${strokeColor}`)
    }

    // Add extra layer for thicker strokes
    if (scaledWidth > 1) {
        const innerWidth = scaledWidth * 0.6
        for (let i = 0; i < steps / 2; i++) {
            const angle = (2 * Math.PI * i) / (steps / 2)
            const x = Math.cos(angle) * innerWidth
            const y = Math.sin(angle) * innerWidth
            shadows.push(`${x.toFixed(1)}px ${y.toFixed(1)}px 0 ${strokeColor}`)
        }
    }

    return shadows.join(', ')
}

/**
 * Parses text for <h>...</h> tags and renders them with highlight styling.
 * Also supports active word highlighting based on progress.
 */
function renderSubtitleWithHighlights(text, styling, scaleFactor, progress = -1) {
    if (!text) return null

    // Explicit <h> tags take precedence
    if (text.includes('<h>')) {
        // Regex to split by <h>...</h>
        const parts = text.split(/(<h>.*?<\/h>)/g)

        return parts.map((part, i) => {
            if (part.startsWith('<h>') && part.endsWith('</h>')) {
                const content = part.slice(3, -4)
                const padding = Math.round((styling.highlight_bg_padding || 0) * scaleFactor)
                return (
                    <span key={i} style={{
                        backgroundColor: styling.highlight_bg_color,
                        color: styling.highlight_font_color,
                        padding: `${padding}px`,
                        borderRadius: `${Math.round((styling.highlight_bg_radius || 0) * scaleFactor)}px`,
                        textShadow: 'none',
                        WebkitBoxDecorationBreak: 'clone',
                        boxDecorationBreak: 'clone',
                        position: 'relative',
                        zIndex: 1
                    }}>
                        {content}
                    </span>
                )
            }
            return part
        })
    }

    // Active Word (Karaoke) logic with whitespace preservation
    if (styling.highlight_active_word && progress >= 0) {
        // Split by whitespace capturing group to preserve spaces and newlines
        const tokens = text.split(/(\s+)/);

        // Count actual words to determine active index
        const wordTokens = tokens.filter(t => t.trim().length > 0);
        const totalWords = wordTokens.length;
        const activeIndex = Math.min(Math.floor(progress * totalWords), totalWords - 1);

        let currentWordIndex = 0;

        return tokens.map((token, i) => {
            // Handle whitespace/newlines
            if (token.trim().length === 0) {
                if (token.includes('\n')) {
                    return <br key={i} />;
                }
                return <span key={i}>{token}</span>;
            }

            // Handle words
            const isActive = currentWordIndex === activeIndex;
            currentWordIndex++;

            const padding = Math.round((styling.highlight_bg_padding || 0) * scaleFactor);

            if (isActive) {
                return (
                    <span key={i} style={{
                        backgroundColor: styling.highlight_bg_color,
                        color: styling.highlight_font_color,
                        padding: `${padding}px`,
                        borderRadius: `${Math.round((styling.highlight_bg_radius || 0) * scaleFactor)}px`,
                        textShadow: 'none',
                        WebkitBoxDecorationBreak: 'clone',
                        boxDecorationBreak: 'clone',
                        position: 'relative',
                        zIndex: 1,
                        margin: '0 2px', // Slight margin for box separation
                        display: 'inline-block' // Ensure transforms/padding work correctly
                    }}>
                        {token}
                    </span>
                );
            }
            return <span key={i}>{token}</span>;
        });
    }

    return text
}

function Preview({ showSubtitlePreview = false }) {
    const { projectId, videoOutput, segments, jobs, project } = useProjectStore()
    const videoRef = useRef(null)
    const previewBoxRef = useRef(null)
    const [imgError, setImgError] = useState(false)
    const [subtitleData, setSubtitleData] = useState(null)
    const [previewDimensions, setPreviewDimensions] = useState({ width: 0, height: 0 })

    // Check if pipeline is running
    const pipeJob = jobs.pipeline
    const isPipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'

    // Reset error when project or segments change
    useEffect(() => {
        setImgError(false)
    }, [projectId, segments])

    // Track preview box dimensions for accurate scaling
    useEffect(() => {
        const updateDimensions = () => {
            const box = previewBoxRef.current
            if (box) {
                const video = videoRef.current
                if (video && video.videoWidth > 0) {
                    setPreviewDimensions({
                        width: video.clientWidth,
                        height: video.clientHeight
                    })
                } else {
                    // Fallback to box dimensions
                    setPreviewDimensions({
                        width: box.clientWidth,
                        height: box.clientHeight
                    })
                }
            }
        }

        updateDimensions()
        window.addEventListener('resize', updateDimensions)

        // Also update when video loads
        const video = videoRef.current
        if (video) {
            video.addEventListener('loadedmetadata', updateDimensions)
            video.addEventListener('resize', updateDimensions)
        }

        return () => {
            window.removeEventListener('resize', updateDimensions)
            if (video) {
                video.removeEventListener('loadedmetadata', updateDimensions)
                video.removeEventListener('resize', updateDimensions)
            }
        }
    }, [videoOutput])

    // Update subtitle preview data from global state
    useEffect(() => {
        if (showSubtitlePreview && typeof window !== 'undefined') {
            const checkData = () => {
                const styling = window.__subtitleStyling
                const entries = window.__subtitleEntries
                if (styling && entries?.length > 0) {
                    setSubtitleData({ styling, entries })
                } else {
                    setSubtitleData(null)
                }
            }
            checkData()
            const interval = setInterval(checkData, 500)
            return () => clearInterval(interval)
        } else {
            setSubtitleData(null)
        }
    }, [showSubtitlePreview])

    // Track video time
    const [currentTime, setCurrentTime] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const rafRef = useRef(null)

    useEffect(() => {
        const video = videoRef.current
        if (!video) return

        const onTimeUpdate = () => setCurrentTime(video.currentTime)
        const onSeeked = () => setCurrentTime(video.currentTime)
        const onPlay = () => {
            setIsPlaying(true)
            setCurrentTime(video.currentTime)
        }
        const onPause = () => {
            setIsPlaying(false)
            setCurrentTime(video.currentTime)
        }

        video.addEventListener('timeupdate', onTimeUpdate)
        video.addEventListener('play', onPlay)
        video.addEventListener('pause', onPause)
        video.addEventListener('seeked', onSeeked)

        return () => {
            video.removeEventListener('timeupdate', onTimeUpdate)
            video.removeEventListener('play', onPlay)
            video.removeEventListener('pause', onPause)
            video.removeEventListener('seeked', onSeeked)
        }
    }, [videoOutput, isPipelineRunning])

    useEffect(() => {
        const video = videoRef.current
        if (!video) return undefined

        if (!isPlaying) {
            if (rafRef.current) {
                cancelAnimationFrame(rafRef.current)
                rafRef.current = null
            }
            return undefined
        }

        const tick = () => {
            setCurrentTime(video.currentTime)
            rafRef.current = requestAnimationFrame(tick)
        }

        rafRef.current = requestAnimationFrame(tick)

        return () => {
            if (rafRef.current) {
                cancelAnimationFrame(rafRef.current)
                rafRef.current = null
            }
        }
    }, [isPlaying])

    // Determine what to show
    const hasVideo = !!videoOutput
    const safeSegments = Array.isArray(segments) ? segments : []
    const lastImage = safeSegments.filter(s => s && s.thumbnail).slice(-1)[0]?.thumbnail

    // Calculate scale factor based on actual render resolution
    const getScaleFactor = useCallback(() => {
        const projectFormat = project?.format || "9:16"
        // Base render resolution
        const baseWidth = projectFormat === "9:16" ? 720 : 1280
        const baseHeight = projectFormat === "9:16" ? 1280 : 720

        // Use actual preview dimensions
        const previewWidth = previewDimensions.width || (projectFormat === "9:16" ? 360 : 640)
        const previewHeight = previewDimensions.height || (projectFormat === "9:16" ? 640 : 360)

        // Scale by the smaller ratio to ensure subtitle fits
        const scaleX = previewWidth / baseWidth
        const scaleY = previewHeight / baseHeight

        return Math.min(scaleX, scaleY)
    }, [project?.format, previewDimensions])

    // Get subtitle preview style - matches backend PILlow rendering exactly
    const getSubtitleStyle = useCallback(() => {
        if (!subtitleData?.styling) return {}
        const s = subtitleData.styling
        const scaleFactor = getScaleFactor()

        const fontSize = Math.max(8, Math.round(s.font_size * scaleFactor))

        // Generate text-shadow that mimics PILlow's stroke technique
        const textShadow = generateStrokeShadow(s.stroke_width, s.stroke_color, scaleFactor)

        const bgPadding = s.background_enabled ? Math.round(s.background_padding * scaleFactor) : 0

        return {
            fontFamily: `"${s.font_family}", sans-serif`,
            fontSize: `${fontSize}px`,
            fontWeight: s.font_weight === 'bold' ? 700 : (s.font_weight === 'black' ? 900 : 400),
            color: s.font_color,
            textAlign: s.text_align,
            // Use text-shadow instead of webkit-text-stroke for PILlow-accurate rendering
            textShadow: textShadow,
            WebkitTextStroke: '0', // Disable webkit-text-stroke
            textTransform: s.uppercase ? 'uppercase' : 'none',
            padding: bgPadding > 0 ? `${bgPadding}px` : '0',
            backgroundColor: s.background_enabled
                ? `${s.background_color}${Math.round(s.background_opacity * 255).toString(16).padStart(2, '0')}`
                : 'transparent',
            borderRadius: s.background_enabled ? `${Math.round((s.background_radius || 4) * scaleFactor)}px` : '0',
            lineHeight: 1.2,
            letterSpacing: '0.01em',
            // Paint order ensures fill renders on top of stroke (like PILlow)
            paintOrder: 'stroke fill',
            // Prevent layout shift
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
        }
    }, [subtitleData, getScaleFactor])

    // Find active subtitle with timing info
    const getActiveSubtitle = useCallback(() => {
        if (!subtitleData?.entries?.length) return null

        // Helper to parse SRT time "00:00:00,000" (or looser formats) to seconds
        const parseSrt = (t) => {
            if (t === null || t === undefined) return 0
            if (typeof t === 'number' && Number.isFinite(t)) return t
            if (typeof t !== 'string') return 0

            const normalized = t.trim().replace(',', '.')

            if (!normalized) return 0

            if (normalized.includes(':')) {
                const parts = normalized.split(':')
                if (parts.length === 3) {
                    const hours = parseFloat(parts[0])
                    const minutes = parseFloat(parts[1])
                    const seconds = parseFloat(parts[2])
                    if ([hours, minutes, seconds].some(Number.isNaN)) return 0
                    return hours * 3600 + minutes * 60 + seconds
                }
                if (parts.length === 2) {
                    const minutes = parseFloat(parts[0])
                    const seconds = parseFloat(parts[1])
                    if ([minutes, seconds].some(Number.isNaN)) return 0
                    return minutes * 60 + seconds
                }
                return 0
            }

            const asSeconds = parseFloat(normalized)
            return Number.isNaN(asSeconds) ? 0 : asSeconds
        }

        const active = subtitleData.entries.find(e => {
            const start = parseSrt(e.start_time)
            const end = parseSrt(e.end_time)
            return currentTime >= start && currentTime <= end
        })

        // If playing, only show if matched. If paused and no match, show first as sample (for styling)
        if (active) {
            const start = parseSrt(active.start_time)
            const end = parseSrt(active.end_time)
            const duration = end - start
            const progress = duration > 0 ? (currentTime - start) / duration : 0
            return { text: active.text, progress }
        }

        if (!isPlaying && subtitleData.entries.length > 0) {
            return { text: subtitleData.entries[0].text, progress: 0.5 } // Show middle word for sample
        }
        return null
    }, [subtitleData, currentTime, isPlaying])

    const activeSubtitle = getActiveSubtitle()
    const displayText = activeSubtitle ? activeSubtitle.text : null
    const displayProgress = activeSubtitle ? activeSubtitle.progress : -1
    const scaleFactor = getScaleFactor()

    return (
        <section className="panel cinema-panel">
            <div className="preview-box" ref={previewBoxRef}>
                {/* Show analysis visualization during pipeline execution */}
                {isPipelineRunning && (
                    <AnalysisVisualization />
                )}

                {!isPipelineRunning && !hasVideo && (!lastImage || imgError) && (
                    <div className="preview-placeholder">
                        <div className="placeholder-icon">🎬</div>
                        <p>{imgError ? "Preview Image Error" : "Preview will appear here"}</p>
                    </div>
                )}

                {!isPipelineRunning && !hasVideo && lastImage && !imgError && (
                    <img
                        src={fixImageUrl(lastImage)}
                        alt="Last generated scene"
                        className="preview-image"
                        onError={() => setImgError(true)}
                    />
                )}

                {!isPipelineRunning && hasVideo && (
                    <video
                        key={videoOutput}
                        ref={videoRef}
                        src={videoOutput}
                        controls
                        className="preview-video"
                    />
                )}

                {/* Subtitle Preview Overlay - pixel-accurate to backend render */}
                {showSubtitlePreview && subtitleData && displayText && (
                    <div
                        className={`subtitle-preview-overlay ${subtitleData.styling.position}`}
                        style={{
                            ...(subtitleData.styling.position === 'top' && {
                                top: `${Math.round(subtitleData.styling.margin_y * scaleFactor)}px`,
                                maxHeight: `calc(100% - ${Math.round(subtitleData.styling.margin_y * scaleFactor)}px)`,
                            }),
                            ...(subtitleData.styling.position === 'bottom' && {
                                bottom: `${Math.round(subtitleData.styling.margin_y * scaleFactor)}px`,
                                maxHeight: `calc(100% - ${Math.round(subtitleData.styling.margin_y * scaleFactor)}px)`,
                            }),
                            ...(subtitleData.styling.position === 'middle' && {
                                maxHeight: '100%',
                            }),
                            // middle position uses CSS transform, no inline margin needed
                            maxWidth: `${subtitleData.styling.max_width_percent}%`,
                            overflow: 'hidden',
                        }}
                    >
                        <div className="subtitle-preview-text" style={getSubtitleStyle()}>
                            {renderSubtitleWithHighlights(displayText, subtitleData.styling, scaleFactor, displayProgress)}
                        </div>
                    </div>
                )}
            </div>

            <Timeline videoRef={videoRef} />
        </section>
    )
}

export default Preview
