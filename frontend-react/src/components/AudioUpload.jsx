import { useState, useRef } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { getAudioUrl } from '../api'
import { useTranslation } from '../i18n'

function AudioUpload() {
    const { projectId, uploadAudio, isLoading, audioUploaded } = useProjectStore()
    const { t } = useTranslation()
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef(null)

    const handleDragOver = (e) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const handleDrop = async (e) => {
        e.preventDefault()
        setIsDragging(false)

        const file = e.dataTransfer.files[0]
        if (file && file.type.startsWith('audio/')) {
            await uploadAudio(file)
        }
    }

    const handleFileSelect = async (e) => {
        const file = e.target.files[0]
        if (file) {
            await uploadAudio(file)
        }
    }

    // If audio is already uploaded, show success state and player
    // If audio is already uploaded, show compact success state
    if (audioUploaded) {
        return (
            <div className="audio-upload-container compact">
                <div className="status-row">
                    <span className="status-badge success">{t('studio.audio.ready')}</span>
                    <button
                        className="btn-text small"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        {t('studio.audio.replace')}
                    </button>
                </div>

                <div className="audio-player-wrapper compact-player">
                    <audio
                        controls
                        src={getAudioUrl(projectId)}
                        className="audio-player"
                    />
                </div>

                <input
                    type="file"
                    ref={fileInputRef}
                    accept="audio/*"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                />
            </div>
        )
    }

    return (
        <div className="audio-upload-container">
            <h2>{t('studio.audio.title')}</h2>
            <p className="description">
                {t('studio.audio.description')}
            </p>

            <div
                className={`dropzone ${isDragging ? 'dragging' : ''} ${isLoading ? 'loading' : ''}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => !isLoading && fileInputRef.current?.click()}
            >
                <input
                    type="file"
                    ref={fileInputRef}
                    accept="audio/*"
                    onChange={handleFileSelect}
                    style={{ display: 'none' }}
                />

                {isLoading ? (
                    <div className="loading-state">
                        <div className="spinner large"></div>
                        <p>{t('studio.audio.uploading')}</p>
                    </div>
                ) : (
                    <div className="upload-state">
                        <div className="upload-icon">☁️</div>
                        <h3>{t('studio.audio.dropzoneTitle')}</h3>
                        <p className="upload-hint">{t('studio.audio.dropzoneHint')}</p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default AudioUpload
