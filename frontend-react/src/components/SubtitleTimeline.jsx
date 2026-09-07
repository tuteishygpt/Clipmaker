import { useRef, useCallback, useEffect } from 'react'
import { parseSrtTimeToSeconds } from './SubtitleVideoPlayer'
import { useTranslation } from '../i18n'
import './SubtitleTimeline.css'

function formatSeconds(secs) {
    if (!secs || isNaN(secs) || !Number.isFinite(secs) || secs < 0) return '00:00'
    const m = Math.floor(secs / 60)
    const s = Math.floor(secs % 60)
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

export default function SubtitleTimeline({
    currentTime = 0,
    duration = 0,
    entries = [],
    activeEntryId = null,
    onSeek = () => {},
    onSelectEntry = () => {}
}) {
    const { formatCount } = useTranslation()
    const trackRef = useRef(null)
    const isDraggingRef = useRef(false)
    const activeCleanupRef = useRef(null)
    const rafIdRef = useRef(null)

    const validDuration = (duration > 0 && Number.isFinite(duration)) ? duration : 1

    // Cleanup drag listeners if component unmounts while dragging
    useEffect(() => {
        return () => {
            if (activeCleanupRef.current) {
                activeCleanupRef.current()
                activeCleanupRef.current = null
            }
            if (rafIdRef.current) {
                cancelAnimationFrame(rafIdRef.current)
                rafIdRef.current = null
            }
        }
    }, [])

    const handleSeekFromEvent = useCallback((e, isThrottled = false) => {
        const track = trackRef.current
        if (!track || validDuration <= 0) return

        const rect = track.getBoundingClientRect()
        if (rect.width <= 0) return

        const clientX = e.touches?.[0]?.clientX ?? e.changedTouches?.[0]?.clientX ?? e.clientX
        if (clientX === undefined) return

        const clickX = clientX - rect.left
        const ratio = Math.max(0, Math.min(1, clickX / rect.width))
        const targetTime = ratio * validDuration

        if (isThrottled) {
            if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current)
            rafIdRef.current = requestAnimationFrame(() => {
                onSeek(targetTime)
                rafIdRef.current = null
            })
        } else {
            if (rafIdRef.current) {
                cancelAnimationFrame(rafIdRef.current)
                rafIdRef.current = null
            }
            onSeek(targetTime)
        }
    }, [validDuration, onSeek])

    const handleMouseDown = (e) => {
        if (e.button !== 0) return
        isDraggingRef.current = true
        handleSeekFromEvent(e, false)

        const onMouseMove = (moveEvent) => {
            if (isDraggingRef.current) {
                handleSeekFromEvent(moveEvent, true)
            }
        }

        const onMouseUp = () => {
            isDraggingRef.current = false
            if (activeCleanupRef.current) {
                activeCleanupRef.current()
                activeCleanupRef.current = null
            }
        }

        const cleanup = () => {
            window.removeEventListener('mousemove', onMouseMove)
            window.removeEventListener('mouseup', onMouseUp)
        }

        activeCleanupRef.current = cleanup
        window.addEventListener('mousemove', onMouseMove)
        window.addEventListener('mouseup', onMouseUp)
    }

    const handleTouchStart = (e) => {
        isDraggingRef.current = true
        handleSeekFromEvent(e, false)

        const onTouchMove = (moveEvent) => {
            if (isDraggingRef.current) {
                if (moveEvent.cancelable) moveEvent.preventDefault()
                handleSeekFromEvent(moveEvent, true)
            }
        }

        const onTouchEnd = () => {
            isDraggingRef.current = false
            if (activeCleanupRef.current) {
                activeCleanupRef.current()
                activeCleanupRef.current = null
            }
        }

        const cleanup = () => {
            window.removeEventListener('touchmove', onTouchMove)
            window.removeEventListener('touchend', onTouchEnd)
            window.removeEventListener('touchcancel', onTouchEnd)
        }

        activeCleanupRef.current = cleanup
        window.addEventListener('touchmove', onTouchMove, { passive: false })
        window.addEventListener('touchend', onTouchEnd)
        window.addEventListener('touchcancel', onTouchEnd)
    }

    // Generate time markers across the timeline (memoized)
    const markers = useMemo(() => {
        if (!Number.isFinite(validDuration) || validDuration <= 0) return [0]
        const list = []
        let interval = 5
        if (validDuration > 300) interval = 60
        else if (validDuration > 120) interval = 30
        else if (validDuration > 60) interval = 15
        else if (validDuration > 30) interval = 10

        for (let t = 0; t <= validDuration; t += interval) {
            list.push(t)
            if (list.length > 50) break
        }
        return list
    }, [validDuration])

    // Memoize parsed entry timings
    const parsedEntries = useMemo(() => {
        return entries.map((entry) => {
            const start = parseSrtTimeToSeconds(entry.start_time)
            const end = parseSrtTimeToSeconds(entry.end_time)
            const leftPct = (start / validDuration) * 100
            const widthPct = Math.max(0.8, ((end - start) / validDuration) * 100)
            return {
                ...entry,
                start,
                end,
                leftPct,
                widthPct
            }
        })
    }, [entries, validDuration])

    const playheadPercent = Math.max(0, Math.min(100, (currentTime / validDuration) * 100))

    return (
        <div className="subtitle-timeline-container">
            {/* Header info */}
            <div className="timeline-info-bar">
                <div className="timeline-time-display">
                    <span className="current-time">{formatSeconds(currentTime)}</span>
                    <span className="time-divider">/</span>
                    <span className="total-time">{formatSeconds(duration)}</span>
                </div>
                <div className="timeline-quick-controls">
                    <button
                        type="button"
                        className="btn-timeline-seek-step"
                        onClick={() => onSeek(Math.max(0, currentTime - 5))}
                        title="-5s"
                        aria-label="Seek backward 5 seconds"
                    >
                        ⏪ 5s
                    </button>
                    <button
                        type="button"
                        className="btn-timeline-seek-step"
                        onClick={() => onSeek(Math.min(validDuration, currentTime + 5))}
                        title="+5s"
                        aria-label="Seek forward 5 seconds"
                    >
                        5s ⏩
                    </button>
                </div>
                <div className="timeline-entry-count">
                    <span>{formatCount(entries.length, 'subtitles.timeline')}</span>
                </div>
            </div>

            {/* Time ruler */}
            <div className="timeline-ruler">
                {markers.map((m) => {
                    const pct = (m / validDuration) * 100
                    return (
                        <div
                            key={m}
                            className="ruler-tick"
                            style={{ left: `${pct}%` }}
                        >
                            <span className="ruler-label">{formatSeconds(m)}</span>
                        </div>
                    )
                })}
            </div>

            {/* Main timeline track with subtitle chips and scrubber */}
            <div
                className="timeline-track"
                ref={trackRef}
                onMouseDown={handleMouseDown}
                onTouchStart={handleTouchStart}
                role="slider"
                aria-label="Video Timeline"
                aria-valuenow={Math.round(currentTime)}
                aria-valuemin={0}
                aria-valuemax={Math.round(validDuration)}
                tabIndex={0}
                onKeyDown={(e) => {
                    if (e.key === 'ArrowLeft') {
                        e.preventDefault()
                        onSeek(Math.max(0, currentTime - (e.shiftKey ? 5 : 1)))
                    } else if (e.key === 'ArrowRight') {
                        e.preventDefault()
                        onSeek(Math.min(validDuration, currentTime + (e.shiftKey ? 5 : 1)))
                    }
                }}
            >
                {/* Subtitle entry blocks */}
                <div className="timeline-blocks-layer">
                    {parsedEntries.map((entry) => {
                        const isActive = entry.id === activeEntryId || (currentTime >= entry.start && currentTime <= entry.end)

                        return (
                            <div
                                key={entry.id}
                                className={`timeline-block ${isActive ? 'active' : ''}`}
                                style={{
                                    left: `${entry.leftPct}%`,
                                    width: `${entry.widthPct}%`
                                }}
                                onMouseDown={(e) => e.stopPropagation()}
                                onTouchStart={(e) => {
                                    e.stopPropagation()
                                    onSeek(entry.start)
                                    onSelectEntry(entry)
                                }}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onSeek(entry.start)
                                    onSelectEntry(entry)
                                }}
                                role="button"
                                tabIndex={0}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' || e.key === ' ') {
                                        e.preventDefault()
                                        e.stopPropagation()
                                        onSeek(entry.start)
                                        onSelectEntry(entry)
                                    }
                                }}
                                title={`#${entry.id} (${entry.start_time} - ${entry.end_time}): ${entry.text}`}
                            >
                                <span className="block-text-snippet">
                                    {entry.text || `#${entry.id}`}
                                </span>
                            </div>
                        )
                    })}
                </div>

                {/* Progress bar fill */}
                <div
                    className="timeline-progress-fill"
                    style={{ width: `${playheadPercent}%` }}
                />

                {/* Playhead needle */}
                <div
                    className="timeline-playhead"
                    style={{ left: `${playheadPercent}%` }}
                >
                    <div className="playhead-handle" />
                    <div className="playhead-line" />
                </div>
            </div>
        </div>
    )
}
