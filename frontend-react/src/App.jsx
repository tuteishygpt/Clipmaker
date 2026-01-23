import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useBillingStore } from './stores/billingStore'
import { isSupabaseConfigured } from './lib/supabase'

// Editor (existing app)
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

// Cabinet (new module)
import AuthPage from './components/auth/AuthPage'
import CabinetLayout from './components/cabinet/CabinetLayout'

import './styles/index.css'

// Protected Route wrapper
function ProtectedRoute({ children }) {
    const { user, isLoading, isInitialized } = useAuthStore()

    if (!isInitialized || isLoading) {
        return (
            <div className="loading-screen">
                <div className="spinner large"></div>
                <p>Loading...</p>
            </div>
        )
    }

    if (!user) {
        return <Navigate to="/auth" replace />
    }

    return children
}

// Editor view (existing functionality)
function EditorView() {
    const { loadProjects, stopPolling, projectId, refreshJobs } = useProjectStore()
    const { user } = useAuthStore()
    const { canGenerate, generationBlockReason = null } = useBillingStore()

    useEffect(() => {
        loadProjects()
        if (projectId) {
            refreshJobs()
        }
        return () => stopPolling()
    }, [loadProjects, stopPolling, projectId, refreshJobs])

    return (
        <div className="app">
            <Header user={user} />

            {/* Generation Warning Banner */}
            {user && !canGenerate && generationBlockReason && (
                <div className="generation-warning-banner">
                    <span className="warning-icon">⚠️</span>
                    <span>{generationBlockReason}</span>
                    <a href="/cabinet" className="btn-warning-action">Manage Account</a>
                </div>
            )}

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

// Auth wrapper for the auth page
function AuthWrapper() {
    const { user } = useAuthStore()

    if (user) {
        return <Navigate to="/cabinet" replace />
    }

    return <AuthPage onSuccess={() => window.location.href = '/cabinet'} />
}

function App() {
    const { initialize, isInitialized } = useAuthStore()
    const { loadBillingData, clearBillingData } = useBillingStore()
    const { user } = useAuthStore()

    // Initialize auth on mount
    useEffect(() => {
        if (isSupabaseConfigured()) {
            initialize()
        }
    }, [initialize])

    // Load billing when user changes
    useEffect(() => {
        if (user?.id) {
            loadBillingData(user.id)
        } else {
            clearBillingData()
        }
    }, [user?.id, loadBillingData, clearBillingData])

    // If Supabase is not configured, just show the editor
    if (!isSupabaseConfigured()) {
        return <EditorView />
    }

    return (
        <BrowserRouter>
            <Routes>
                {/* Main Editor - Works without auth */}
                <Route path="/" element={<EditorView />} />

                {/* Auth page */}
                <Route path="/auth" element={<AuthWrapper />} />

                {/* User Cabinet - Protected */}
                <Route
                    path="/cabinet"
                    element={
                        <ProtectedRoute>
                            <CabinetLayout />
                        </ProtectedRoute>
                    }
                />

                {/* Password reset callback */}
                <Route path="/reset-password" element={<AuthWrapper />} />

                {/* Catch all - redirect to home */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
