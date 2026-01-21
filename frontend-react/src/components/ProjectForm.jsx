import { useState } from 'react'
import { useProjectStore } from '../stores/projectStore'

const STYLES = [
    { value: 'cinematic', label: 'Cinematic', emoji: '🎬' },
    { value: 'anime', label: 'Anime', emoji: '🎌' },
    { value: 'illustration', label: 'Illustration', emoji: '🖼️' },
    { value: 'abstract', label: 'Abstract', emoji: '🌀' },
    { value: 'cyberpunk', label: 'Cyberpunk', emoji: '🌆' },
    { value: 'watercolor', label: 'Watercolor', emoji: '🎨' },
    { value: 'horror', label: 'Horror', emoji: '👻' },
    { value: 'minimalist', label: 'Minimalist', emoji: '◻️' }
]

const FORMATS = [
    { value: '9:16', label: 'Vertical (9:16)', desc: 'TikTok, Reels, Stories' },
    { value: '16:9', label: 'Horizontal (16:9)', desc: 'YouTube, Desktop' }
]

function ProjectForm() {
    const { createProject, isLoading } = useProjectStore()

    const [format, setFormat] = useState('9:16')
    const [style, setStyle] = useState('cinematic')
    const [userDescription, setUserDescription] = useState('')
    const [characterDescription, setCharacterDescription] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)

    const handleCreate = async () => {
        await createProject({
            format,
            style,
            subtitles: true,
            user_description: userDescription,
            character_description: characterDescription,
            render_preset: 'fast'
        })
    }

    return (
        <div className="project-form">
            <h2>Create New Project</h2>
            <p className="form-description">
                Set up your video style and describe your vision
            </p>

            {/* Format Selection */}
            <div className="form-section">
                <label className="form-label">Video Format</label>
                <div className="format-options">
                    {FORMATS.map(f => (
                        <button
                            key={f.value}
                            className={`format-btn ${format === f.value ? 'active' : ''}`}
                            onClick={() => setFormat(f.value)}
                        >
                            <span className="format-label">{f.label}</span>
                            <span className="format-desc">{f.desc}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Style Selection */}
            <div className="form-section">
                <label className="form-label">Visual Style</label>
                <div className="style-grid">
                    {STYLES.map(s => (
                        <button
                            key={s.value}
                            className={`style-btn ${style === s.value ? 'active' : ''}`}
                            onClick={() => setStyle(s.value)}
                        >
                            <span className="style-emoji">{s.emoji}</span>
                            <span className="style-label">{s.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Description */}
            <div className="form-section">
                <label className="form-label">
                    Video Concept
                    <span className="label-hint">(optional)</span>
                </label>
                <textarea
                    value={userDescription}
                    onChange={(e) => setUserDescription(e.target.value)}
                    placeholder="Describe your video idea... e.g., 'A dreamy journey through a neon city at night'"
                    rows={3}
                    className="form-textarea"
                />
            </div>

            {/* Advanced Options Toggle */}
            <button
                className="toggle-advanced"
                onClick={() => setShowAdvanced(!showAdvanced)}
            >
                {showAdvanced ? '▼' : '▶'} Advanced Options
            </button>

            {showAdvanced && (
                <div className="advanced-options">
                    <div className="form-section">
                        <label className="form-label">Character Description</label>
                        <textarea
                            value={characterDescription}
                            onChange={(e) => setCharacterDescription(e.target.value)}
                            placeholder="Describe recurring characters... e.g., 'A young woman with silver hair wearing a futuristic outfit'"
                            rows={2}
                            className="form-textarea"
                        />
                    </div>
                </div>
            )}

            {/* Create Button */}
            <button
                className="btn-primary btn-lg full-width"
                onClick={handleCreate}
                disabled={isLoading}
            >
                {isLoading ? (
                    <>
                        <span className="spinner" />
                        Creating...
                    </>
                ) : (
                    <>
                        <span>✨</span> Create Project
                    </>
                )}
            </button>
        </div>
    )
}

export default ProjectForm
