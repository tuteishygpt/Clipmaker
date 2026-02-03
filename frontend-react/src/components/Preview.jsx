import { useRef, useEffect, useState } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { getDownloadUrl } from '../api'
import { fixImageUrl } from '../utils'
import Timeline from './Timeline'
import AnalysisVisualization from './AnalysisVisualization'

function Preview() {
    const { projectId, videoOutput, segments, jobs } = useProjectStore()
    const videoRef = useRef(null)
    const [imgError, setImgError] = useState(false)

    // Check if pipeline is running
    const pipeJob = jobs.pipeline
    const isPipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'

    // Reset error when project or segments change
    useEffect(() => {
        setImgError(false)
    }, [projectId, segments])

    // Determine what to show
    const hasVideo = !!videoOutput
    const safeSegments = Array.isArray(segments) ? segments : []
    const lastImage = safeSegments.filter(s => s && s.thumbnail).slice(-1)[0]?.thumbnail

    return (
        <section className="panel cinema-panel">
            <div className="preview-box">
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
            </div>

            <Timeline videoRef={videoRef} />
        </section>
    )
}

export default Preview
