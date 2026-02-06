import { useState, useEffect, useCallback } from 'react'
import './SubtitleEditor.css'

const API_BASE = 'http://localhost:8000'

// Font categories with their fonts
const FONT_CATEGORIES = {
    'Sans-serif': [
        'Montserrat', 'Inter', 'Roboto', 'Open Sans', 'Lato', 'Poppins',
        'Nunito', 'Raleway', 'Ubuntu', 'Oswald', 'Source Sans Pro', 'Fira Sans',
        'Work Sans', 'DM Sans', 'Quicksand', 'Mulish', 'Barlow', 'Outfit',
        'Manrope', 'Urbanist'
    ],
    'Serif': [
        'Playfair Display', 'Merriweather', 'Lora', 'PT Serif',
        'Libre Baskerville', 'Crimson Text', 'Source Serif Pro'
    ],
    'Display': [
        'Bebas Neue', 'Anton', 'Righteous', 'Lobster', 'Pacifico',
        'Permanent Marker', 'Abril Fatface', 'Russo One', 'Bangers',
        'Concert One', 'Bungee', 'Black Ops One', 'Impact', 'Arial Black',
        'Archivo Black', 'Teko'
    ],
    'Monospace': [
        'Fira Code', 'JetBrains Mono', 'Source Code Pro', 'Roboto Mono'
    ]
}

const DEFAULT_STYLING = {
    font_family: 'Montserrat',
    font_size: 48,
    font_weight: 'bold',
    font_color: '#FFFFFF',
    stroke_color: '#000000',
    stroke_width: 3,
    shadow_color: '#000000',
    shadow_offset: 2,
    background_enabled: false,
    background_color: '#000000',
    background_opacity: 0.7,
    background_padding: 10,
    position: 'bottom',
    margin_x: 50,
    margin_y: 60,
    text_align: 'center',
    max_width_percent: 90,
    uppercase: false,
    animation: 'none'
}

