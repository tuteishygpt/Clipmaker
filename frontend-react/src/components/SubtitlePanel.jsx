import { useState, useEffect } from 'react'
import './SubtitlePanel.css'

const API_BASE = 'http://localhost:8000'

// Font categories
const FONT_CATEGORIES = {
    'Sans-serif': ['Montserrat', 'Inter', 'Roboto', 'Open Sans', 'Poppins', 'Outfit'],
    'Serif': ['Playfair Display', 'Merriweather', 'Lora'],
    'Display': ['Bebas Neue', 'Anton', 'Bangers', 'Russo One'],
    'Monospace': ['Fira Code', 'JetBrains Mono']
}

const DEFAULT_STYLING = {
    font_family: 'Montserrat',
    font_size: 48,
    font_weight: 'bold',
    font_color: '#FFFFFF',
    stroke_color: '#000000',
    stroke_width: 3,
    background_enabled: false,
    background_color: '#000000',
    background_opacity: 0.7,
    background_padding: 12,
    background_radius: 8,
    position: 'bottom',
    margin_y: 60,
    text_align: 'center',
    max_width_percent: 90,
    uppercase: false,
    animation: 'none',
    highlight_font_color: '#FFFFFF',
    highlight_bg_color: '#6e00ff',
    highlight_bg_radius: 8,
    highlight_bg_padding: 8,
    highlight_active_word: true
}

// Preset styles for quick selection
const STYLE_PRESETS = [
    { name: 'Classic', icon: '📺', styling: { font_family: 'Arial', font_color: '#FFFFFF', stroke_color: '#000000', stroke_width: 2, background_enabled: false } },
    { name: 'Netflix', icon: '🎬', styling: { font_family: 'Montserrat', font_color: '#FFFFFF', stroke_color: '#000000', stroke_width: 0, background_enabled: true, background_color: '#000000', background_opacity: 0.75, background_padding: 8, background_radius: 4 } },
    { name: 'YouTube', icon: '▶️', styling: { font_family: 'Roboto', font_color: '#FFFFFF', stroke_color: '#000000', stroke_width: 0, background_enabled: true, background_color: '#000000', background_opacity: 0.8, background_padding: 4, background_radius: 2 } },
    { name: 'Neon', icon: '💜', styling: { font_family: 'Poppins', font_color: '#FF00FF', stroke_color: '#00FFFF', stroke_width: 2, background_enabled: false } },
    { name: 'Minimal', icon: '✨', styling: { font_family: 'Inter', font_color: '#FFFFFF', stroke_color: '#000000', stroke_width: 1, background_enabled: false } },
    { name: 'Bold', icon: '💪', styling: { font_family: 'Bebas Neue', font_color: '#FFFF00', stroke_color: '#000000', stroke_width: 3, background_enabled: false, uppercase: true } },
]

