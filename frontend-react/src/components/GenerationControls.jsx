import { useProjectStore } from '../stores/projectStore'
import ProgressBar from './common/ProgressBar'

function GenerationControls() {
    const {
        projectId,
        jobs,
        project,
        runPipeline,
        renderVideo,
        recalculateTimings
    } = useProjectStore()

    const pipeJob = jobs.pipeline
    const renderJob = jobs.render

    const isPipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'
    const isRenderRunning = renderJob?.status === 'RUNNING'

    const hasScenes = project?.status === 'ready' || project?.status === 'completed' || pipeJob?.status === 'DONE'

    return (
        <div className="generation-controls">
            <h2>Generation Controls</h2>

            {/* 1. Generate Scenes */}
            <div className={`control-step ${hasScenes ? 'completed' : ''}`}>
                <div className="step-header">
                    <div className="step-number">1</div>
                    <div className="step-info">
                        <h3>Generate Scenes</h3>
                        <p>AI will analyze lyrics/beats and create scene descriptions</p>
                    </div>
                </div>

                {isPipelineRunning ? (
                    <div className="job-progress">
                        <ProgressBar
                            label="Generating Scenes"
                            progress={pipeJob.progress || 0}
                            step={pipeJob.step}
                        />
                    </div>
                ) : (
                    <button
                        className={`btn-primary full-width ${hasScenes ? 'btn-outline' : ''}`}
                        onClick={runPipeline}
                        disabled={!projectId || isPipelineRunning || isRenderRunning}
                    >
                        {hasScenes ? 'Regenerate All Scenes' : 'Start Generation'}
                    </button>
                )}
            </div>

            {hasScenes && (
                <div className="mid-controls">
                    <button
                        className="btn-text"
                        onClick={recalculateTimings}
                        disabled={isPipelineRunning || isRenderRunning}
                    >
                        ⏱️ Recalculate Timings
                    </button>
                </div>
            )}

            {/* 2. Render Video */}
            <div className={`control-step ${hasScenes ? '' : 'disabled'}`}>
                <div className="step-header">
                    <div className="step-number">2</div>
                    <div className="step-info">
                        <h3>Render Video</h3>
                        <p>Compile all scenes into the final video</p>
                    </div>
                </div>

                {isRenderRunning ? (
                    <div className="job-progress">
                        <ProgressBar
                            label="Rendering Video"
                            progress={renderJob.progress || 0}
                        />
                    </div>
                ) : (
                    <button
                        className="btn-accent full-width"
                        onClick={renderVideo}
                        disabled={!hasScenes || isRenderRunning || isPipelineRunning}
                    >
                        Render Final Video
                    </button>
                )}
            </div>
        </div>
    )
}

export default GenerationControls
