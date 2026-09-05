import { useState, useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react'
import './SubtitleVideoPlayer.css'

/**
 * Helper to parse time string "00:00:00,000" or "00:00:00.000" to seconds (float)
 */
export function parseSrtTimeToSeconds(t) {
    if (t === null || t === undefined) return 0
    if (typeof t === 'number' && Number.isFinite(t)) return t
    if (typeof t !== 'string') return 0

    const normalized = t.trim().replace(',', '.')
    if (!normalized) return 0

    if (normalized.includes(':')) {
        const parts = normalized.split(':')
        if (parts.length === 3) {
            const hours = parseFloat(parts[0]) || 0
            const minutes = parseFloat(parts[1]) || 0
            const seconds = parseFloat(parts[2]) || 0
            return hours * 3600 + minutes * 60 + seconds
        }
        if (parts.length === 2) {
            const minutes = parseFloat(parts[0]) || 0
            const seconds = parseFloat(parts[1]) || 0
            return minutes * 60 + seconds
        }
    }

    const asSeconds = parseFloat(normalized)
    return Number.isNaN(asSeconds) ? 0 : asSeconds
}

/**
 * Generates text-shadow CSS that mimics PILlow's stroke rendering.
 */
function generateStrokeShadow(strokeWidth, strokeColor, scaleFactor) {
    if (!strokeWidth || strokeWidth <= 0 || !strokeColor) return 'none'

    const scaledWidth = Math.max(1, strokeWidth * scaleFactor)
    const shadows = []
    const steps = Math.max(8, Math.ceil(scaledWidth * 4))

    for (let i = 0; i < steps; i++) {
        const angle = (2 * Math.PI * i) / steps
        const x = Math.cos(angle) * scaledWidth
        const y = Math.sin(angle) * scaledWidth
        shadows.push(`${x.toFixed(1)}px ${y.toFixed(1)}px 0 ${strokeColor}`)
    }

    if (scaledWidth > 1.5) {
        const innerWidth = scaledWidth * 0.55
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
 * Render subtitle content supporting <h> tags and active karaoke word highlight
 */
function renderSubtitleContent(text, styling, scaleFactor, progress = -1) {
    if (!text) return null

    const paddingV = Math.round((styling.highlight_bg_padding ?? 8) * 0.3 * scaleFactor)
    const paddingH = Math.round((styling.highlight_bg_padding ?? 8) * 0.6 * scaleFactor)
    const radius = Math.round((styling.highlight_bg_radius ?? 8) * scaleFactor)
    const hlBg = styling.highlight_bg_color || '#FF0000'
    const hlColor = styling.highlight_font_color || '#FFFFFF'

    // Split text preserving <h> tags and whitespace/newlines
    const rawParts = text.split(/(<h>.*?<\/h>)/gi)
    const tokens = []

    rawParts.forEach(part => {
        if (!part) return
        const isTag = /^<h>[\s\S]*<\/h>$/i.test(part)
        const content = isTag ? part.slice(3, -4) : part
        const subTokens = content.split(/(\s+)/)
        subTokens.forEach(st => {
            if (!st) return
            const isWhitespace = /^\s+$/.test(st)
            tokens.push({
                text: st,
                isWhitespace,
                isHl: isTag && !isWhitespace
            })
        })
    })

    const wordTokens = tokens.filter(t => !t.isWhitespace)
    const totalWords = wordTokens.length
    const isKaraokeActive = styling.highlight_active_word && progress >= 0 && totalWords > 0
    const activeIndex = isKaraokeActive ? Math.min(Math.floor(progress * totalWords), totalWords - 1) : -1

    let currentWordIndex = 0

    return tokens.map((token, i) => {
        if (token.isWhitespace) {
            if (token.text.includes('\n')) return <br key={i} />
            return <span key={i}>{token.text}</span>
        }

        const isCurrentActive = isKaraokeActive && currentWordIndex === activeIndex
        const shouldHighlight = token.isHl || isCurrentActive
        currentWordIndex++

        if (shouldHighlight) {
            return (
                <span
                    key={i}
                    style={{
                        backgroundColor: hlBg,
                        color: hlColor,
                        padding: `${paddingV}px ${paddingH}px`,
                        borderRadius: `${radius}px`,
                        textShadow: 'none',
                        WebkitBoxDecorationBreak: 'clone',
                        boxDecorationBreak: 'clone',
                        position: 'relative',
                        zIndex: 1,
                        margin: '0 2px',
                        display: 'inline-block',
                        transform: isCurrentActive ? 'scale(1.04)' : 'none',
                        transition: 'all 0.12s ease'
                    }}
                >
                    {token.text}
                </span>
            )
        }

        return <span key={i}>{token.text}</span>
    })
}

const SubtitleVideoPlayer = forwardRef(function SubtitleVideoPlayer({
    videoUrl,
    entries = [],
    styling = {},
    format = '9:16',
    isRendered = false,
    badgeText = null,
    onTimeChange = null,
    onDurationChange = null,
    previewEntryId = null,
    autoPlay = false
}, ref) {
    const videoRef = useRef(null)
    const containerRef = useRef(null)
    const rafRef = useRef(null)

    const [currentTime, setCurrentTime] = useState(0)
    const [duration, setDuration] = useState(0)
    const [isPlaying, setIsPlaying] = useState(false)
    const [videoBox, setVideoBox] = useState({ width: 0, height: 0 })

    // Expose video control methods via ref
    useImperativeHandle(ref, () => ({
        play: () => videoRef.current?.play(),
        pause: () => videoRef.current?.pause(),
        seekTo: (seconds) => {
            if (videoRef.current) {
                videoRef.current.currentTime = seconds
                setCurrentTime(seconds)
            }
        },
        getVideoElement: () => videoRef.current
    }))

    // Calculate actual letterboxed/pillarboxed video dimensions within container
    const updateDimensions = useCallback(() => {
        const video = videoRef.current
        const container = containerRef.current
        if (!video || !container) return

        const containerWidth = container.clientWidth
        const containerHeight = container.clientHeight

        if (containerWidth === 0 || containerHeight === 0) return

        const nativeW = video.videoWidth || (format === '16:9' ? 1280 : 720)
        const nativeH = video.videoHeight || (format === '16:9' ? 720 : 1280)
        const videoAspect = nativeW / nativeH
        const containerAspect = containerWidth / containerHeight

        let displayW, displayH
        if (videoAspect > containerAspect) {
            // Letterboxed top/bottom
            displayW = containerWidth
            displayH = containerWidth / videoAspect
        } else {
            // Pillarboxed left/right
            displayH = containerHeight
            displayW = containerHeight * videoAspect
        }

        setVideoBox({
            width: Math.round(displayW),
            height: Math.round(displayH)
        })
    }, [format])

    useEffect(() => {
        const video = videoRef.current
        const container = containerRef.current
        if (!video) return

        const handleLoadedMetadata = () => {
            const dur = video.duration
            if (Number.isFinite(dur) && dur > 0) {
                setDuration(dur)
                if (onDurationChange) onDurationChange(dur)
            }
            updateDimensions()
        }

        const handleLoadedData = () => {
            if (video.currentTime === 0) {
                video.currentTime = 0.001
            }
            updateDimensions()
        }

        if (video.readyState >= 1) {
            handleLoadedMetadata()
        }
        if (video.readyState >= 2) {
            handleLoadedData()
        }

        let resizeObserver = null
        if (typeof ResizeObserver !== 'undefined' && container) {
            resizeObserver = new ResizeObserver(() => {
                updateDimensions()
            })
            resizeObserver.observe(container)
        }

        video.addEventListener('loadedmetadata', handleLoadedMetadata)
        video.addEventListener('loadeddata', handleLoadedData)
        video.addEventListener('canplay', updateDimensions)
        video.addEventListener('resize', updateDimensions)
        window.addEventListener('resize', updateDimensions)

        updateDimensions()

        return () => {
            if (resizeObserver) resizeObserver.disconnect()
            video.removeEventListener('loadedmetadata', handleLoadedMetadata)
            video.removeEventListener('loadeddata', handleLoadedData)
            video.removeEventListener('canplay', updateDimensions)
            video.removeEventListener('resize', updateDimensions)
            window.removeEventListener('resize', updateDimensions)
        }
    }, [videoUrl, updateDimensions, onDurationChange])

    // Time tracking
    useEffect(() => {
        const video = videoRef.current
        if (!video) return

        const onTimeUpdate = () => {
            setCurrentTime(video.currentTime)
            if (onTimeChange) onTimeChange(video.currentTime)
        }

        const onPlay = () => setIsPlaying(true)
        const onPause = () => setIsPlaying(false)
        const onSeeked = () => {
            setCurrentTime(video.currentTime)
            if (onTimeChange) onTimeChange(video.currentTime)
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
    }, [videoUrl, onTimeChange])

    // High frequency tick while playing for smooth karaoke word tracking
    useEffect(() => {
        const video = videoRef.current
        if (!video) return

        if (!isPlaying) {
            if (rafRef.current) cancelAnimationFrame(rafRef.current)
            return
        }

        const tick = () => {
            if (video && !video.paused) {
                setCurrentTime(video.currentTime)
            }
            rafRef.current = requestAnimationFrame(tick)
        }

        rafRef.current = requestAnimationFrame(tick)

        return () => {
            if (rafRef.current) cancelAnimationFrame(rafRef.current)
        }
    }, [isPlaying])

    // Calculate scale factor relative to render resolution (720x1280 or 1280x720)
    const getScaleFactor = useCallback(() => {
        const isHorizontal = format === '16:9'
        const baseWidth = isHorizontal ? 1280 : 720
        const baseHeight = isHorizontal ? 720 : 1280

        const previewW = videoBox.width || (isHorizontal ? 640 : 360)
        const previewH = videoBox.height || (isHorizontal ? 360 : 640)

        const scaleX = previewW / baseWidth
        const scaleY = previewH / baseHeight

        return Math.min(scaleX, scaleY)
    }, [format, videoBox])

    // Find active subtitle entry based on current time
    const getActiveSubtitle = useCallback(() => {
        if (!entries || entries.length === 0) return null

        // If a specific entry is chosen for preview and video is paused at start, highlight that entry
        if (!isPlaying && previewEntryId !== null) {
            const chosen = entries.find(e => e.id === previewEntryId)
            if (chosen) {
                return { text: chosen.text, progress: 0.5, isSample: false }
            }
        }

        const active = entries.find(e => {
            const start = parseSrtTimeToSeconds(e.start_time)
            const end = parseSrtTimeToSeconds(e.end_time)
            return currentTime >= start && currentTime <= end
        })

        if (active) {
            const start = parseSrtTimeToSeconds(active.start_time)
            const end = parseSrtTimeToSeconds(active.end_time)
            const span = end - start
            const progress = span > 0 ? (currentTime - start) / span : 0
            return { text: active.text, progress, isSample: false }
        }

        // When paused and no subtitle at exact time, show the nearest or first entry so user can see styling
        if (!isPlaying && entries.length > 0) {
            // Find nearest entry
            let nearest = entries[0]
            let minDiff = Infinity
            for (const e of entries) {
                const s = parseSrtTimeToSeconds(e.start_time)
                const diff = Math.abs(currentTime - s)
                if (diff < minDiff) {
                    minDiff = diff
                    nearest = e
                }
            }
            return { text: nearest.text, progress: 0.5, isSample: minDiff > 2.0 }
        }

        return null
    }, [entries, currentTime, isPlaying, previewEntryId])

    const scaleFactor = getScaleFactor()
    const activeSub = getActiveSubtitle()

    // Subtitle CSS styles matching PILlow backend
    const getSubtitleStyle = () => {
        if (!styling) return {}

        const fontSize = Math.max(10, Math.round((styling.font_size || 48) * scaleFactor))
        const strokeShadow = generateStrokeShadow(styling.stroke_width || 3, styling.stroke_color || '#000000', scaleFactor)
        const bgPadding = styling.background_enabled ? Math.round((styling.background_padding || 10) * scaleFactor) : 0
        const bgRadius = styling.background_enabled ? Math.round((styling.background_radius || 8) * scaleFactor) : 0

        return {
            fontFamily: `"${styling.font_family || 'Montserrat'}", sans-serif`,
            fontSize: `${fontSize}px`,
            fontWeight: styling.font_weight === 'bold' ? 700 : (styling.font_weight === '900' ? 900 : 400),
            color: styling.font_color || '#FFFFFF',
            textAlign: styling.text_align || 'center',
            textShadow: strokeShadow,
            WebkitTextStroke: '0',
            textTransform: styling.uppercase ? 'uppercase' : 'none',
            padding: bgPadding > 0 ? `${bgPadding}px ${Math.round(bgPadding * 1.4)}px` : '0',
            backgroundColor: styling.background_enabled
                ? `${styling.background_color || '#000000'}${Math.round((styling.background_opacity ?? 0.75) * 255).toString(16).padStart(2, '0')}`
                : 'transparent',
            borderRadius: `${bgRadius}px`,
            lineHeight: 1.25,
            letterSpacing: '0.01em',
            paintOrder: 'stroke fill',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            display: 'inline-block'
        }
    }

    const position = styling?.position || 'bottom'
    const marginY = Math.round((styling?.margin_y ?? 60) * scaleFactor)
    const maxWidthPercent = styling?.max_width_percent || 90

    return (
        <div
            className={`subtitle-video-player-container ${format === '16:9' ? 'format-16-9' : 'format-9-16'}`}
            ref={containerRef}
        >
            {/* Badge Indicator */}
            {badgeText && (
                <div className={`player-badge ${isRendered ? 'badge-rendered' : 'badge-preview'}`}>
                    {badgeText}
                </div>
            )}

            {/* Video Element */}
            <video
                ref={videoRef}
                src={videoUrl}
                controls
                playsInline
                preload="auto"
                autoPlay={autoPlay}
                className="svp-video-element"
                onError={(e) => {
                    console.error('Video error:', videoRef.current?.error, e)
                }}
            />

            {/* Subtitle Overlay (disabled if isRendered is true since video has burned-in subs) */}
            {!isRendered && activeSub && videoBox.width > 0 && (
                <div
                    className={`svp-subtitle-overlay pos-${position}`}
                    style={{
                        width: `${videoBox.width}px`,
                        maxWidth: `${videoBox.width}px`,
                        left: '50%',
                        transform: position === 'middle'
                            ? 'translateX(-50%) translateY(-50%)'
                            : 'translateX(-50%)',
                        ...(position === 'top' && {
                            top: `calc(50% - ${videoBox.height / 2}px + ${marginY}px)`,
                        }),
                        ...(position === 'bottom' && {
                            bottom: `calc(50% - ${videoBox.height / 2}px + ${marginY}px)`,
                        }),
                        ...(position === 'middle' && {
                            top: '50%',
                        }),
                    }}
                >
                    <div
                        className="svp-subtitle-wrapper"
                        style={{
                            maxWidth: `${maxWidthPercent}%`,
                            textAlign: styling?.text_align || 'center'
                        }}
                    >
                        <div
                            className={`svp-subtitle-text ${styling?.animation && styling.animation !== 'none' ? `anim-${styling.animation}` : ''} ${activeSub.isSample ? 'svp-sample-mode' : ''}`}
                            style={getSubtitleStyle()}
                        >
                            {renderSubtitleContent(activeSub.text, styling, scaleFactor, activeSub.progress)}
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
})

export default SubtitleVideoPlayer
