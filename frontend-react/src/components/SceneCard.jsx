import { useState, useEffect } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { fixImageUrl } from '../utils'

function SceneCard({ segment }) {
    const { updateSegment, regenerateSegment, showLightbox } = useProjectStore()

    const [isEditing, setIsEditing] = useState(false)
    const [saving, setSaving] = useState(false)
    const [regenerating, setRegenerating] = useState(false)
    const [imgError, setImgError] = useState(false)

    // Reset error when segment or thumbnail changes (e.g. project load or regeneration)
    useEffect(() => {
        setImgError(false)
    }, [segment.id, segment.thumbnail])

    // Form state
    const [startTime, setStartTime] = useState(segment.start_time)
    const [endTime, setEndTime] = useState(segment.end_time)
    const [lyricText, setLyricText] = useState(segment.lyric_text || segment.text || '')
    const [visualIntent, setVisualIntent] = useState(segment.visual_intent || segment.visual_description || '')
    const [imagePrompt, setImagePrompt] = useState(segment.prompt?.image_prompt || '')
    const [cameraAngle, setCameraAngle] = useState(segment.camera_angle || '')
    const [emotion, setEmotion] = useState(segment.emotion || '')

    const handleSave = async () => {
        setSaving(true)
        try {
            await updateSegment(segment.id, {
                start_time: startTime,
                end_time: endTime,
                lyric_text: lyricText,
                visual_intent: visualIntent,
                image_prompt: imagePrompt,
                camera_angle: cameraAngle,
                emotion: emotion
            })
        } finally {
            setSaving(false)
        }
    }

    const handleRegenerate = async () => {
        await handleSave()
        setRegenerating(true)
        try {
            await regenerateSegment(segment.id)
            setImgError(false) // Reset error when regenerating
        } finally {
            setRegenerating(false)
        }
    }

    const handleImageClick = (e) => {
        if (imgError || !imageUrl) return
        e.stopPropagation()
        showLightbox(segment.thumbnail)
    }

    const imageUrl = fixImageUrl(segment.thumbnail)

    return (
        <div className="scene-card">
            <div className="scene-card-image-wrapper">
                {(!imageUrl || imgError) ? (
                    <div className="image-placeholder">
                        <span className="icon">🖼️</span>
                        <span>{imgError ? 'Image Error' : 'Generating...'}</span>
                    </div>
                ) : (
                    <img
                        src={imageUrl}
                        alt={segment.id}
                        loading="lazy"
                        onClick={handleImageClick}
                        onError={() => setImgError(true)}
                        style={{ cursor: 'zoom-in' }}
                    />
                )}
            </div>

            <div className="scene-details">
                <div className="edit-toggle-row">
                    <h3>{segment.id}</h3>
                    <button
                        className="edit-toggle-btn"
                        onClick={() => setIsEditing(!isEditing)}
                    >
                        {isEditing ? 'Hide Details' : 'Edit Details'}
                    </button>
                </div>

                {isEditing && (
                    <div className="collapsible-content expanded">
                        <div className="scene-input-group">
                            <label className="time-label">Start</label>
                            <input
                                className="scene-time-input"
                                value={startTime}
                                onChange={(e) => setStartTime(e.target.value)}
                                placeholder="0:00"
                            />
                            <label className="time-label" style={{ marginLeft: '8px' }}>End</label>
                            <input
                                className="scene-time-input"
                                value={endTime}
                                onChange={(e) => setEndTime(e.target.value)}
                                placeholder="0:00"
                            />
                        </div>

                        <label className="scene-label">Text / Lyric</label>
                        <textarea
                            className="scene-text-input"
                            value={lyricText}
                            onChange={(e) => setLyricText(e.target.value)}
                            rows={2}
                        />

                        <label className="scene-label">Visual Description</label>
                        <textarea
                            className="scene-text-input"
                            value={visualIntent}
                            onChange={(e) => setVisualIntent(e.target.value)}
                            rows={3}
                        />

                        <label className="scene-label prompt-label">Image Prompt</label>
                        <textarea
                            className="scene-text-input"
                            value={imagePrompt}
                            onChange={(e) => setImagePrompt(e.target.value)}
                            rows={3}
                        />

                        <div className="extras-grid">
                            <div>
                                <label className="scene-label">Camera Angle</label>
                                <textarea
                                    className="scene-text-input"
                                    value={cameraAngle}
                                    onChange={(e) => setCameraAngle(e.target.value)}
                                    rows={1}
                                />
                            </div>
                            <div>
                                <label className="scene-label">Emotion</label>
                                <textarea
                                    className="scene-text-input"
                                    value={emotion}
                                    onChange={(e) => setEmotion(e.target.value)}
                                    rows={1}
                                />
                            </div>
                        </div>

                        <div className="btn-row">
                            <button
                                className="save-btn"
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? 'Saving...' : 'Save Changes'}
                            </button>
                            <button
                                className="regenerate-btn"
                                onClick={handleRegenerate}
                                disabled={regenerating}
                            >
                                {regenerating ? 'Queued...' : 'Regenerate Image'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default SceneCard
