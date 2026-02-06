import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, Link } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import { useBillingStore } from './stores/billingStore'
import { isSupabaseConfigured } from './lib/supabase'

// Editor (existing app)
import { useProjectStore } from './stores/projectStore'
import { getDownloadUrl } from './api'
import WorkflowStepper from './components/WorkflowStepper'
import ProjectSelector from './components/ProjectSelector'
import ProjectForm from './components/ProjectForm'
import AudioUpload from './components/AudioUpload'
import GenerationControls from './components/GenerationControls'
import Preview from './components/Preview'
import Scenes from './components/Scenes'
import AnalysisModal from './components/AnalysisModal'
import Lightbox from './components/Lightbox'
import Toast from './components/common/Toast'
import LandingPage from './components/landing/LandingPage'
import LegalPage from './components/landing/LegalPage'
import SubtitleStandalonePage from './components/SubtitleStandalonePage'
import SubtitlePanel from './components/SubtitlePanel'

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
    const { loadProjects, stopPolling, projectId, refreshJobs, videoOutput } = useProjectStore()
    const { user } = useAuthStore()
    const { canGenerate, generationBlockReason = null, credits } = useBillingStore()
    const [showSubtitles, setShowSubtitles] = useState(false)
    const [showAnalysis, setShowAnalysis] = useState(false)

    useEffect(() => {
        loadProjects()
        if (projectId) {
            refreshJobs()
        }
        return () => stopPolling()
    }, [loadProjects, stopPolling, projectId, refreshJobs])

    return (
        <div className="app">
            {/* Header moved to sidebar */}

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
                    {/* Header Section in Sidebar */}
                    <div className="sidebar-header-section">
                        <Link to="/" className="sidebar-app-logo">
                            <span className="logo-icon">🎬</span>
                            <span className="logo-text">Studio</span>
                        </Link>
                        <p className="sidebar-tagline">AI-powered music video generator</p>

                        {/* User Auth */}
                        {isSupabaseConfigured() && (
                            <div className="sidebar-auth-section">
                                {user ? (
                                    <Link to="/cabinet" className="sidebar-user-card">
                                        <div className="user-avatar">
                                            {user.email?.charAt(0).toUpperCase() || '?'}
                                        </div>
                                        <div className="user-info-col">
                                            <span className="user-label">My Account</span>
                                            <span className="credits-badge">💎 {credits}</span>
                                        </div>
                                    </Link>
                                ) : (
                                    <Link to="/auth" className="sidebar-signin-btn">
                                        Sign In
                                    </Link>
                                )}
                            </div>
                        )}
                    </div>

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

                            {/* Tools Section - Analysis, Subtitles, Download */}
                            <div className="left-section">
                                <div className="divider"><span>TOOLS</span></div>
                                <div className="sidebar-tools-buttons">
                                    <button
                                        className={`sidebar-tool-btn ${showAnalysis ? 'active' : ''}`}
                                        onClick={() => {
                                            setShowAnalysis(!showAnalysis)
                                            if (!showAnalysis) setShowSubtitles(false)
                                        }}
                                    >
                                        <span className="btn-icon-emoji">📊</span>
                                        Analysis
                                    </button>
                                    <button
                                        className={`sidebar-tool-btn ${showSubtitles ? 'active' : ''}`}
                                        onClick={() => {
                                            setShowSubtitles(!showSubtitles)
                                            if (!showSubtitles) setShowAnalysis(false)
                                        }}
                                    >
                                        <span className="btn-icon-emoji">📝</span>
                                        Subtitles
                                    </button>
                                    {videoOutput && (
                                        <a
                                            href={getDownloadUrl(projectId)}
                                            download
                                            className="sidebar-tool-btn"
                                        >
                                            <span className="btn-icon-emoji">⬇️</span>
                                            Download
                                        </a>
                                    )}
                                </div>
                            </div>

                            {/* Inline Tool Panels in Sidebar */}
                            {showAnalysis && (
                                <div className="left-section sidebar-tool-panel">
                                    <AnalysisModal inSidebar={true} onClose={() => setShowAnalysis(false)} />
                                </div>
                            )}

                            {showSubtitles && (
                                <div className="left-section sidebar-tool-panel">
                                    <SubtitlePanel
                                        projectId={projectId}
                                        isExpanded={true}
                                        onToggle={() => setShowSubtitles(false)}
                                        inSidebar={true}
                                    />
                                </div>
                            )}

                            <div className="left-section">
                                <div className="divider"><span>ACTIONS</span></div>
                                <GenerationControls />
                            </div>
                        </>
                    )}
                </aside>

                {/* Center - Preview & Scenes (maximized video) */}
                <section className="content-area content-area-wide content-area-maximized">
                    <div className="preview-workflow-container preview-maximized">
                        <Preview showSubtitlePreview={showSubtitles} />
                        {projectId && <WorkflowStepper />}
                    </div>
                    <Scenes />
                </section>
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
        initialize()
    }, [initialize])

    // Load billing when user changes
    useEffect(() => {
        if (user?.id) {
            loadBillingData(user.id)
        } else {
            clearBillingData()
        }
    }, [user?.id, loadBillingData, clearBillingData])

    return (
        <BrowserRouter>
            <Routes>
                {/* Marketing Home */}
                <Route path="/" element={<LandingPage />} />

                {/* Main Editor - Works without auth */}
                <Route path="/studio" element={<EditorView />} />

                {/* Standalone Subtitles Tool */}
                <Route path="/subtitles" element={<SubtitleStandalonePage />} />

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

                <Route
                    path="/privacy"
                    element={(
                        <LegalPage title="Privacy Policy">
                            <p>
                                This page will outline how HukFlow collects and uses account, billing, and usage data.
                                Replace this placeholder with your official privacy policy.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/terms"
                    element={(
                        <LegalPage title="Terms of Service">
                            <p>
                                This page will describe the terms that govern use of HukFlow. Replace this placeholder
                                with your official terms of service.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/refund"
                    element={(
                        <LegalPage title="Refund Policy">
                            <p>
                                This page will explain refunds and billing adjustments for HukFlow subscriptions.
                                Replace this placeholder with your official refund policy.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/pricing"
                    element={(
                        <LegalPage title="Pricing">
                            <p>
                                Review HukFlow pricing tiers, included credits, and usage details on this page.
                                Replace this placeholder with your official pricing content.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/partners"
                    element={(
                        <LegalPage title="Partners">
                            <p>
                                Share partnership opportunities, media kits, and collaboration details here.
                                Replace this placeholder with your official partner information.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/contact"
                    element={(
                        <LegalPage title="Contact Us">
                            <p>
                                List your support channels, response times, and preferred contact methods here.
                                Replace this placeholder with your official contact information.
                            </p>
                        </LegalPage>
                    )}
                />

                {/* Catch all - redirect to home */}
                <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
