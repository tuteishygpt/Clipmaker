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
import LandingPage from './components/landing/LandingPage'
import LegalPage from './components/landing/LegalPage'

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

    return (
        <BrowserRouter>
            <Routes>
                {/* Marketing Home */}
                <Route path="/" element={<LandingPage />} />

                {/* Main Editor - Works without auth */}
                <Route path="/studio" element={<EditorView />} />

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
                                HukFlow collects the minimum account information needed to authenticate you, manage
                                billing, and deliver the product experience. We also store usage analytics to improve
                                generation quality and reliability.
                            </p>
                            <p>
                                You can request access, correction, or deletion of your data by contacting our team.
                                This page will be updated with the full privacy policy and regional disclosures.
                            </p>
                            <p>
                                Questions about data practices can be sent to <a href="mailto:privacy@hukflow.ai">privacy@hukflow.ai</a>.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/terms"
                    element={(
                        <LegalPage title="Terms of Service">
                            <p>
                                By using HukFlow, you agree to follow our acceptable use guidelines and respect content
                                ownership rights. You retain ownership of your source audio and generated outputs.
                            </p>
                            <p>
                                Subscription access and usage limits are defined by your current plan. This page will
                                be updated with the complete terms, including billing, limitations, and dispute
                                resolution policies.
                            </p>
                            <p>
                                Questions about terms can be sent to <a href="mailto:legal@hukflow.ai">legal@hukflow.ai</a>.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/refund"
                    element={(
                        <LegalPage title="Refund Policy">
                            <p>
                                Refunds are evaluated on a case-by-case basis based on usage and billing history. If
                                you have questions about a charge, please reach out within 14 days of the transaction.
                            </p>
                            <p>
                                We'll review your request and respond with next steps, including any account credit or
                                billing adjustments available under your plan.
                            </p>
                            <p>
                                Contact <a href="mailto:billing@hukflow.ai">billing@hukflow.ai</a> to start a refund review.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/pricing"
                    element={(
                        <LegalPage title="Pricing">
                            <p>
                                HukFlow offers flexible plans with monthly credits, export options, and support levels
                                tailored to individual creators and teams.
                            </p>
                            <p>
                                Start free to explore the workflow, then upgrade when you are ready to publish more
                                videos or unlock advanced export formats.
                            </p>
                            <p>
                                For current plan details, contact <a href="mailto:sales@hukflow.ai">sales@hukflow.ai</a>.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/partners"
                    element={(
                        <LegalPage title="Partners">
                            <p>
                                We collaborate with labels, artist teams, and creator platforms to bring music visuals
                                to wider audiences. Partners can access co-marketing opportunities and early feature
                                pilots.
                            </p>
                            <p>
                                If you are interested in a partnership, reach out with your goals and audience size.
                            </p>
                            <p>
                                Email <a href="mailto:partners@hukflow.ai">partners@hukflow.ai</a> to start a conversation.
                            </p>
                        </LegalPage>
                    )}
                />
                <Route
                    path="/contact"
                    element={(
                        <LegalPage title="Contact Us">
                            <p>
                                Need help with a project or subscription? Our team is available Monday through Friday
                                to assist with onboarding, billing, and technical questions.
                            </p>
                            <p>
                                For product support, email <a href="mailto:hello@hukflow.ai">hello@hukflow.ai</a>.
                                For urgent billing issues, use <a href="mailto:billing@hukflow.ai">billing@hukflow.ai</a>.
                            </p>
                            <p>
                                We aim to respond within one business day.
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
