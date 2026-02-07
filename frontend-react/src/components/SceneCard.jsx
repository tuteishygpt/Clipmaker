import { useState, useEffect } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { fixImageUrl } from '../utils'

function SceneCard({ segment }) {
    const { updateSegment, regenerateSegment, regeneratePrompt, regenerateImage, showLightbox, projectId } = useProjectStore()

    const [isEditing, setIsEditing] = useState(false)
    const [saving, setSaving] = useState(false)
    const [regenerating, setRegenerating] = useState(false)
    const [imgError, setImgError] = useState(false)

    const [previewVersion, setPreviewVersion] = useState(
        segment.prompt?.version || 1
    )

    // Reset error when segment updates (e.g. polling, version change)
    useEffect(() => {
        setImgError(false)
    }, [segment, previewVersion])

    // Form state
    const [startTime, setStartTime] = useState(segment.start_time)
    const [endTime, setEndTime] = useState(segment.end_time)
    const [lyricText, setLyricText] = useState(segment.lyric_text || segment.text || '')
    const [visualIntent, setVisualIntent] = useState(segment.visual_intent || segment.visual_description || '')
    const [imagePrompt, setImagePrompt] = useState(segment.prompt?.image_prompt || '')
    const [cameraAngle, setCameraAngle] = useState(segment.camera_angle || '')
    const [emotion, setEmotion] = useState(segment.emotion || '')
    const [effect, setEffect] = useState(segment.effect || 'random')
    const [transition, setTransition] = useState(segment.transition || 'random')

    // Sync form state when segment changes (safety measure)
    useEffect(() => {
        setStartTime(segment.start_time)
        setEndTime(segment.end_time)
        setLyricText(segment.lyric_text || segment.text || '')
        setVisualIntent(segment.visual_intent || segment.visual_description || '')
        setImagePrompt(segment.prompt?.image_prompt || '')
        setCameraAngle(segment.camera_angle || '')
        setEmotion(segment.emotion || '')
        setEffect(segment.effect || 'random')
        setTransition(segment.transition || 'random')
    }, [segment.id, segment.start_time, segment.end_time, segment.lyric_text, segment.text, segment.visual_intent, segment.visual_description, segment.prompt?.image_prompt, segment.camera_angle, segment.emotion, segment.effect, segment.transition])

    // Update imagePrompt when segment updates (e.g. external regen)
    // Only update if we are not editing/focused... actually simple way:
    // When we trigger regen prompt, we manually update.

    // BUT: if we navigated away and came back, or another user updated it, we want sync.
    // For now stick to simple initialization, but update on regen action.

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
                emotion: emotion,
                effect: effect,
                transition: transition
            })
        } finally {
            setSaving(false)
        }
    }

    const handleRegenerate = async (e) => {
        if (e) e.stopPropagation()
        await handleSave()
        setRegenerating(true)
        try {
            await regenerateSegment(segment.id)
            setImgError(false)
        } finally {
            setRegenerating(false)
        }
    }

    const handleRegeneratePrompt = async () => {
        await handleSave()
        setRegenerating(true)
        try {
            const res = await regeneratePrompt(segment.id)
            if (res && res.prompt) {
                setImagePrompt(res.prompt.image_prompt)
            }
        } finally {
            setRegenerating(false)
        }
    }

    const handleRegenerateImageOnly = async () => {
        await handleSave()
        setRegenerating(true)
        try {
            await regenerateImage(segment.id)
            setImgError(false)
        } finally {
            setRegenerating(false)
        }
    }


    // Sync preview version when segment updates
    useEffect(() => {
        // If the segment updates (e.g. max_version increases), 
        // we generally want to stay on the current preview UNLESS it was the active one that changed.
        // But for "Regenerate", we want to jump to the newest version.
        // Simple logic: if active version changes, sync to it.
        const activeV = segment.prompt?.version || 1
        setPreviewVersion(activeV)
    }, [segment.prompt?.version, segment.max_version])

    const maxVersion = segment.max_version !== undefined ? segment.max_version : (segment.prompt?.version || 1)
    const currentVersion = segment.prompt?.version || 1
    const isDifferentVersion = previewVersion !== currentVersion

    const handleVersionChange = (direction) => {
        let newV = previewVersion + direction
        if (newV < 1) newV = 1
        if (newV > maxVersion) newV = maxVersion
        setPreviewVersion(newV)
        setImgError(false)
    }

    const handleSetVersion = async (e) => {
        e.stopPropagation()
        setSaving(true)
        try {
            await updateSegment(segment.id, {
                version: previewVersion
            })
            // Toast will be shown by store
        } finally {
            setSaving(false)
        }
    }

    const hasImage = maxVersion > 0
    const imageUrl = fixImageUrl(
        projectId && segment?.id && hasImage
            ? `/projects/${projectId}/images/${segment.id}_v${previewVersion}.png`
            : null
    )

    const handleImageClick = (e) => {
        if (imgError || !imageUrl) return
        e.stopPropagation()
        // Determine which image to show in lightbox
        showLightbox(`/projects/${useProjectStore.getState().projectId}/images/${segment.id}_v${previewVersion}.png`)
    }

    return (
        <div className="scene-card">
            <div className="scene-card-image-wrapper">
                {(!imageUrl || imgError) ? (
                    <div className="image-placeholder">
                        <span className="icon">🖼️</span>
                        <span>{imgError ? `Error v${previewVersion}` : 'Generating...'}</span>
                    </div>
                ) : (
                    <img
                        src={imageUrl}
                        alt={`${segment.id} v${previewVersion}`}
                        loading="lazy"
                        onClick={handleImageClick}
                        onError={() => setImgError(true)}
                        style={{ cursor: 'zoom-in' }}
                    />
                )}

                {/* Version Controls - Minimal Design */}
                {maxVersion > 1 && (
                    <div
                        className="version-controls"
                        onClick={e => e.stopPropagation()}
                        style={{
                            backgroundColor: 'rgba(0, 0, 0, 0.6)',
                            position: 'absolute',
                            bottom: '8px',
                            left: '50%',
                            transform: 'translateX(-50%)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            padding: '3px 8px',
                            borderRadius: '12px',
                            zIndex: 10,
                            fontSize: '12px',
                            color: 'white'
                        }}
                    >
                        <button
                            className="v-btn prev"
                            disabled={previewVersion <= 1}
                            onClick={() => handleVersionChange(-1)}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: previewVersion <= 1 ? 'rgba(255,255,255,0.3)' : 'white',
                                cursor: previewVersion <= 1 ? 'default' : 'pointer',
                                padding: '0 4px',
                                fontSize: '16px'
                            }}
                        >
                            ‹
                        </button>

                        <span style={{ fontSize: '11px', fontWeight: '500' }}>
                            v{previewVersion}/{maxVersion}
                        </span>


                        <button
                            className="v-btn next"
                            disabled={previewVersion >= maxVersion}
                            onClick={() => handleVersionChange(1)}
                            style={{
                                background: 'none',
                                border: 'none',
                                color: previewVersion >= maxVersion ? 'rgba(255,255,255,0.3)' : 'white',
                                cursor: previewVersion >= maxVersion ? 'default' : 'pointer',
                                padding: '0 4px',
                                fontSize: '16px'
                            }}
                        >
                            ›
                        </button>

                        {isDifferentVersion && (
                            <button
                                onClick={handleSetVersion}
                                disabled={saving}
                                style={{
                                    background: 'rgba(99, 102, 241, 0.9)',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '6px',
                                    padding: '2px 6px',
                                    fontSize: '10px',
                                    fontWeight: '600',
                                    cursor: 'pointer',
                                    marginLeft: '4px'
                                }}
                            >
                                Set
                            </button>
                        )}
                    </div>
                )}
            </div>

            <div className="scene-details">
                <div className="edit-toggle-row">
                    <h3>{segment.id}</h3>
                    <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                            className="edit-toggle-btn"
                            onClick={handleRegenerate}
                            disabled={regenerating}
                            title="Regenerate fully (Prompt + Image)"
                        >
                            Regenerate
                        </button>
                        <button
                            className="edit-toggle-btn"
                            onClick={() => setIsEditing(!isEditing)}
                        >
                            {isEditing ? 'Hide' : 'Edit'}
                        </button>
                    </div>
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

                        <div style={{ marginTop: '12px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                            <div>
                                <label className="scene-label">Camera Motion (Effect)</label>
                                <select
                                    className="scene-text-input"
                                    value={effect}
                                    onChange={(e) => setEffect(e.target.value)}
                                    style={{ height: '36px', padding: '0 8px', width: '100%' }}
                                >
                                    <option value="random">Random</option>
                                    <option value="zoom_in">Zoom In</option>
                                    <option value="zoom_out">Zoom Out</option>
                                    <option value="pan_left">Pan Left</option>
                                    <option value="pan_right">Pan Right</option>
                                    <option value="pan_up">Pan Up</option>
                                    <option value="pan_down">Pan Down</option>
                                </select>
                            </div>
                            <div>
                                <label className="scene-label">Transition (In)</label>
                                <select
                                    className="scene-text-input"
                                    value={transition}
                                    onChange={(e) => setTransition(e.target.value)}
                                    style={{ height: '36px', padding: '0 8px', width: '100%' }}
                                >
                                    <option value="random">Random</option>
                                    <option value="crossfade">Crossfade (Blend)</option>
                                    <option value="slide_left">Slide Left</option>
                                    <option value="slide_right">Slide Right</option>
                                    <option value="slide_up">Slide Up</option>
                                    <option value="slide_down">Slide Down</option>
                                    <option value="zoom_in">Zoom In (Pop)</option>
                                    <option value="zoom_out">Zoom Out</option>
                                </select>
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
                        </div>
                        <div className="btn-row" style={{ marginTop: '8px' }}>
                            <button
                                className="regenerate-btn"
                                onClick={handleRegeneratePrompt}
                                disabled={regenerating}
                                style={{ fontSize: '0.75rem' }}
                            >
                                {regenerating ? '...' : 'Regenerate Prompt'}
                            </button>
                            <button
                                className="regenerate-btn"
                                onClick={handleRegenerateImageOnly}
                                disabled={regenerating}
                                style={{ fontSize: '0.75rem' }}
                            >
                                {regenerating ? '...' : 'Regenerate Image'}
                            </button>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

export default SceneCard
