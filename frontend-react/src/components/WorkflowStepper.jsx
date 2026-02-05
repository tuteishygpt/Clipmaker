import { useProjectStore } from '../stores/projectStore'
import './WorkflowStepper.css'

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
        <div className="workflow-stepper-vertical">
            {STEPS.map((step, index) => {
                const isActive = step.id === currentStep
                const isCompleted = index < currentIndex
                const isClickable = index <= currentIndex && projectId

                return (
                    <div
                        key={step.id}
                        className={`wf-vstep ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isClickable ? 'clickable' : ''}`}
                        onClick={() => handleStepClick(step, index)}
                        title={step.label}
                    >
                        <div className="wf-vstep-indicator">
                            {step.icon}
                        </div>
                        {index < STEPS.length - 1 && (
                            <div className={`wf-vline ${isCompleted ? 'completed' : ''}`} />
                        )}
                    </div>
                )
            })}
        </div>
    )
}

export default WorkflowStepper
