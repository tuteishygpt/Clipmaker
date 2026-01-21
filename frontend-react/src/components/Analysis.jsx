import { useProjectStore } from '../stores/projectStore'

function Analysis() {
    const { analysis, loadAnalysis, projectId } = useProjectStore()

    const handleRefresh = () => {
        if (projectId) {
            loadAnalysis()
        }
    }

    if (!analysis || Object.keys(analysis).length === 0) {
        return (
            <section className="panel analysis-panel">
                <div className="analysis-header">
                    <h2>Analysis Data</h2>
                    <button onClick={handleRefresh} className="secondary-btn small">
                        Refresh
                    </button>
                </div>
                <div className="analysis-scroll-area">
                    <p className="muted">No analysis data loaded.</p>
                </div>
            </section>
        )
    }

    return (
        <section className="panel analysis-panel">
            <div className="analysis-header">
                <h2>Analysis Data</h2>
                <button onClick={handleRefresh} className="secondary-btn small">
                    Refresh
                </button>
            </div>

            <div className="analysis-scroll-area">
                {/* Summary */}
                {analysis.summary && (
                    <AnalysisField label="Summary" value={analysis.summary} />
                )}

                {/* Narrative */}
                {analysis.global_visual_narrative && (
                    <AnalysisField label="Narrative" value={analysis.global_visual_narrative} />
                )}

                {/* Visual Style */}
                {analysis.visual_style_anchor && (
                    <AnalysisField label="Visual Style" value={analysis.visual_style_anchor} />
                )}

                {/* Duration */}
                {analysis.total_duration && (
                    <AnalysisField label="Duration" value={analysis.total_duration} />
                )}

                {/* Technical Stats */}
                {analysis.technical_stats && (
                    <div className="analysis-section">
                        <div className="analysis-label">Technical Stats</div>
                        <div className="technical-stats">
                            <div>
                                BPM: <span className="stat-value">{analysis.technical_stats.bpm ? Math.round(analysis.technical_stats.bpm) : 'N/A'}</span>
                            </div>
                            <div>
                                Beats: {analysis.technical_stats.beat_times?.length || 0}
                            </div>
                            <div>
                                Energy: {analysis.technical_stats.energy_stats?.avg?.toFixed(4) || 'N/A'}
                            </div>
                        </div>
                    </div>
                )}

                {/* Segments Table */}
                {analysis.segments && analysis.segments.length > 0 && (
                    <div className="analysis-section">
                        <div className="analysis-label">LLM Segments</div>
                        <div className="segments-table-wrapper">
                            <table className="segments-table">
                                <thead>
                                    <tr>
                                        <th>Time</th>
                                        <th>Section</th>
                                        <th>Text / Lyrics</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {analysis.segments.map((seg, idx) => (
                                        <tr key={idx}>
                                            <td className="time-cell">{seg.start_time}-{seg.end_time}</td>
                                            <td className="section-cell">{seg.section_type || ''}</td>
                                            <td>{seg.text || seg.lyric_text || ''}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </section>
    )
}

function AnalysisField({ label, value }) {
    const displayValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : value

    return (
        <div className="analysis-section">
            <div className="analysis-label">{label}</div>
            <div className="analysis-value" style={{ whiteSpace: 'pre-wrap' }}>{displayValue}</div>
        </div>
    )
}

export default Analysis
