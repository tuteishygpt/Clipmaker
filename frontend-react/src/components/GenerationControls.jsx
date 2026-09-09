import { useProjectStore } from '../stores/projectStore'
import { useAuthStore } from '../stores/authStore'
import { useBillingStore } from '../stores/billingStore'
import { isSupabaseConfigured } from '../lib/supabase'
import ProgressBar from './common/ProgressBar'
import { useTranslation } from '../i18n'

function GenerationControls() {
    const { t } = useTranslation()
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
                addToast(generationBlockReason || t('studio.generation.cannotGenerate'), 'error')
                return
            }

            // Note: Credits will be deducted per-image by the backend
            // Here we just verify eligibility
            if (credits < 1) {
                addToast(t('studio.generation.insufficientCredits'), 'error')
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
            <h2>{t('studio.generation.title')}</h2>

            {/* Credits info for logged-in users */}
            {isSupabaseConfigured() && user && (
                <div className={`credits-info-box ${isGenerationBlocked ? 'warning' : ''}`}>
                    <div className="credits-display-inline">
                        <span className="credits-icon">💎</span>
                        <span className="credits-count">{t('studio.generation.credits', { count: credits })}</span>
                    </div>
                    {isGenerationBlocked && (
                        <div className="credits-warning">
                            <span className="warning-icon">⚠️</span>
                            <span>{generationBlockReason}</span>
                        </div>
                    )}
                    {!isGenerationBlocked && (
                        <div className="credits-hint">
                            {t('studio.generation.creditsUsed', { count: estimatedCredits })}
                        </div>
                    )}
                </div>
            )}

            {/* 1. Generate Scenes */}
            <div className={`control-step ${hasScenes ? 'completed' : ''} ${isGenerationBlocked ? 'blocked' : ''}`}>
                <div className="step-header">
                    <div className="step-number">1</div>
                    <div className="step-info">
                        <h3>{t('studio.generation.step1Title')}</h3>
                        <p>{t('studio.generation.step1Desc')}</p>
                    </div>
                </div>

                {isPipelineRunning ? (
                    <div className="job-progress">
                        <ProgressBar
                            label={t('studio.generation.step1Progress')}
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
                                {t('studio.generation.genUnavailable')}
                            </>
                        ) : hasScenes ? (
                            t('studio.generation.regenAll')
                        ) : (
                            t('studio.generation.startGen')
                        )}
                    </button>
                )}

                {isGenerationBlocked && (
                    <a href="/cabinet" className="btn-upgrade-inline">
                        {t('studio.generation.upgradeBtn')}
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
                        {t('studio.generation.recalcTimings')}
                    </button>
                </div>
            )}

            {/* 2. Render Video */}
            <div className={`control-step ${hasScenes ? '' : 'disabled'}`}>
                <div className="step-header">
                    <div className="step-number">2</div>
                    <div className="step-info">
                        <h3>{t('studio.generation.step2Title')}</h3>
                        <p>{t('studio.generation.step2Desc')}</p>
                    </div>
                </div>

                {isRenderRunning ? (
                    <div className="job-progress">
                        <ProgressBar
                            label={t('studio.generation.step2Progress')}
                            progress={renderJob.progress || 0}
                        />
                    </div>
                ) : (
                    <button
                        className="btn-accent full-width"
                        onClick={handleRenderVideo}
                        disabled={!hasScenes || isRenderRunning || isPipelineRunning || isLoading}
                    >
                        {t('studio.generation.renderFinal')}
                    </button>
                )}
            </div>

        </div>
    )
}

export default GenerationControls

