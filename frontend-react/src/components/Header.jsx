import { useProjectStore } from '../stores/projectStore'
import { useAuthStore } from '../stores/authStore'
import { useBillingStore } from '../stores/billingStore'
import { isSupabaseConfigured } from '../lib/supabase'

function Header() {
    const { projectId, project, resetProject } = useProjectStore()
    const { user } = useAuthStore()
    const { credits } = useBillingStore()

    return (
        <header className="app-header">
            <div className="header-content">
                <div className="logo-section">
                    <div className="logo">
                        <span className="logo-icon">🎬</span>
                        <h1>Clipmaker</h1>
                    </div>
                    <p className="tagline">AI-powered music video generator</p>
                </div>

                {/* Right side - User info */}
                {isSupabaseConfigured() && (
                    <div className="header-actions">
                        {user ? (
                            <>
                                <div className="header-credits">
                                    <span className="credits-icon">💎</span>
                                    <span className="credits-value">{credits}</span>
                                </div>
                                <a href="/cabinet" className="btn-cabinet">
                                    <span className="user-initial">
                                        {user.email?.charAt(0).toUpperCase() || '?'}
                                    </span>
                                    <span className="cabinet-label">My Account</span>
                                </a>
                            </>
                        ) : (
                            <a href="/auth" className="btn-sign-in">
                                Sign In
                            </a>
                        )}
                    </div>
                )}
            </div>
        </header>
    )
}

export default Header
