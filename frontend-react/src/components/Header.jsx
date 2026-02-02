import { Link } from 'react-router-dom'
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
                <Link to="/" className="logo-section" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <div className="logo">
                        <span className="logo-icon">🎬</span>
                        <h1>Studio</h1>
                    </div>
                </Link>
                <div className="header-nav">
                    {/* Optional: Add navigation links here if needed */}
                </div>
            </div>

            <div className="header-right">
                <p className="tagline">AI-powered music video generator</p>
                {/* Right side - User info */}
                {isSupabaseConfigured() && (
                    <div className="header-actions">
                        {user ? (
                            <>
                                <div className="header-credits">
                                    <span className="credits-icon">💎</span>
                                    <span className="credits-value">{credits}</span>
                                </div>
                                <Link to="/cabinet" className="btn-cabinet">
                                    <span className="user-initial">
                                        {user.email?.charAt(0).toUpperCase() || '?'}
                                    </span>
                                    <span className="cabinet-label">My Account</span>
                                </Link>
                            </>
                        ) : (
                            <Link to="/auth" className="btn-sign-in">
                                Sign In
                            </Link>
                        )}
                    </div>
                )}
            </div>
        </header>
    )
}

export default Header
