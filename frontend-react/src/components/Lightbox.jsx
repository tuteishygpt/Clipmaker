import { useState } from 'react'
import { useProjectStore } from '../stores/projectStore'
import { fixImageUrl } from '../utils'

function Lightbox() {
    const { lightboxSrc, hideLightbox } = useProjectStore()
    const [imgError, setImgError] = useState(false)

    if (!lightboxSrc) return null

    const handleClose = () => {
        setImgError(false)
        hideLightbox()
    }

    const handleBackdropClick = (e) => {
        if (e.target === e.currentTarget) {
            handleClose()
        }
    }

    const imageUrl = fixImageUrl(lightboxSrc)

    return (
        <div
            className="lightbox"
            onClick={handleBackdropClick}
            style={{ display: 'flex' }}
        >
            <span className="lightbox-close" onClick={handleClose}>&times;</span>

            {imgError ? (
                <div className="image-placeholder" style={{ maxWidth: '80%', maxHeight: '80%', padding: '40px', borderRadius: '12px' }}>
                    <span className="icon">⚠️</span>
                    <span style={{ color: 'white' }}>Failed to load full-size image</span>
                </div>
            ) : (
                <img
                    className="lightbox-img"
                    src={imageUrl}
                    alt="Full size preview"
                    onError={() => setImgError(true)}
                />
            )}
        </div>
    )
}

export default Lightbox
