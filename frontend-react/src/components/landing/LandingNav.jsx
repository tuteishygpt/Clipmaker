import { useState } from 'react'
import { useAuthStore } from '../../stores/authStore'

const navLinks = [
    { label: 'Product', href: '#features' },
    { label: 'How it works', href: '#how-it-works' },
    { label: 'Examples', href: '#examples' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'FAQ', href: '#faq' }
]

function LandingNav() {
    const { user } = useAuthStore()
    const [isOpen, setIsOpen] = useState(false)

    return (
        <header className="landing-nav">
            <div className="landing-nav-inner">
                <a className="brand" href="/">
                    <span className="brand-mark" aria-hidden="true">◆</span>
                    <span className="brand-name">HukFlow</span>
                </a>

                <nav className="landing-nav-links" aria-label="Primary">
                    {navLinks.map((link) => (
                        <a key={link.href} href={link.href} className="nav-link">
                            {link.label}
                        </a>
                    ))}
                </nav>

                <div className="landing-nav-actions">
                    {!user && (
                        <a className="nav-link login-link" href="/auth">Login</a>
                    )}
                    {user ? (
                        <a className="btn btn-secondary" href="/studio">Open Studio</a>
                    ) : (
                        <a className="btn btn-primary" href="/auth">Start free</a>
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
                            {link.label}
                        </a>
                    ))}
                </div>
                <div className="mobile-menu-actions">
                    {!user && (
                        <a className="btn btn-secondary" href="/auth">Login</a>
                    )}
                    {user ? (
                        <a className="btn btn-primary" href="/studio">Open Studio</a>
                    ) : (
                        <a className="btn btn-primary" href="/auth">Start free</a>
                    )}
                </div>
            </div>
        </header>
    )
}

export default LandingNav
