import { Link } from 'react-router-dom'
import { useProjectStore } from '../stores/projectStore'
import { useAuthStore } from '../stores/authStore'
import { useBillingStore } from '../stores/billingStore'
import { isSupabaseConfigured } from '../lib/supabase'
import { useTranslation } from '../i18n'

function Header() {
    const { projectId, project, resetProject } = useProjectStore()
    const { user } = useAuthStore()
    const { credits } = useBillingStore()
    const { t } = useTranslation()

    return (
        <header className="app-header">
            <div className="header-content">
                <Link to="/" className="logo-section" style={{ textDecoration: 'none', color: 'inherit' }}>
                    <div className="logo">
                        <span className="logo-icon">🎬</span>
                        <h1>Studio</h1>
                    </div>
                </Link>
                <div className="header-nav" style={{ display: 'flex', gap: '16px', marginLeft: '24px' }}>
                    <Link to="/studio" className="nav-link" style={{ color: 'var(--text-secondary, #aaa)', textDecoration: 'none', fontSize: '14px', fontWeight: 500 }}>{t('nav.studio')}</Link>
                    <Link to="/subtitles" className="nav-link" style={{ color: 'var(--text-secondary, #aaa)', textDecoration: 'none', fontSize: '14px', fontWeight: 500 }}>{t('nav.subtitles')}</Link>
                </div>
            </div>

            <div className="header-right">
                <p className="tagline">{t('nav.tagline')}</p>
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
                                    <span className="cabinet-label">{t('nav.myAccount')}</span>
                                </Link>
                            </>
                        ) : (
                            <Link to="/auth" className="btn-sign-in">
                                {t('nav.signIn')}
                            </Link>
                        )}
                    </div>
                )}
            </div>
        </header>
    )
}

export default Header