export default function SubtitleEditor({ projectId, onClose, format = '9:16' }) {
    const [entries, setEntries] = useState([])
    const [styling, setStyling] = useState(DEFAULT_STYLING)
    const [loading, setLoading] = useState(false)
    const [generating, setGenerating] = useState(false)
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState(null)
    const [activeTab, setActiveTab] = useState('entries')
    const [editingEntry, setEditingEntry] = useState(null)
    const [hasChanges, setHasChanges] = useState(false)

    // Load subtitles on mount
    useEffect(() => {
        loadSubtitles()
    }, [projectId])

    const loadSubtitles = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`)
            if (res.ok) {
                const data = await res.json()
                setEntries(data.entries || [])
                if (data.styling) {
                    setStyling({ ...DEFAULT_STYLING, ...data.styling })
                }
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
                body: JSON.stringify({
                    language: 'auto',
                    max_chars_per_line: 42,
                    min_duration: 1.0,
                    max_duration: 5.0
                })
            })

            if (!res.ok) {
                const errData = await res.json()
                throw new Error(errData.detail || 'Generation failed')
            }

            const data = await res.json()
            setEntries(data.entries || [])
            if (data.styling) {
                setStyling({ ...DEFAULT_STYLING, ...data.styling })
            }
            setHasChanges(false)
        } catch (err) {
            setError(err.message)
        } finally {
            setGenerating(false)
        }
    }

    const importSrt = async (file) => {
        const formData = new FormData()
        formData.append('srt_file', file)

        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles/import`, {
                method: 'POST',
                body: formData
            })

            if (!res.ok) {
                const errData = await res.json()
                throw new Error(errData.detail || 'Import failed')
            }

            const data = await res.json()
            setEntries(data.entries || [])
            setHasChanges(false)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const saveSubtitles = async () => {
        setSaving(true)
        setError(null)
        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    entries: entries,
                    styling: styling
                })
            })

            if (!res.ok) {
                const errData = await res.json()
                throw new Error(errData.detail || 'Save failed')
            }

            setHasChanges(false)
        } catch (err) {
            setError(err.message)
        } finally {
            setSaving(false)
        }
    }

    const downloadSrt = () => {
        window.open(`${API_BASE}/projects/${projectId}/subtitles/download`, '_blank')
    }

    const deleteSubtitles = async () => {
        if (!confirm('Are you sure you want to delete all subtitles?')) return

        try {
            const res = await fetch(`${API_BASE}/projects/${projectId}/subtitles`, {
                method: 'DELETE'
            })
            if (res.ok) {
                setEntries([])
                setStyling(DEFAULT_STYLING)
                setHasChanges(false)
            }
        } catch (err) {
            setError(err.message)
        }
    }

    const updateEntry = (id, field, value) => {
        setEntries(prev => prev.map(e =>
            e.id === id ? { ...e, [field]: value } : e
        ))
        setHasChanges(true)
    }

    const deleteEntry = (id) => {
        setEntries(prev => prev.filter(e => e.id !== id))
        setHasChanges(true)
    }

    const addEntry = () => {
        const lastEntry = entries[entries.length - 1]
        const newId = entries.length > 0 ? Math.max(...entries.map(e => e.id)) + 1 : 1

        const newEntry = {
            id: newId,
            start_time: lastEntry ? lastEntry.end_time : '00:00:00,000',
            end_time: lastEntry ? incrementTime(lastEntry.end_time, 3) : '00:00:03,000',
            text: ''
        }

        setEntries([...entries, newEntry])
        setEditingEntry(newId)
        setHasChanges(true)
    }

    const updateStyling = (key, value) => {
        setStyling(prev => ({ ...prev, [key]: value }))
        setHasChanges(true)
    }

    // Helper to increment SRT time by seconds
    const incrementTime = (srtTime, seconds) => {
        const parts = srtTime.replace(',', '.').split(':')
        let totalSeconds = parseFloat(parts[0]) * 3600 + parseFloat(parts[1]) * 60 + parseFloat(parts[2])
        totalSeconds += seconds

        const h = Math.floor(totalSeconds / 3600)
        const m = Math.floor((totalSeconds % 3600) / 60)
        const s = totalSeconds % 60
        const ms = Math.round((s % 1) * 1000)

        return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(Math.floor(s)).padStart(2, '0')},${String(ms).padStart(3, '0')}`
    }

    const handleFileUpload = (e) => {
        const file = e.target.files?.[0]
        if (file) {
            importSrt(file)
        }
    }

    return (
        <div className="subtitle-editor">
            <div className="subtitle-editor-header">
                <h2>Subtitle Editor</h2>
                <button className="close-btn" onClick={onClose}>×</button>
            </div>

            {error && (
                <div className="subtitle-error">
                    {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}

            <div className="subtitle-toolbar">
                <button
                    className="btn btn-primary"
                    onClick={generateSubtitles}
                    disabled={generating || loading}
                >
                    {generating ? 'Generating...' : '🎤 Generate from Audio'}
                </button>

                <label className="btn btn-secondary">
                    📄 Import SRT
                    <input
                        type="file"
                        accept=".srt"
                        hidden
                        onChange={handleFileUpload}
                    />
                </label>

                {entries.length > 0 && (
                    <>
                        <button className="btn btn-secondary" onClick={downloadSrt}>
                            ⬇️ Download SRT
                        </button>
                        <button className="btn btn-danger" onClick={deleteSubtitles}>
                            🗑️ Delete All
                        </button>
                    </>
                )}

                {hasChanges && (
                    <button
                        className="btn btn-success"
                        onClick={saveSubtitles}
                        disabled={saving}
                    >
                        {saving ? 'Saving...' : '💾 Save Changes'}
                    </button>
                )}
            </div>

            <div className="subtitle-tabs">
                <button
                    className={`tab ${activeTab === 'entries' ? 'active' : ''}`}
                    onClick={() => setActiveTab('entries')}
                >
                    Subtitles ({entries.length})
                </button>
                <button
                    className={`tab ${activeTab === 'styling' ? 'active' : ''}`}
                    onClick={() => setActiveTab('styling')}
                >
                    Styling
                </button>
                <button
                    className={`tab ${activeTab === 'preview' ? 'active' : ''}`}
                    onClick={() => setActiveTab('preview')}
                >
                    Preview
                </button>
            </div>

            <div className="subtitle-content">
                {loading ? (
                    <div className="subtitle-loading">Loading...</div>
                ) : activeTab === 'entries' ? (
                    <div className="entries-panel">
                        {entries.length === 0 ? (
                            <div className="no-entries">
                                <p>No subtitles yet. Generate from audio or import an SRT file.</p>
                            </div>
                        ) : (
                            <div className="entries-list">
                                {entries.map((entry, idx) => (
                                    <div key={entry.id} className="subtitle-entry">
                                        <div className="entry-header">
                                            <span className="entry-index">#{entry.id}</span>
                                            <div className="entry-timing">
                                                <input
                                                    type="text"
                                                    value={entry.start_time}
                                                    onChange={(e) => updateEntry(entry.id, 'start_time', e.target.value)}
                                                    placeholder="00:00:00,000"
                                                />
                                                <span>→</span>
                                                <input
                                                    type="text"
                                                    value={entry.end_time}
                                                    onChange={(e) => updateEntry(entry.id, 'end_time', e.target.value)}
                                                    placeholder="00:00:00,000"
                                                />
                                            </div>
                                            <button
                                                className="delete-entry"
                                                onClick={() => deleteEntry(entry.id)}
                                            >
                                                ×
                                            </button>
                                        </div>
                                        <textarea
                                            value={entry.text}
                                            onChange={(e) => updateEntry(entry.id, 'text', e.target.value)}
                                            placeholder="Enter subtitle text..."
                                            rows={2}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                        <button className="btn btn-secondary add-entry" onClick={addEntry}>
                            + Add Subtitle
                        </button>
                    </div>
                ) : activeTab === 'styling' ? (
                    <div className="styling-panel">
                        {/* Font Section */}
                        <div className="styling-section">
                            <h3>Font</h3>
                            <div className="styling-row">
                                <label>Font Family</label>
                                <select
                                    value={styling.font_family}
                                    onChange={(e) => updateStyling('font_family', e.target.value)}
                                >
                                    {Object.entries(FONT_CATEGORIES).map(([category, fonts]) => (
                                        <optgroup key={category} label={category}>
                                            {fonts.map(font => (
                                                <option key={font} value={font}>{font}</option>
                                            ))}
                                        </optgroup>
                                    ))}
                                </select>
                            </div>
                            <div className="styling-row">
                                <label>Font Size: {styling.font_size}px</label>
                                <input
                                    type="range"
                                    min="16"
                                    max="120"
                                    value={styling.font_size}
                                    onChange={(e) => updateStyling('font_size', parseInt(e.target.value))}
                                />
                            </div>
                            <div className="styling-row">
                                <label>Font Weight</label>
                                <select
                                    value={styling.font_weight}
                                    onChange={(e) => updateStyling('font_weight', e.target.value)}
                                >
                                    <option value="normal">Normal</option>
                                    <option value="bold">Bold</option>
                                    <option value="900">Black</option>
                                </select>
                            </div>
                            <div className="styling-row checkbox">
                                <input
                                    type="checkbox"
                                    id="uppercase"
                                    checked={styling.uppercase}
                                    onChange={(e) => updateStyling('uppercase', e.target.checked)}
                                />
                                <label htmlFor="uppercase">UPPERCASE</label>
                            </div>
                        </div>

                        {/* Colors Section */}
                        <div className="styling-section">
                            <h3>Colors</h3>
                            <div className="styling-row">
                                <label>Text Color</label>
                                <input
                                    type="color"
                                    value={styling.font_color}
                                    onChange={(e) => updateStyling('font_color', e.target.value)}
                                />
                            </div>
                            <div className="styling-row">
                                <label>Stroke Color</label>
                                <input
                                    type="color"
                                    value={styling.stroke_color}
                                    onChange={(e) => updateStyling('stroke_color', e.target.value)}
                                />
                            </div>
                            <div className="styling-row">
                                <label>Stroke Width: {styling.stroke_width}px</label>
                                <input
                                    type="range"
                                    min="0"
                                    max="10"
                                    value={styling.stroke_width}
                                    onChange={(e) => updateStyling('stroke_width', parseInt(e.target.value))}
                                />
                            </div>
                        </div>

                        {/* Background Section */}
                        <div className="styling-section">
                            <h3>Background</h3>
                            <div className="styling-row checkbox">
                                <input
                                    type="checkbox"
                                    id="bg_enabled"
                                    checked={styling.background_enabled}
                                    onChange={(e) => updateStyling('background_enabled', e.target.checked)}
                                />
                                <label htmlFor="bg_enabled">Enable Background Box</label>
                            </div>
                            {styling.background_enabled && (
                                <>
                                    <div className="styling-row">
                                        <label>Background Color</label>
                                        <input
                                            type="color"
                                            value={styling.background_color}
                                            onChange={(e) => updateStyling('background_color', e.target.value)}
                                        />
                                    </div>
                                    <div className="styling-row">
                                        <label>Opacity: {Math.round(styling.background_opacity * 100)}%</label>
                                        <input
                                            type="range"
                                            min="0"
                                            max="100"
                                            value={styling.background_opacity * 100}
                                            onChange={(e) => updateStyling('background_opacity', parseInt(e.target.value) / 100)}
                                        />
                                    </div>
                                    <div className="styling-row">
                                        <label>Padding: {styling.background_padding}px</label>
                                        <input
                                            type="range"
                                            min="0"
                                            max="50"
                                            value={styling.background_padding}
                                            onChange={(e) => updateStyling('background_padding', parseInt(e.target.value))}
                                        />
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Position Section */}
                        <div className="styling-section">
                            <h3>Position</h3>
                            <div className="styling-row">
                                <label>Vertical Position</label>
                                <select
                                    value={styling.position}
                                    onChange={(e) => updateStyling('position', e.target.value)}
                                >
                                    <option value="top">Top</option>
                                    <option value="middle">Middle</option>
                                    <option value="bottom">Bottom</option>
                                </select>
                            </div>
                            <div className="styling-row">
                                <label>Text Alignment</label>
                                <select
                                    value={styling.text_align}
                                    onChange={(e) => updateStyling('text_align', e.target.value)}
                                >
                                    <option value="left">Left</option>
                                    <option value="center">Center</option>
                                    <option value="right">Right</option>
                                </select>
                            </div>
                            <div className="styling-row">
                                <label>Vertical Margin: {styling.margin_y}px</label>
                                <input
                                    type="range"
                                    min="0"
                                    max="300"
                                    value={styling.margin_y}
                                    onChange={(e) => updateStyling('margin_y', parseInt(e.target.value))}
                                />
                            </div>
                            <div className="styling-row">
                                <label>Max Width: {styling.max_width_percent}%</label>
                                <input
                                    type="range"
                                    min="50"
                                    max="100"
                                    value={styling.max_width_percent}
                                    onChange={(e) => updateStyling('max_width_percent', parseInt(e.target.value))}
                                />
                            </div>
                        </div>

                        {/* Animation Section */}
                        <div className="styling-section">
                            <h3>Animation</h3>
                            <div className="styling-row">
                                <label>Animation Effect</label>
                                <select
                                    value={styling.animation}
                                    onChange={(e) => updateStyling('animation', e.target.value)}
                                >
                                    <option value="none">None</option>
                                    <option value="fade">Fade In/Out</option>
                                    <option value="pop">Pop In</option>
                                    <option value="typewriter">Typewriter</option>
                                </select>
                            </div>
                            <p className="styling-hint">
                                {styling.animation === 'fade' && 'Subtitles will smoothly fade in and out'}
                                {styling.animation === 'pop' && 'Subtitles will pop in with a scaling effect'}
                                {styling.animation === 'typewriter' && 'Text appears character by character'}
                                {styling.animation === 'none' && 'No animation - instant appearance'}
                            </p>
                        </div>
                    </div>
                ) : (
                    <div className="se-preview-panel">
                        <SubtitlePreview entries={entries} styling={styling} format={format} />
                    </div>
                )}
            </div>
        </div>
    )
}

// Preview component showing styled subtitle example
function SubtitlePreview({ entries, styling, format = '9:16' }) {
    const [currentIndex, setCurrentIndex] = useState(0)

    const sampleText = entries.length > 0
        ? entries[Math.min(currentIndex, entries.length - 1)].text
        : 'Sample subtitle text appears here'

    const displayText = styling.uppercase ? sampleText.toUpperCase() : sampleText

    const textStyle = {
        fontFamily: styling.font_family,
        fontSize: `${Math.min(styling.font_size * 0.5, 32)}px`,
        fontWeight: styling.font_weight,
        color: styling.font_color,
        textAlign: styling.text_align,
        textShadow: styling.stroke_width > 0
            ? `0 0 ${styling.stroke_width}px ${styling.stroke_color}, 
         0 0 ${styling.stroke_width * 2}px ${styling.stroke_color}`
            : 'none',
        maxWidth: `${styling.max_width_percent}%`,
        padding: styling.background_enabled ? `${styling.background_padding * 0.5}px` : '0',
        backgroundColor: styling.background_enabled
            ? `${styling.background_color}${Math.round(styling.background_opacity * 255).toString(16).padStart(2, '0')}`
            : 'transparent',
        borderRadius: styling.background_enabled ? '4px' : '0',
    }

    const containerStyle = {
        display: 'flex',
        flexDirection: 'column',
        justifyContent: styling.position === 'top' ? 'flex-start' :
            styling.position === 'middle' ? 'center' : 'flex-end',
        alignItems: styling.text_align === 'left' ? 'flex-start' :
            styling.text_align === 'right' ? 'flex-end' : 'center',
        padding: `${styling.margin_y * 0.3}px ${styling.margin_x * 0.3}px`,
    }

    const isHorizontal = format === '16:9'

    return (
        <div className="se-preview-container">
            <div
                className="se-preview-box"
                style={{
                    ...containerStyle,
                    aspectRatio: isHorizontal ? '16/9' : '9/16',
                    maxWidth: isHorizontal ? '600px' : '400px'
                }}
            >
                <div className="se-preview-text" style={textStyle}>
                    {displayText}
                </div>
            </div>

            {entries.length > 1 && (
                <div className="se-preview-controls">
                    <button
                        disabled={currentIndex === 0}
                        onClick={() => setCurrentIndex(i => i - 1)}
                    >
                        ◀ Prev
                    </button>
                    <span>Subtitle {currentIndex + 1} of {entries.length}</span>
                    <button
                        disabled={currentIndex >= entries.length - 1}
                        onClick={() => setCurrentIndex(i => i + 1)}
                    >
                        Next ▶
                    </button>
                </div>
            )}

            <p className="se-preview-note">
                This is a preview. Final render may vary slightly.
            </p>
        </div>
    )
}
