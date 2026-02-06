import { useState, useEffect } from 'react'
import { useProjectStore } from '../stores/projectStore'
import './AnalysisModal.css'

function AnalysisModal({ inSidebar = false, onClose }) {
    const [isOpen, setIsOpen] = useState(false)
    const { analysis, loadAnalysis, projectId } = useProjectStore()

    // Auto-load analysis when in sidebar mode
    useEffect(() => {
        if (inSidebar && projectId) {
            loadAnalysis()
        }
    }, [inSidebar, projectId, loadAnalysis])

    const handleOpen = () => {
        if (projectId) {
            loadAnalysis()
        }
        setIsOpen(true)
    }

    const handleClose = () => {
        setIsOpen(false)
        if (onClose) onClose()
    }

    const hasData = analysis && Object.keys(analysis).length > 0

    // Render content for both modal and sidebar
    const renderContent = () => (
        <>
            {/* Stats Grid */}
            {(analysis.technical_stats || analysis.total_duration) && (
                <div className="am-section">
                    <h3>📈 Technical Stats</h3>
                    <div className="am-stats-grid">
                        {analysis.technical_stats?.bpm && (
                            <div className="am-stat">
                                <span className="am-stat-value">{Math.round(analysis.technical_stats.bpm)}</span>
                                <span className="am-stat-label">BPM</span>
                            </div>
                        )}
                        {analysis.technical_stats?.beat_times?.length > 0 && (
                            <div className="am-stat">
                                <span className="am-stat-value">{analysis.technical_stats.beat_times.length}</span>
                                <span className="am-stat-label">Beats</span>
                            </div>
                        )}
                        {analysis.total_duration > 0 && (
                            <div className="am-stat">
                                <span className="am-stat-value">{analysis.total_duration.toFixed(1)}s</span>
                                <span className="am-stat-label">Duration</span>
                            </div>
                        )}
                        {analysis.technical_stats?.energy_stats?.avg && (
                            <div className="am-stat">
                                <span className="am-stat-value">{analysis.technical_stats.energy_stats.avg.toFixed(3)}</span>
                                <span className="am-stat-label">Avg Energy</span>
                            </div>
                        )}
                        {analysis.technical_stats?.tempo_stability && (
                            <div className="am-stat">
                                <span className="am-stat-value">{(analysis.technical_stats.tempo_stability * 100).toFixed(0)}%</span>
                                <span className="am-stat-label">Tempo Stability</span>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Summary */}
            {analysis.summary && (
                <div className="am-section">
                    <h3>📋 Summary</h3>
                    <p className="am-text">{analysis.summary}</p>
                </div>
            )}

            {/* Narrative */}
            {analysis.global_visual_narrative && (
                <div className="am-section">
                    <h3>🎭 Visual Narrative</h3>
                    <p className="am-text">{analysis.global_visual_narrative}</p>
                </div>
            )}

            {/* Visual Style */}
            {analysis.visual_style_anchor && (
                <div className="am-section">
                    <h3>🎨 Visual Style</h3>
                    <p className="am-text am-style">{analysis.visual_style_anchor}</p>
                </div>
            )}

            {/* Character Description */}
            {analysis.character_description && (
                <div className="am-section">
                    <h3>👤 Character Description</h3>
                    <p className="am-text">{analysis.character_description}</p>
                </div>
            )}

            {/* Segments Table */}
            {analysis.segments && analysis.segments.length > 0 && (
                <div className="am-section">
                    <h3>🎞️ LLM Segments ({analysis.segments.length})</h3>
                    <div className="am-table-wrapper">
                        <table className="am-table">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Time</th>
                                    <th>Section</th>
                                    <th>Emotion</th>
                                    <th>Text / Lyrics</th>
                                </tr>
                            </thead>
                            <tbody>
                                {analysis.segments.map((seg, idx) => (
                                    <tr key={idx}>
                                        <td>{idx + 1}</td>
                                        <td className="am-time">{seg.start_time?.toFixed(1)}s - {seg.end_time?.toFixed(1)}s</td>
                                        <td>{seg.section_type || '-'}</td>
                                        <td>{seg.emotion || '-'}</td>
                                        <td className="am-text-cell">{seg.text || seg.lyric_text || '-'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </>
    )

    // Sidebar mode - render inline
    if (inSidebar) {
        return (
            <div className="am-sidebar">
                <div className="am-sidebar-header">
                    <h3>📊 Analysis</h3>
                    <div className="am-header-actions">
                        <button onClick={() => loadAnalysis()} className="am-refresh-btn">
                            🔄
                        </button>
                        {onClose && (
                            <button onClick={onClose} className="am-close-btn">✕</button>
                        )}
                    </div>
                </div>

                <div className="am-sidebar-content">
                    {!hasData ? (
                        <div className="am-empty">
                            <p>No analysis data available.</p>
                            <p className="muted">Run "Generate Scenes" to analyze your audio.</p>
                        </div>
                    ) : renderContent()}
                </div>
            </div>
        )
    }

    // Modal mode - original behavior
    return (
        <>
            {/* Trigger button */}
            <button
                className="preview-btn"
                onClick={handleOpen}
                title="View Analysis Data"
            >
                <span className="btn-icon-emoji">📊</span>
                Analysis
            </button>

            {/* Modal overlay */}
            {isOpen && (
                <div className="analysis-modal-overlay" onClick={handleClose}>
                    <div className="analysis-modal" onClick={e => e.stopPropagation()}>
                        <div className="am-header">
                            <h2>📊 Analysis Data</h2>
                            <div className="am-header-actions">
                                <button onClick={() => loadAnalysis()} className="am-refresh-btn">
                                    🔄 Refresh
                                </button>
                                <button onClick={handleClose} className="am-close-btn">✕</button>
                            </div>
                        </div>

                        <div className="am-content">
                            {!hasData ? (
                                <div className="am-empty">
                                    <p>No analysis data available.</p>
                                    <p className="muted">Run "Generate Scenes" to analyze your audio.</p>
                                </div>
                            ) : renderContent()}
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}

export default AnalysisModal

