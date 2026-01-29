import { useEffect } from 'react'
import LandingFooter from './LandingFooter'
import LandingNav from './LandingNav'

function LegalPage({ title, children }) {
    useEffect(() => {
        document.body.classList.add('landing-body')
        return () => document.body.classList.remove('landing-body')
    }, [])

    return (
        <div className="landing-page">
            <LandingNav />
            <main className="landing-main legal-main">
                <section className="landing-section">
                    <div className="container legal-card">
                        <h1 className="legal-title">{title}</h1>
                        <div className="legal-content">{children}</div>
                    </div>
                </section>
            </main>
            <LandingFooter />
        </div>
    )
}

export default LegalPage
