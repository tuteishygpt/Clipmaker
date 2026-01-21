import { useProjectStore } from '../../stores/projectStore'

function Toast() {
    const { toasts, removeToast } = useProjectStore()

    if (toasts.length === 0) return null

    return (
        <div className="toast-container">
            {toasts.map(toast => (
                <div
                    key={toast.id}
                    className={`toast toast-${toast.type}`}
                    onClick={() => removeToast(toast.id)}
                >
                    <div className="toast-icon">
                        {toast.type === 'success' && '✅'}
                        {toast.type === 'error' && '❌'}
                        {toast.type === 'info' && 'ℹ️'}
                    </div>
                    <div className="toast-message">{toast.message}</div>
                </div>
            ))}
        </div>
    )
}

export default Toast
