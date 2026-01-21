import { useProjectStore } from '../stores/projectStore'

function Header() {
    const { projectId, project, resetProject } = useProjectStore()

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

            </div>
        </header>
    )
}

export default Header
