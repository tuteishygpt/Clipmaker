import { useEffect, useRef, useState, useCallback } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { parseTimeToSeconds, fixImageUrl } from '../utils'

function Timeline({ videoRef }) {
    const { segments } = useProjectStore()
    const [progress, setProgress] = useState(0)
    const animationRef = useRef(null)

    // Calculate total duration
    const totalDuration = segments.length > 0
        ? parseTimeToSeconds(segments[segments.length - 1].end_time)
        : 0

    // Sync progress
    const updateProgress = useCallback(() => {
        if (videoRef?.current) {
            const currentTime = videoRef.current.currentTime
            const duration = videoRef.current.duration || totalDuration || 1
            const pct = (currentTime / duration) * 100
            setProgress(pct)
        }
        animationRef.current = requestAnimationFrame(updateProgress)
    }, [videoRef, totalDuration])

    useEffect(() => {
        if (totalDuration > 0) {
            animationRef.current = requestAnimationFrame(updateProgress)
        }
        return () => {
            if (animationRef.current) cancelAnimationFrame(animationRef.current)
        }
    }, [updateProgress, totalDuration])

    const handleSegmentClick = (startStr) => {
        if (!videoRef?.current) return;

        let seconds = parseTimeToSeconds(startStr);
        console.log('Timeline click - Raw:', startStr, 'Parsed:', seconds);

        if (seconds === undefined || seconds === null || isNaN(seconds)) {
            seconds = 0;
        }

        try {
            if (Number.isFinite(seconds) && videoRef.current.fastSeek) {
                videoRef.current.fastSeek(seconds);
            } else {
                videoRef.current.currentTime = seconds;
            }
            if (videoRef.current.paused) {
                videoRef.current.play().catch(e => console.log('Playback prevented:', e));
            }
        } catch (err) {
            console.error('Seek error:', err);
        }
    }

    if (segments.length === 0) return null

    return (
        <div className="timeline-container">
            <div className="timeline-progress-track">
                <div
                    className="timeline-progress-fill"
                    style={{ width: `${progress}%` }}
                />
            </div>

            <div className="segments-strip">
                {segments.map((seg, idx) => {
                    const projectId = useProjectStore.getState().projectId;
                    const startOriginal = seg.start_time;
                    const endOriginal = seg.end_time;

                    const start = parseTimeToSeconds(startOriginal)
                    const end = parseTimeToSeconds(endOriginal)
                    const duration = end - start
                    const widthPct = (duration / totalDuration) * 100
                    const bgUrl = fixImageUrl(seg.thumbnail);

                    return (
                        <div
                            key={`${projectId}-${seg.id}`}
                            className="segment-block"
                            style={{
                                flexBasis: `${widthPct}%`,
                                backgroundImage: bgUrl ? `url(${bgUrl})` : 'none',
                                backgroundSize: 'cover',
                                backgroundPosition: 'center'
                            }}
                            onClick={(e) => {
                                e.stopPropagation();
                                handleSegmentClick(startOriginal)
                            }}
                            title={`Scene ${idx + 1}: ${startOriginal} - ${endOriginal}`}
                        >
                            <div className="segment-overlay">
                                <span className="segment-number">{idx + 1}</span>
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default Timeline
