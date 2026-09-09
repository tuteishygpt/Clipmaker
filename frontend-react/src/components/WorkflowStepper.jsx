import { useProjectStore } from '../stores/projectStore'
import { useTranslation } from '../i18n'
import './WorkflowStepper.css'

const STEP_DEFS = [
    { id: 'setup', icon: '📁' },
    { id: 'upload', icon: '🎵' },
    { id: 'generate', icon: '🎨' },
    { id: 'render', icon: '🎬' },
    { id: 'complete', icon: '✅' }
]

function WorkflowStepper() {
    const { currentStep, projectId, setStep } = useProjectStore()
    const { t } = useTranslation()

    const currentIndex = STEP_DEFS.findIndex(s => s.id === currentStep)

    const handleStepClick = (step, index) => {
        // Only allow clicking on completed or current steps
        if (index <= currentIndex && projectId) {
            setStep(step.id)
        }
    }

    return (
        <div className="workflow-stepper-vertical">
            {STEP_DEFS.map((step, index) => {
                const isActive = step.id === currentStep
                const isCompleted = index < currentIndex
                const isClickable = index <= currentIndex && projectId
                const label = t(`studio.stepper.${step.id}`)

                return (
                    <div
                        key={step.id}
                        className={`wf-vstep ${isActive ? 'active' : ''} ${isCompleted ? 'completed' : ''} ${isClickable ? 'clickable' : ''}`}
                        onClick={() => handleStepClick(step, index)}
                        title={label}
                    >
                        <div className="wf-vstep-indicator">
                            {step.icon}
                        </div>
                        {index < STEP_DEFS.length - 1 && (
                            <div className={`wf-vline ${isCompleted ? 'completed' : ''}`} />
                        )}
                    </div>
                )
            })}
        </div>
    )
}

export default WorkflowStepper