export default function SubtitlePanel({ projectId, isExpanded, onToggle }) {
    const [entries, setEntries] = useState([])
    const [styling, setStyling] = useState(DEFAULT_STYLING)
    const [loading, setLoading] = useState(false)
    const [generating, setGenerating] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)
    const [hasChanges, setHasChanges] = useState(false)
    const [activeSection, setActiveSection] = useState('entries')
    const [expandedGroup, setExpandedGroup] = useState('text') // text, background, position

    useEffect(() => {
        if (projectId) {
            loadSubtitles()
        }
    }, [projectId])

    const loadSubtitles = async () => {
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`)
            if (res.ok) {
                const data = await res.json()
                setEntries(data.entries || [])
                if (data.styling) setStyling({ ...DEFAULT_STYLING, ...data.styling })
            }
        } catch (err) {
            console.error('Failed to load subtitles:', err)
        } finally {
            setLoading(false)
        }
    }

    const generateSubtitles = async () => {
        setGenerating(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: 'auto' })
            })
            if (!res.ok) {
                const err = await res.json()
                throw new Error(err.detail || 'Generation failed')
            }
            const data = await res.json()
            setEntries(data.entries || [])
            if (data.styling) setStyling({ ...DEFAULT_STYLING, ...data.styling })
            setHasChanges(false)
        } catch (err) {
            setError(err.message)
        } finally {
            setGenerating(false)
        }
    }

    const saveSubtitles = async () => {
        setSaving(true)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ entries, styling })
            })
            if (res.ok) setHasChanges(false)
        } catch (err) {
            setError(err.message)
        } finally {
            setSaving(false)
        }
    }

    const importSrt = async (file) => {
        const formData = new FormData()
        formData.append('srt_file', file)
        setLoading(true)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles/import`, {
                method: 'POST',
                body: formData
            })
            if (res.ok) {
                const data = await res.json()
                setEntries(data.entries || [])
                setHasChanges(false)
            }
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const deleteSubtitles = async () => {
        if (!confirm('Delete all subtitles?')) return
        try {
            await fetch(`${API_BASE}/projects/${projectId}/subtitles`, { method: 'DELETE' })
            setEntries([])
            setStyling(DEFAULT_STYLING)
            setHasChanges(false)
        } catch (err) {
            setError(err.message)
        }
    }

    const updateEntry = (id, field, value) => {
        setEntries(prev => prev.map(e => e.id === id ? { ...e, [field]: value } : e))
        setHasChanges(true)
    }

    const deleteEntry = (id) => {
        setEntries(prev => prev.filter(e => e.id !== id))
        setHasChanges(true)
    }

    const updateStyling = (key, value) => {
        setStyling(prev => ({ ...prev, [key]: value }))
        setHasChanges(true)
    }

    const applyPreset = (preset) => {
        setStyling(prev => ({ ...prev, ...preset.styling }))
        setHasChanges(true)
    }

    // Export styling for preview overlay
    useEffect(() => {
        if (typeof window !== 'undefined') {
            window.__subtitleStyling = styling
            window.__subtitleEntries = entries
        }
    }, [styling, entries])

    if (!isExpanded) return null

    const toggleGroup = (group) => {
        setExpandedGroup(expandedGroup === group ? null : group)
    }

    return (
        <div className="subtitle-panel">
            <div className="subtitle-panel-header">
                <div className="subtitle-panel-tabs">
                    <button
                        className={activeSection === 'entries' ? 'active' : ''}
                        onClick={() => setActiveSection('entries')}
                    >
                        <span className="tab-icon">📝</span>
                        Subtitles ({entries.length})
                    </button>
                    <button
                        className={activeSection === 'styling' ? 'active' : ''}
                        onClick={() => setActiveSection('styling')}
                    >
                        <span className="tab-icon">🎨</span>
                        Styling
                    </button>
                </div>
                <div className="subtitle-panel-actions">
                    <button
                        className="btn-gen"
                        onClick={generateSubtitles}
                        disabled={generating || loading}
                    >
                        {generating ? <span className="spinner" /> : '🎤'} Generate
                    </button>
                    <label className="btn-import">
                        📄 Import
                        <input type="file" accept=".srt" hidden onChange={(e) => e.target.files?.[0] && importSrt(e.target.files[0])} />
                    </label>
                    {entries.length > 0 && (
                        <>
                            <a href={`${API_BASE}/projects/${projectId}/subtitles/download`} className="btn-icon" title="Download SRT">⬇️</a>
                            <button className="btn-icon btn-danger" onClick={deleteSubtitles} title="Delete all">🗑️</button>
                        </>
                    )}
                    {hasChanges && (
                        <button className="btn-save" onClick={saveSubtitles} disabled={saving}>
                            {saving ? <span className="spinner" /> : '💾'} Save
                        </button>
                    )}
                    <button className="btn-close" onClick={onToggle}>✕</button>
                </div>
            </div>

            {error && <div className="subtitle-error">{error} <button onClick={() => setError(null)}>×</button></div>}

            <div className="subtitle-panel-content">
                {loading ? (
                    <div className="subtitle-loading">
                        <span className="spinner large" />
                        <span>Loading subtitles...</span>
                    </div>
                ) : activeSection === 'entries' ? (
                    <div className="entries-compact">
                        {entries.length === 0 ? (
                            <div className="no-entries">
                                <span className="empty-icon">💬</span>
                                <p>No subtitles yet</p>
                                <span className="empty-hint">Click "Generate" to create from audio or "Import" an SRT file</span>
                            </div>
                        ) : (
                            <div className="entries-scroll">
                                {entries.map(entry => (
                                    <div key={entry.id} className="entry-row">
                                        <span className="entry-num">#{entry.id}</span>
                                        <input
                                            type="text"
                                            className="entry-time"
                                            value={entry.start_time}
                                            onChange={(e) => updateEntry(entry.id, 'start_time', e.target.value)}
                                        />
                                        <span className="entry-arrow">→</span>
                                        <input
                                            type="text"
                                            className="entry-time"
                                            value={entry.end_time}
                                            onChange={(e) => updateEntry(entry.id, 'end_time', e.target.value)}
                                        />
                                        <input
                                            type="text"
                                            className="entry-text"
                                            value={entry.text}
                                            onChange={(e) => updateEntry(entry.id, 'text', e.target.value)}
                                        />
                                        <button className="entry-delete" onClick={() => deleteEntry(entry.id)}>×</button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="styling-modern">
                        {/* Quick Presets */}
                        <div className="style-presets">
                            {STYLE_PRESETS.map(preset => (
                                <button
                                    key={preset.name}
                                    className="preset-btn"
                                    onClick={() => applyPreset(preset)}
                                    title={preset.name}
                                >
                                    <span className="preset-icon">{preset.icon}</span>
                                    <span className="preset-name">{preset.name}</span>
                                </button>
                            ))}
                        </div>

                        {/* Text Styling Group */}
                        <div className={`style-group ${expandedGroup === 'text' ? 'expanded' : ''}`}>
                            <button className="group-header" onClick={() => toggleGroup('text')}>
                                <span className="group-icon">🔤</span>
                                <span className="group-title">Text Style</span>
                                <span className="group-chevron">{expandedGroup === 'text' ? '▼' : '▶'}</span>
                            </button>
                            {expandedGroup === 'text' && (
                                <div className="group-content">
                                    <div className="control-row">
                                        <label>Font</label>
                                        <select
                                            value={styling.font_family}
                                            onChange={(e) => updateStyling('font_family', e.target.value)}
                                            style={{ fontFamily: styling.font_family }}
                                        >
                                            {Object.entries(FONT_CATEGORIES).map(([cat, fonts]) => (
                                                <optgroup key={cat} label={cat}>
                                                    {fonts.map(f => <option key={f} value={f} style={{ fontFamily: f }}>{f}</option>)}
                                                </optgroup>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="control-row">
                                        <label>Size</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="24"
                                                max="96"
                                                value={styling.font_size}
                                                onChange={(e) => updateStyling('font_size', +e.target.value)}
                                            />
                                            <span className="value-badge">{styling.font_size}px</span>
                                        </div>
                                    </div>
                                    <div className="control-row colors">
                                        <div className="color-control">
                                            <label>Fill</label>
                                            <div className="color-picker-wrapper">
                                                <input
                                                    type="color"
                                                    value={styling.font_color}
                                                    onChange={(e) => updateStyling('font_color', e.target.value)}
                                                />
                                                <span className="color-hex">{styling.font_color}</span>
                                            </div>
                                        </div>
                                        <div className="color-control">
                                            <label>Stroke</label>
                                            <div className="color-picker-wrapper">
                                                <input
                                                    type="color"
                                                    value={styling.stroke_color}
                                                    onChange={(e) => updateStyling('stroke_color', e.target.value)}
                                                />
                                                <span className="color-hex">{styling.stroke_color}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Stroke Width</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="10"
                                                value={styling.stroke_width}
                                                onChange={(e) => updateStyling('stroke_width', +e.target.value)}
                                            />
                                            <span className="value-badge">{styling.stroke_width}px</span>
                                        </div>
                                    </div>
                                    <div className="control-row toggles">
                                        <label className="toggle-label">
                                            <input
                                                type="checkbox"
                                                checked={styling.uppercase}
                                                onChange={(e) => updateStyling('uppercase', e.target.checked)}
                                            />
                                            <span className="toggle-text">UPPERCASE</span>
                                        </label>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Highlight Group */}
                        <div className={`style-group ${expandedGroup === 'highlight' ? 'expanded' : ''}`}>
                            <button className="group-header" onClick={() => toggleGroup('highlight')}>
                                <span className="group-icon">✨</span>
                                <span className="group-title">Highlight Style</span>
                                <span className="group-chevron">{expandedGroup === 'highlight' ? '▼' : '▶'}</span>
                            </button>
                            {expandedGroup === 'highlight' && (
                                <div className="group-content">
                                    <div className="control-desc" style={{ fontSize: '12px', color: '#888', marginBottom: '8px' }}>
                                        Use <code>&lt;h&gt;word&lt;/h&gt;</code> to highlight specific words.
                                    </div>
                                    <div className="control-row" style={{ background: '#2a2a2a', padding: '8px', borderRadius: '4px', marginBottom: '8px' }}>
                                        <label className="toggle-label" style={{ display: 'flex', alignItems: 'center', width: '100%', cursor: 'pointer' }}>
                                            <input
                                                type="checkbox"
                                                checked={styling.highlight_active_word}
                                                onChange={(e) => updateStyling('highlight_active_word', e.target.checked)}
                                                style={{ marginRight: '8px' }}
                                            />
                                            <span className="toggle-text" style={{ fontWeight: '500', color: '#fff' }}>Enable Karaoke Mode (Active Word)</span>
                                        </label>
                                    </div>

                                    <div className="control-row colors">
                                        <div className="color-control">
                                            <label>Text</label>
                                            <div className="color-picker-wrapper">
                                                <input
                                                    type="color"
                                                    value={styling.highlight_font_color || '#FFFFFF'}
                                                    onChange={(e) => updateStyling('highlight_font_color', e.target.value)}
                                                />
                                                <span className="color-hex">{styling.highlight_font_color}</span>
                                            </div>
                                        </div>
                                        <div className="color-control">
                                            <label>Background</label>
                                            <div className="color-picker-wrapper">
                                                <input
                                                    type="color"
                                                    value={styling.highlight_bg_color || '#6e00ff'}
                                                    onChange={(e) => updateStyling('highlight_bg_color', e.target.value)}
                                                />
                                                <span className="color-hex">{styling.highlight_bg_color}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Padding</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="20"
                                                value={styling.highlight_bg_padding || 8}
                                                onChange={(e) => updateStyling('highlight_bg_padding', +e.target.value)}
                                            />
                                            <span className="value-badge">{styling.highlight_bg_padding}px</span>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Radius</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="20"
                                                value={styling.highlight_bg_radius || 4}
                                                onChange={(e) => updateStyling('highlight_bg_radius', +e.target.value)}
                                            />
                                            <span className="value-badge">{styling.highlight_bg_radius}px</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Background Group */}
                        <div className={`style-group ${expandedGroup === 'background' ? 'expanded' : ''}`}>
                            <button className="group-header" onClick={() => toggleGroup('background')}>
                                <span className="group-icon">🎴</span>
                                <span className="group-title">Background</span>
                                <label className="group-toggle" onClick={(e) => e.stopPropagation()}>
                                    <input
                                        type="checkbox"
                                        checked={styling.background_enabled}
                                        onChange={(e) => updateStyling('background_enabled', e.target.checked)}
                                    />
                                    <span className="toggle-slider"></span>
                                </label>
                            </button>
                            {expandedGroup === 'background' && (
                                <div className="group-content">
                                    <div className="control-row">
                                        <label>Color</label>
                                        <div className="color-picker-wrapper">
                                            <input
                                                type="color"
                                                value={styling.background_color}
                                                onChange={(e) => updateStyling('background_color', e.target.value)}
                                                disabled={!styling.background_enabled}
                                            />
                                            <span className="color-hex">{styling.background_color}</span>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Opacity</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="100"
                                                value={Math.round(styling.background_opacity * 100)}
                                                onChange={(e) => updateStyling('background_opacity', +e.target.value / 100)}
                                                disabled={!styling.background_enabled}
                                            />
                                            <span className="value-badge">{Math.round(styling.background_opacity * 100)}%</span>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Padding</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="30"
                                                value={styling.background_padding}
                                                onChange={(e) => updateStyling('background_padding', +e.target.value)}
                                                disabled={!styling.background_enabled}
                                            />
                                            <span className="value-badge">{styling.background_padding}px</span>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Radius</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="0"
                                                max="20"
                                                value={styling.background_radius || 0}
                                                onChange={(e) => updateStyling('background_radius', +e.target.value)}
                                                disabled={!styling.background_enabled}
                                            />
                                            <span className="value-badge">{styling.background_radius || 0}px</span>
                                        </div>
                                    </div>
                                    {/* Background Preview */}
                                    <div className="bg-preview" style={{
                                        backgroundColor: styling.background_enabled
                                            ? `${styling.background_color}${Math.round(styling.background_opacity * 255).toString(16).padStart(2, '0')}`
                                            : 'transparent',
                                        borderRadius: `${styling.background_radius || 0}px`,
                                        padding: `${styling.background_padding}px`,
                                        border: styling.background_enabled ? 'none' : '1px dashed rgba(255,255,255,0.2)'
                                    }}>
                                        <span style={{
                                            color: styling.font_color,
                                            fontFamily: styling.font_family,
                                            textTransform: styling.uppercase ? 'uppercase' : 'none'
                                        }}>
                                            Preview Text
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Position & Animation Group */}
                        <div className={`style-group ${expandedGroup === 'position' ? 'expanded' : ''}`}>
                            <button className="group-header" onClick={() => toggleGroup('position')}>
                                <span className="group-icon">📍</span>
                                <span className="group-title">Position & Animation</span>
                                <span className="group-chevron">{expandedGroup === 'position' ? '▼' : '▶'}</span>
                            </button>
                            {expandedGroup === 'position' && (
                                <div className="group-content">
                                    <div className="control-row">
                                        <label>Position</label>
                                        <div className="position-buttons">
                                            {['top', 'middle', 'bottom'].map(pos => (
                                                <button
                                                    key={pos}
                                                    className={`pos-btn ${styling.position === pos ? 'active' : ''}`}
                                                    onClick={() => updateStyling('position', pos)}
                                                >
                                                    {pos === 'top' ? '⬆️' : pos === 'middle' ? '⏺️' : '⬇️'}
                                                    <span>{pos.charAt(0).toUpperCase() + pos.slice(1)}</span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Margin</label>
                                        <div className="slider-with-value">
                                            <input
                                                type="range"
                                                min="20"
                                                max="150"
                                                value={styling.margin_y}
                                                onChange={(e) => updateStyling('margin_y', +e.target.value)}
                                            />
                                            <span className="value-badge">{styling.margin_y}px</span>
                                        </div>
                                    </div>
                                    <div className="control-row">
                                        <label>Animation</label>
                                        <div className="animation-buttons">
                                            {[
                                                { value: 'none', icon: '—', label: 'None' },
                                                { value: 'fade', icon: '🌗', label: 'Fade' },
                                                { value: 'pop', icon: '💥', label: 'Pop' },
                                            ].map(anim => (
                                                <button
                                                    key={anim.value}
                                                    className={`anim-btn ${styling.animation === anim.value ? 'active' : ''}`}
                                                    onClick={() => updateStyling('animation', anim.value)}
                                                >
                                                    <span>{anim.icon}</span>
                                                    <span>{anim.label}</span>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

// Export for use in Preview component
export function getSubtitlePreviewStyle() {
    const styling = typeof window !== 'undefined' ? window.__subtitleStyling : null
    const entries = typeof window !== 'undefined' ? window.__subtitleEntries : []

    if (!styling || !entries?.length) return null

    return {
        styling,
        entries,
        sampleText: entries[0]?.text || 'Sample subtitle'
    }
}
