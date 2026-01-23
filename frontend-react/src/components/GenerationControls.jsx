import { useProjectStore } from '../stores/projectStore'
import { useAuthStore } from '../stores/authStore'
import { useBillingStore } from '../stores/billingStore'
import { isSupabaseConfigured } from '../lib/supabase'
import ProgressBar from './common/ProgressBar'

function GenerationControls() {
    const {
        projectId,
        jobs,
        project,
        segments,
        runPipeline,
        renderVideo,
        recalculateTimings,
        addToast,
        isLoading
    } = useProjectStore()

    const { user } = useAuthStore()
    const { credits, canGenerate, generationBlockReason, deductCredits } = useBillingStore()

    const pipeJob = jobs.pipeline
    const renderJob = jobs.render

    const isPipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'
    const isRenderRunning = renderJob?.status === 'RUNNING'

    const hasScenes = project?.status === 'ready' || project?.status === 'completed' || pipeJob?.status === 'DONE'

    // Calculate estimated credits needed (1 per segment, minimum 1)
    const estimatedCredits = Math.max(1, segments.length || 5)

    // Check if user can generate (either no Supabase, or has credits + subscription)
    const isGenerationBlocked = isSupabaseConfigured() && user && !canGenerate

    const handleRunPipeline = async () => {
        // If Supabase is configured and user is logged in, check credits
        if (isSupabaseConfigured() && user) {
            if (!canGenerate) {
                addToast(generationBlockReason || 'Cannot generate at this time', 'error')
                return
            }

            // Note: Credits will be deducted per-image by the backend
            // Here we just verify eligibility
            if (credits < 1) {
                addToast('Insufficient credits. Please purchase more to continue.', 'error')
                return
            }
        }

        await runPipeline()
    }

    const handleRenderVideo = async () => {
        // Rendering doesn't cost credits (already paid for generation)
        await renderVideo()
    }

    return (
        <div className="generation-controls">
            <h2>Generation Controls</h2>

            {/* Credits info for logged-in users */}
            {isSupabaseConfigured() && user && (
                <div className={`credits-info-box ${isGenerationBlocked ? 'warning' : ''}`}>
                    <div className="credits-display-inline">
                        <span className="credits-icon">💎</span>
                        <span className="credits-count">{credits} credits</span>
                    </div>
                    {isGenerationBlocked && (
                        <div className="credits-warning">
                            <span className="warning-icon">⚠️</span>
                            <span>{generationBlockReason}</span>
                        </div>
                    )}
                    {!isGenerationBlocked && (
                        <div className="credits-hint">
                            ~{estimatedCredits} credits will be used
                        </div>
                    )}
                </div>
            )}

            {/* 1. Generate Scenes */}
            <div className={`control-step ${hasScenes ? 'completed' : ''} ${isGenerationBlocked ? 'blocked' : ''}`}>
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
                        onClick={handleRunPipeline}
                        disabled={!projectId || isPipelineRunning || isRenderRunning || isGenerationBlocked || isLoading}
                    >
                        {isGenerationBlocked ? (
                            <>
                                <span className="lock-icon">🔒</span>
                                Generation Unavailable
                            </>
                        ) : hasScenes ? (
                            'Regenerate All Scenes'
                        ) : (
                            'Start Generation'
                        )}
                    </button>
                )}

                {isGenerationBlocked && (
                    <a href="/cabinet" className="btn-upgrade-inline">
                        Upgrade to Continue →
                    </a>
                )}
            </div>

            {hasScenes && (
                <div className="mid-controls">
                    <button
                        className="btn-text"
                        onClick={recalculateTimings}
                        disabled={isPipelineRunning || isRenderRunning || isLoading}
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
                        onClick={handleRenderVideo}
                        disabled={!hasScenes || isRenderRunning || isPipelineRunning || isLoading}
                    >
                        Render Final Video
                    </button>
                )}
            </div>
        </div>
    )
}

export default GenerationControls
