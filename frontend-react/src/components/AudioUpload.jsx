import { useState, useRef } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { getAudioUrl } from '../api'

function AudioUpload() {
    const { projectId, uploadAudio, isLoading, audioUploaded } = useProjectStore()
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
                    <span className="status-badge success">✓ Audio Track Ready</span>
                    <button
                        className="btn-text small"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        Replace
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
            <h2>Upload Audio</h2>
            <p className="description">
                Max file size: 50MB. Supported formats: MP3, WAV, AAC.
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
                        <p>Uploading and analyzing audio...</p>
                    </div>
                ) : (
                    <div className="upload-state">
                        <div className="upload-icon">☁️</div>
                        <h3>Click or Drag Audio Here</h3>
                        <p className="upload-hint">Upload your music track to begin</p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default AudioUpload
