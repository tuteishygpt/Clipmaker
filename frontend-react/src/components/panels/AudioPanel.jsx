import { useState, useRef } from 'react'
import { useProjectStore } from '../../stores/projectStore'
import { getAudioUrl } from '../../api'

function AudioPanel() {
    const { projectId, uploadAudio } = useProjectStore()
    const [status, setStatus] = useState('')
    const fileInputRef = useRef(null)
    const audioRef = useRef(null)

    const handleUpload = async () => {
        if (!projectId) {
            setStatus('Create a project first.')
            return
        }

        const file = fileInputRef.current?.files[0]
        if (!file) {
            setStatus('Select an audio file.')
            return
        }

        setStatus('Uploading...')
        const result = await uploadAudio(file)

        if (result) {
            setStatus(result.message || 'Uploaded successfully!')
            // Reload audio player
            if (audioRef.current) {
                audioRef.current.src = getAudioUrl(projectId)
                audioRef.current.style.display = 'block'
            }
        } else {
            setStatus('Upload failed.')
        }
    }

    return (
        <section className="panel">
            <h2>Audio</h2>
            <input
                type="file"
                ref={fileInputRef}
                accept="audio/*"
            />
            <button
                onClick={handleUpload}
                className="full-width"
                style={{ marginTop: '10px' }}
            >
                Upload
            </button>
            {status && <div className="muted">{status}</div>}
            <audio
                ref={audioRef}
                controls
                style={{ width: '100%', marginTop: '10px', display: 'none' }}
            />
        </section>
    )
}

export default AudioPanel
