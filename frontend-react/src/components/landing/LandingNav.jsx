import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../stores/authStore'
import { useTranslation } from '../../i18n'

const navLinks = [
    { key: 'nav.product', defaultLabel: 'Product', href: '#features' },
    { key: 'nav.howItWorks', defaultLabel: 'How it works', href: '#how-it-works' },
    { key: 'nav.examples', defaultLabel: 'Examples', href: '#examples' },
    { key: 'nav.pricing', defaultLabel: 'Pricing', href: '#pricing' },
    { key: 'nav.faq', defaultLabel: 'FAQ', href: '#faq' }
]

function LandingNav() {
    const { user } = useAuthStore()
    const { t } = useTranslation()
    const [isOpen, setIsOpen] = useState(false)

    return (
        <header className="landing-nav">
            <div className="landing-nav-inner">
                <Link className="brand" to="/">
                    <span className="brand-mark" aria-hidden="true">◆</span>
                    <span className="brand-name">HukFlow</span>
                </Link>

                <nav className="landing-nav-links" aria-label="Primary">
                    {navLinks.map((link) => (
                        <a key={link.href} href={link.href} className="nav-link">
                            {t(link.key) || link.defaultLabel}
                        </a>
                    ))}
                    <Link to="/subtitles" className="nav-link">
                        {t('nav.subtitles')}
                    </Link>
                </nav>

                <div className="landing-nav-actions">

                    {!user && (
                        <Link className="nav-link login-link" to="/auth">{t('nav.login')}</Link>
                    )}
                    {user ? (
                        <Link className="btn btn-secondary" to="/studio">{t('nav.openStudio')}</Link>
                    ) : (
                        <Link className="btn btn-primary" to="/auth">{t('nav.startFree')}</Link>
                    )}
                    <button
                        className="menu-toggle"
                        type="button"
                        aria-label="Toggle navigation"
                        aria-expanded={isOpen}
                        onClick={() => setIsOpen((prev) => !prev)}
                    >
                        <span />
                        <span />
                        <span />
                    </button>
                </div>
            </div>

            <div className={`mobile-menu ${isOpen ? 'open' : ''}`}>
                <div className="mobile-menu-links">
                    {navLinks.map((link) => (
                        <a
                            key={link.href}
                            href={link.href}
                            className="nav-link"
                            onClick={() => setIsOpen(false)}
                        >
                            {t(link.key) || link.defaultLabel}
                        </a>
                    ))}
                    <Link to="/subtitles" className="nav-link" onClick={() => setIsOpen(false)}>
                        {t('nav.subtitles')}
                    </Link>
                </div>
                <div className="mobile-menu-actions">
                    {!user && (
                        <Link className="btn btn-secondary" to="/auth">{t('nav.login')}</Link>
                    )}
                    {user ? (
                        <Link className="btn btn-primary" to="/studio">{t('nav.openStudio')}</Link>
                    ) : (
                        <Link className="btn btn-primary" to="/auth">{t('nav.startFree')}</Link>
                    )}
                </div>
            </div>
        </header>
    )
}

export default LandingNav
