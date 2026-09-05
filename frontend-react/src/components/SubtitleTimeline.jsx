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

    const validDuration = (duration > 0 && Number.isFinite(duration)) ? duration : 1

    const handleSeekFromEvent = useCallback((e) => {
        const track = trackRef.current
        if (!track || validDuration <= 0) return

        const rect = track.getBoundingClientRect()
        const clickX = e.clientX - rect.left
        const ratio = Math.max(0, Math.min(1, clickX / rect.width))
        const targetTime = ratio * validDuration
        onSeek(targetTime)
    }, [validDuration, onSeek])

    const handleMouseDown = (e) => {
        isDraggingRef.current = true
        handleSeekFromEvent(e)

        const onMouseMove = (moveEvent) => {
            if (isDraggingRef.current) {
                handleSeekFromEvent(moveEvent)
            }
        }

        const onMouseUp = () => {
            isDraggingRef.current = false
            window.removeEventListener('mousemove', onMouseMove)
            window.removeEventListener('mouseup', onMouseUp)
        }

        window.addEventListener('mousemove', onMouseMove)
        window.addEventListener('mouseup', onMouseUp)
    }

    // Generate time markers across the timeline (e.g. every 5s, 10s, 30s depending on duration)
    const getMarkers = () => {
        if (!Number.isFinite(validDuration) || validDuration <= 0) return [0]
        const markers = []
        let interval = 5
        if (validDuration > 300) interval = 60
        else if (validDuration > 120) interval = 30
        else if (validDuration > 60) interval = 15
        else if (validDuration > 30) interval = 10

        for (let t = 0; t <= validDuration; t += interval) {
            markers.push(t)
            if (markers.length > 50) break
        }
        return markers
    }

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
                <div className="timeline-entry-count">
                    <span>{formatCount(entries.length, 'subtitles.timeline')}</span>
                </div>
            </div>

            {/* Time ruler */}
            <div className="timeline-ruler">
                {getMarkers().map((m) => {
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
            >
                {/* Subtitle entry blocks */}
                <div className="timeline-blocks-layer">
                    {entries.map((entry) => {
                        const start = parseSrtTimeToSeconds(entry.start_time)
                        const end = parseSrtTimeToSeconds(entry.end_time)
                        const leftPct = (start / validDuration) * 100
                        const widthPct = Math.max(0.8, ((end - start) / validDuration) * 100)
                        const isActive = entry.id === activeEntryId || (currentTime >= start && currentTime <= end)

                        return (
                            <div
                                key={entry.id}
                                className={`timeline-block ${isActive ? 'active' : ''}`}
                                style={{
                                    left: `${leftPct}%`,
                                    width: `${widthPct}%`
                                }}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onSeek(start)
                                    onSelectEntry(entry)
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
