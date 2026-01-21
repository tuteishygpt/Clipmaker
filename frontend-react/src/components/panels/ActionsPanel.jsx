import { useState } from 'react'
import { useProjectStore } from '../../stores/projectStore'
import ProgressBar from '../common/ProgressBar'

function ActionsPanel() {
    const {
        projectId,
        jobs,
        runPipeline,
        renderVideo,
        recalculateTimings
    } = useProjectStore()

    const [recalculating, setRecalculating] = useState(false)

    const pipeJob = jobs.pipeline
    const renderJob = jobs.render

    const handleRunPipeline = async () => {
        if (!projectId) {
            alert('Create a project first.')
            return
        }
        await runPipeline()
    }

    const handleRender = async () => {
        if (!projectId) {
            alert('Create a project first.')
            return
        }
        await renderVideo()
    }

    const handleRecalculate = async () => {
        if (!projectId) {
            alert('Select a project first')
            return
        }

        if (!confirm('This will evenly redistribute all existing scenes across the audio duration. Continue?')) {
            return
        }

        setRecalculating(true)
        try {
            const result = await recalculateTimings()
            if (result) {
                alert(result.message || 'Timings recalculated!')
            }
        } finally {
            setRecalculating(false)
        }
    }

    // Render duration text
    let renderDurationText = ''
    if (renderJob?.status === 'DONE' && renderJob.render_duration_seconds) {
        const secs = renderJob.render_duration_seconds
        if (secs >= 60) {
            const mins = Math.floor(secs / 60)
            const remainSecs = Math.round(secs % 60)
            renderDurationText = ` (${mins}m ${remainSecs}s)`
        } else {
            renderDurationText = ` (${Math.round(secs)}s)`
        }
    }

    return (
        <section className="panel">
            <h2>Actions</h2>

            <button
                onClick={handleRunPipeline}
                className="full-width"
                style={{ marginBottom: '10px' }}
            >
                Generate Scenes
            </button>

            <button
                onClick={handleRender}
                className="full-width"
                style={{ marginBottom: '10px' }}
            >
                Render Video
            </button>

            <button
                onClick={handleRecalculate}
                className="secondary-btn full-width"
                disabled={recalculating}
            >
                {recalculating ? 'Recalculating...' : 'Recalculate Timings'}
            </button>

            {/* Pipeline Progress */}
            {pipeJob && (pipeJob.status === 'RUNNING' || pipeJob.status === 'RETRYING') && (
                <ProgressBar
                    label="Pipeline"
                    progress={pipeJob.progress || 0}
                    step={pipeJob.step}
                />
            )}

            {pipeJob?.status === 'DONE' && (
                <div className="muted" style={{ marginTop: '10px' }}>
                    Pipeline complete! Video is ready.
                </div>
            )}

            {pipeJob?.status === 'FAILED' && (
                <div className="error" style={{ marginTop: '10px' }}>
                    Error: {pipeJob.error || 'Pipeline failed'}
                </div>
            )}

            {/* Render Progress */}
            {renderJob?.status === 'RUNNING' && (
                <ProgressBar
                    label="Rendering"
                    progress={renderJob.progress || 0}
                />
            )}

            {renderJob?.status === 'DONE' && (
                <div className="muted" style={{ marginTop: '10px' }}>
                    Render complete!{renderDurationText}
                </div>
            )}

            {renderJob?.status === 'FAILED' && (
                <div className="error" style={{ marginTop: '10px' }}>
                    Render failed
                </div>
            )}
        </section>
    )
}

export default ActionsPanel
