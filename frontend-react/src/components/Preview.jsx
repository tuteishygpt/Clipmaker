import { useRef, useEffect, useState } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { getDownloadUrl } from '../api'
import { fixImageUrl } from '../utils'
import Timeline from './Timeline'

function Preview() {
    const { projectId, videoOutput, segments } = useProjectStore()
    const videoRef = useRef(null)
    const [imgError, setImgError] = useState(false)

    // Reset error when project or segments change
    useEffect(() => {
        setImgError(false)
    }, [projectId, segments])

    // Determine what to show
    const hasVideo = !!videoOutput
    const lastImage = segments.filter(s => s.thumbnail).slice(-1)[0]?.thumbnail

    return (
        <section className="panel cinema-panel">
            <div className="preview-box">
                {!hasVideo && (!lastImage || imgError) && (
                    <div className="preview-placeholder">
                        <div className="placeholder-icon">🎬</div>
                        <p>{imgError ? "Preview Image Error" : "Preview will appear here"}</p>
                    </div>
                )}

                {!hasVideo && lastImage && !imgError && (
                    <img
                        src={fixImageUrl(lastImage)}
                        alt="Last generated scene"
                        className="preview-image"
                        onError={() => setImgError(true)}
                    />
                )}

                {hasVideo && (
                    <video
                        ref={videoRef}
                        src={videoOutput}
                        controls
                        className="preview-video"
                    />
                )}
            </div>

            <Timeline videoRef={videoRef} />

            <div className="preview-controls">
                {hasVideo && projectId && (
                    <a
                        href={getDownloadUrl(projectId)}
                        download
                        className="button-link"
                    >
                        Download Video
                    </a>
                )}
            </div>
        </section>
    )
}

export default Preview
