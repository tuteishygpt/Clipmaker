import { useEffect } from 'react'
import { useProjectStore } from './stores/projectStore'
import Header from './components/Header'
import WorkflowStepper from './components/WorkflowStepper'
import ProjectSelector from './components/ProjectSelector'
import ProjectForm from './components/ProjectForm'
import AudioUpload from './components/AudioUpload'
import GenerationControls from './components/GenerationControls'
import Preview from './components/Preview'
import Scenes from './components/Scenes'
import Analysis from './components/Analysis'
import Lightbox from './components/Lightbox'
import Toast from './components/common/Toast'
import './styles/index.css'

function App() {
    const { loadProjects, stopPolling } = useProjectStore()

    useEffect(() => {
        loadProjects()
        return () => stopPolling()
    }, [loadProjects, stopPolling])

    const { projectId } = useProjectStore()

    return (
        <div className="app">
            <Header />

            <main className="main-layout">
                {/* Left Panel - Project Management & Inputs */}
                <aside className="control-panel">
                    <ProjectSelector />

                    {!projectId && (
                        <div className="project-creation-wrapper">
                            <div className="divider"><span>OR</span></div>
                            <ProjectForm />
                        </div>
                    )}

                    {projectId && (
                        <>
                            <div className="left-section">
                                <div className="divider"><span>AUDIO</span></div>
                                <AudioUpload />
                            </div>

                            <div className="left-section">
                                <div className="divider"><span>ACTIONS</span></div>
                                <GenerationControls />
                            </div>
                        </>
                    )}
                </aside>

                {/* Center - Preview & Scenes */}
                <section className="content-area">
                    <Preview />
                    <Scenes />
                </section>

                {/* Right Panel - Workflow & Status */}
                <aside className="details-panel">
                    {projectId && (
                        <div className="sticky-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                            <WorkflowStepper />
                            <Analysis />
                        </div>
                    )}
                    {!projectId && (
                        <div className="empty-state-start">
                            <span className="arrow-left">←</span>
                            <p>Start by selecting or creating a project</p>
                        </div>
                    )}
                </aside>
            </main>

            <Lightbox />
            <Toast />
        </div>
    )
}

// CurrentStepPanel removed as controls are now always visible on the left

export default App
