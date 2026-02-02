import { useState } from 'react'
import { Link } from 'react-router-dom'
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
                <Link className="brand" to="/">
                    <span className="brand-mark" aria-hidden="true">◆</span>
                    <span className="brand-name">HukFlow</span>
                </Link>

                <nav className="landing-nav-links" aria-label="Primary">
                    {navLinks.map((link) => (
                        <a key={link.href} href={link.href} className="nav-link">
                            {link.label}
                        </a>
                    ))}
                </nav>

                <div className="landing-nav-actions">
                    {!user && (
                        <Link className="nav-link login-link" to="/auth">Login</Link>
                    )}
                    {user ? (
                        <Link className="btn btn-secondary" to="/studio">Open Studio</Link>
                    ) : (
                        <Link className="btn btn-primary" to="/auth">Start free</Link>
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
                        <Link className="btn btn-secondary" to="/auth">Login</Link>
                    )}
                    {user ? (
                        <Link className="btn btn-primary" to="/studio">Open Studio</Link>
                    ) : (
                        <Link className="btn btn-primary" to="/auth">Start free</Link>
                    )}
                </div>
            </div>
        </header>
    )
}

export default LandingNav
