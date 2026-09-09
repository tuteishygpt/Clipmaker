import { useState } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { useTranslation } from '../i18n'

const STYLE_KEYS = [
    { value: 'cinematic', emoji: '🎬' },
    { value: 'anime', emoji: '🎌' },
    { value: 'illustration', emoji: '🖼️' },
    { value: 'abstract', emoji: '🌀' },
    { value: 'cyberpunk', emoji: '🌆' },
    { value: 'watercolor', emoji: '🎨' },
    { value: 'horror', emoji: '👻' },
    { value: 'minimalist', emoji: '◻️' }
]

function ProjectForm() {
    const { createProject, isLoading } = useProjectStore()
    const { t } = useTranslation()

    const [format, setFormat] = useState('9:16')
    const [style, setStyle] = useState('cinematic')
    const [userDescription, setUserDescription] = useState('')
    const [characterDescription, setCharacterDescription] = useState('')
    const [showAdvanced, setShowAdvanced] = useState(false)

    const formats = [
        {
            value: '9:16',
            label: t('studio.project.formatVertical'),
            desc: t('studio.project.formatVerticalDesc')
        },
        {
            value: '16:9',
            label: t('studio.project.formatHorizontal'),
            desc: t('studio.project.formatHorizontalDesc')
        }
    ]

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
            <h2>{t('studio.project.title')}</h2>
            <p className="form-description">
                {t('studio.project.description')}
            </p>

            {/* Format Selection */}
            <div className="form-section">
                <label className="form-label">{t('studio.project.format')}</label>
                <div className="format-options">
                    {formats.map(f => (
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
                <label className="form-label">{t('studio.project.visualStyle')}</label>
                <div className="style-grid">
                    {STYLE_KEYS.map(s => (
                        <button
                            key={s.value}
                            className={`style-btn ${style === s.value ? 'active' : ''}`}
                            onClick={() => setStyle(s.value)}
                        >
                            <span className="style-emoji">{s.emoji}</span>
                            <span className="style-label">{t(`studio.project.styles.${s.value}`)}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Description */}
            <div className="form-section">
                <label className="form-label">
                    {t('studio.project.concept')}
                    <span className="label-hint"> {t('studio.project.optional')}</span>
                </label>
                <textarea
                    value={userDescription}
                    onChange={(e) => setUserDescription(e.target.value)}
                    placeholder={t('studio.project.conceptPlaceholder')}
                    rows={3}
                    className="form-textarea"
                />
            </div>

            {/* Advanced Options Toggle */}
            <button
                className="toggle-advanced"
                onClick={() => setShowAdvanced(!showAdvanced)}
            >
                {showAdvanced ? '▼' : '▶'} {t('studio.project.advancedOptions')}
            </button>

            {showAdvanced && (
                <div className="advanced-options">
                    <div className="form-section">
                        <label className="form-label">{t('studio.project.character')}</label>
                        <textarea
                            value={characterDescription}
                            onChange={(e) => setCharacterDescription(e.target.value)}
                            placeholder={t('studio.project.characterPlaceholder')}
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
                        {t('studio.project.creatingBtn')}
                    </>
                ) : (
                    <>
                        <span>✨</span> {t('studio.project.createBtn')}
                    </>
                )}
            </button>
        </div>
    )
}

export default ProjectForm
