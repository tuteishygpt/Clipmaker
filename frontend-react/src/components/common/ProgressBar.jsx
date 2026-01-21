function ProgressBar({ label, progress, step }) {
    return (
        <div className="progress-container">
            <div className="progress-label">
                <span>{label}: {progress}%</span>
            </div>
            <div className="progress-bg">
                <div
                    className="progress-fill"
                    style={{ width: `${progress}%` }}
                />
            </div>
            {step && (
                <div className="progress-step">Step: {step}</div>
            )}
        </div>
    )
}

export default ProgressBar
