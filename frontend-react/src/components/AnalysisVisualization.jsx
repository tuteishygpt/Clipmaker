import { useEffect, useState } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { fixImageUrl } from '../utils'
import './AnalysisVisualization.css'

// Step names for display
const STEP_NAMES = {
    'analysis': 'Analyzing Audio',
    'segments': 'Generating Segments',
    'prompts': 'Creating Prompts',
    'images': 'Generating Images',
    'render': 'Rendering Video',
    'complete': 'Complete!'
}

// Step icons
const STEP_ICONS = {
    'analysis': '🎵',
    'segments': '📝',
    'prompts': '✨',
    'images': '🎨',
    'render': '🎬',
    'complete': '✅'
}

function AnalysisVisualization() {
    const { jobs, analysis, segments } = useProjectStore()
    const [animatedProgress, setAnimatedProgress] = useState(0)
    const [currentSlide, setCurrentSlide] = useState(0)

    const pipeJob = jobs.pipeline
    const isPipelineRunning = pipeJob?.status === 'RUNNING' || pipeJob?.status === 'RETRYING'
    const currentStep = pipeJob?.step || 'analysis'
    const progress = pipeJob?.progress || 0

    // Get segments with text (from analysis or generated segments)
    const llmSegments = analysis?.segments || []
    const genSegments = segments || []

    // Combine for slideshow - prefer generated segments if they have prompts
    const slideshowItems = genSegments.length > 0 && genSegments.some(s => s?.prompt?.image_prompt)
        ? genSegments.filter(s => s?.prompt?.image_prompt || s?.visual_intent)
        : llmSegments.filter(s => s?.text || s?.emotion)

    // Animate progress smoothly
    useEffect(() => {
        if (progress > animatedProgress) {
            const timer = setInterval(() => {
                setAnimatedProgress(prev => {
                    if (prev >= progress) {
                        clearInterval(timer)
                        return progress
                    }
                    return prev + 1
                })
            }, 30)
            return () => clearInterval(timer)
        } else {
            setAnimatedProgress(progress)
        }
    }, [progress])

    // Auto-rotate slides every 8 seconds
    useEffect(() => {
        if (slideshowItems.length <= 1) return

        const timer = setInterval(() => {
            setCurrentSlide(prev => (prev + 1) % slideshowItems.length)
        }, 8000)

        return () => clearInterval(timer)
    }, [slideshowItems.length])

    // Reset slide when segments change
    useEffect(() => {
        setCurrentSlide(0)
    }, [slideshowItems.length])

    if (!isPipelineRunning) {
        return null
    }

    const stepEntries = Object.entries(STEP_NAMES)
    const currentStepIndex = stepEntries.findIndex(([key]) => key === currentStep)
    const hasAnalysisData = analysis?.summary || analysis?.global_visual_narrative || analysis?.visual_style_anchor

    // Get current slide content
    const slide = slideshowItems[currentSlide]
    const isGenSegment = genSegments.length > 0 && genSegments.some(s => s?.prompt)

    return (
        <div className="analysis-visualization">
            {/* Header row - step + progress */}
            <div className="av-header-row">
                <div className="av-step-info">
                    <span className="av-icon">{STEP_ICONS[currentStep]}</span>
                    <span className="av-step-name">{STEP_NAMES[currentStep]}</span>
                </div>
                <div className="av-progress-bar">
                    <div className="av-progress-fill" style={{ width: `${animatedProgress}%` }} />
                </div>
                <span className="av-progress-pct">{animatedProgress}%</span>
            </div>

            {/* Mini step dots */}
            <div className="av-steps-mini">
                {stepEntries.slice(0, -1).map(([key], index) => (
                    <div
                        key={key}
                        className={`av-dot ${index < currentStepIndex ? 'done' : ''} ${key === currentStep ? 'active' : ''}`}
                        title={STEP_NAMES[key]}
                    />
                ))}
            </div>

            {/* Main content - two columns */}
            <div className="av-main-content">
                {/* LEFT: Analysis Data - ALWAYS visible when available */}
                <div className="av-analysis-data">
                    {/* Stats row */}
                    {(analysis?.technical_stats?.bpm || analysis?.total_duration > 0) && (
                        <div className="av-stats-row">
                            {analysis?.technical_stats?.bpm && (
                                <div className="av-stat">
                                    <span className="av-stat-val">{Math.round(analysis.technical_stats.bpm)}</span>
                                    <span className="av-stat-lbl">BPM</span>
                                </div>
                            )}
                            {analysis?.total_duration > 0 && (
                                <div className="av-stat">
                                    <span className="av-stat-val">{Math.round(analysis.total_duration)}s</span>
                                    <span className="av-stat-lbl">Duration</span>
                                </div>
                            )}
                            {llmSegments.length > 0 && (
                                <div className="av-stat">
                                    <span className="av-stat-val">{llmSegments.length}</span>
                                    <span className="av-stat-lbl">Segments</span>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Summary - always show */}
                    {analysis?.summary && (
                        <div className="av-text-block">
                            <span className="av-label">📋 Summary</span>
                            <p className="av-text">{analysis.summary}</p>
                        </div>
                    )}

                    {/* Narrative - always show */}
                    {analysis?.global_visual_narrative && (
                        <div className="av-text-block">
                            <span className="av-label">🎭 Narrative</span>
                            <p className="av-text">{analysis.global_visual_narrative}</p>
                        </div>
                    )}

                    {/* Style - always show */}
                    {analysis?.visual_style_anchor && (
                        <div className="av-text-block av-style-block">
                            <span className="av-label">🎨 Visual Style</span>
                            <p className="av-text">{analysis.visual_style_anchor}</p>
                        </div>
                    )}

                    {/* Loading state if no data */}
                    {!hasAnalysisData && !analysis?.technical_stats && (
                        <div className="av-loading">
                            <span>Analyzing audio</span>
                            <div className="av-dots"><span /><span /><span /></div>
                        </div>
                    )}
                </div>

                {/* RIGHT: Slideshow for segments */}
                {slideshowItems.length > 0 && (
                    <div className="av-slideshow">
                        <div className="av-slide-header">
                            <span className="av-slide-title">
                                {isGenSegment ? '🎬 Scene' : '🎞️ Segment'} {currentSlide + 1}/{slideshowItems.length}
                            </span>
                            <div className="av-slide-dots">
                                {slideshowItems.slice(0, 12).map((_, idx) => (
                                    <span
                                        key={idx}
                                        className={`av-slide-dot ${idx === currentSlide ? 'active' : ''}`}
                                        onClick={() => setCurrentSlide(idx)}
                                    />
                                ))}
                                {slideshowItems.length > 12 && <span className="av-slide-more">+{slideshowItems.length - 12}</span>}
                            </div>
                        </div>

                        <div className="av-slide-content" key={currentSlide}>
                            {/* Time & Type */}
                            <div className="av-slide-meta">
                                <span className="av-slide-time">
                                    ⏱️ {slide?.start_time?.toFixed(1) || '0.0'}s - {slide?.end_time?.toFixed(1) || '?'}s
                                </span>
                                {(slide?.section_type || slide?.emotion) && (
                                    <span className="av-slide-type">
                                        {slide?.section_type || slide?.emotion}
                                    </span>
                                )}
                            </div>

                            {/* Text content */}
                            {slide?.text && (
                                <div className="av-slide-text">
                                    <span className="av-mini-label">Text/Lyrics:</span>
                                    <p>{slide.text}</p>
                                </div>
                            )}

                            {/* Visual Intent (for generated segments) */}
                            {slide?.visual_intent && (
                                <div className="av-slide-text">
                                    <span className="av-mini-label">Visual Intent:</span>
                                    <p>{slide.visual_intent}</p>
                                </div>
                            )}

                            {/* Prompt (for generated segments) */}
                            {slide?.prompt?.image_prompt && (
                                <div className="av-slide-text av-prompt">
                                    <span className="av-mini-label">Image Prompt:</span>
                                    <p>{slide.prompt.image_prompt}</p>
                                </div>
                            )}

                            {/* Environment/Instrumentation for LLM segments */}
                            {(slide?.acoustic_environment || slide?.instrumentation) && (
                                <div className="av-slide-extra">
                                    {slide?.instrumentation && <span>🎸 {slide.instrumentation}</span>}
                                    {slide?.acoustic_environment && <span>🏠 {slide.acoustic_environment}</span>}
                                </div>
                            )}

                            {/* Thumbnail if available */}
                            {slide?.thumbnail && (
                                <div className="av-slide-thumb">
                                    <img src={fixImageUrl(slide.thumbnail)} alt="" />
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default AnalysisVisualization
