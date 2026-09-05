import { useEffect } from 'react'
import './ConfirmDialog.css'

export default function ConfirmDialog({
    isOpen,
    title,
    message,
    confirmLabel = 'Delete',
    cancelLabel = 'Cancel',
    confirmIcon = '🗑',
    confirmVariant = 'danger',
    onConfirm,
    onCancel,
    children
}) {
    useEffect(() => {
        if (!isOpen) return

        const handleKeyDown = (e) => {
            if (e.key === 'Escape') {
                e.preventDefault()
                onCancel?.()
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [isOpen, onCancel])

    if (!isOpen) return null

    return (
        <div className="confirm-dialog-overlay" onClick={onCancel}>
            <div 
                className="confirm-dialog-box"
                onClick={(ev) => ev.stopPropagation()}
                role="dialog"
                aria-modal="true"
                aria-labelledby="confirm-dialog-title"
            >
                <div className="confirm-dialog-header">
                    {confirmIcon && <span className="confirm-dialog-icon">{confirmIcon}</span>}
                    <h3 id="confirm-dialog-title" className="confirm-dialog-title">{title}</h3>
                </div>

                {message && <p className="confirm-dialog-message">{message}</p>}

                {children && <div className="confirm-dialog-content">{children}</div>}

                <div className="confirm-dialog-actions">
                    <button
                        type="button"
                        className="btn-dialog-cancel"
                        onClick={onCancel}
                    >
                        {cancelLabel}
                    </button>
                    <button
                        type="button"
                        className={`btn-dialog-confirm ${confirmVariant === 'danger' ? 'btn-dialog-danger' : 'btn-dialog-primary'}`}
                        onClick={onConfirm}
                        autoFocus
                    >
                        {confirmIcon && <span className="btn-confirm-icon">{confirmIcon}</span>}
                        {confirmLabel}
                    </button>
                </div>
            </div>
        </div>
    )
}
