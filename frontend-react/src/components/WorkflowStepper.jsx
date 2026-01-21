import { useProjectStore } from '../stores/projectStore'

const STEPS = [
    { id: 'setup', label: 'Create Project', icon: '📁' },
    { id: 'upload', label: 'Upload Audio', icon: '🎵' },
    { id: 'generate', label: 'Generate Scenes', icon: '🎨' },
    { id: 'render', label: 'Render Video', icon: '🎬' },
    { id: 'complete', label: 'Complete', icon: '✅' }
]

function WorkflowStepper() {
    const { currentStep, projectId, setStep } = useProjectStore()

    const currentIndex = STEPS.findIndex(s => s.id === currentStep)

    const handleStepClick = (step, index) => {
        // Only allow clicking on completed or current steps
        if (index <= currentIndex && projectId) {
            setStep(step.id)
        }
    }

    return (
        <div className="workflow-stepper">
            <h3 className="stepper-title">Workflow</h3>
            <div className="steps-container">
                {STEPS.map((step, index) => {
                    const isActive = step.id === currentStep
                    const isCompleted = index < currentIndex
                    const isClickable = index <= currentIndex && projectId

                    return (
                        <div
                            key={step.id}
                            className={`step ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isClickable ? 'clickable' : ''}`}
                            onClick={() => handleStepClick(step, index)}
                        >
                            <div className="step-indicator">
                                {isCompleted ? (
                                    <span className="check">✓</span>
                                ) : (
                                    <span className="step-icon">{step.icon}</span>
                                )}
                            </div>
                            <div className="step-content">
                                <span className="step-label">{step.label}</span>
                                {index < STEPS.length - 1 && (
                                    <div className={`step-line ${isCompleted ? 'completed' : ''}`} />
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default WorkflowStepper
