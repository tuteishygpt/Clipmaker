import { useProjectStore } from '../stores/projectStore'

function ProjectSelector() {
    const { projects, projectId, project, openProject, loadProjects, resetProject } = useProjectStore()

    const handleSelect = (e) => {
        const id = e.target.value
        if (id) {
            openProject(id)
        }
    }

    return (
        <div className="project-selector">
            <div className="selector-header">
                <h3>Projects</h3>
                <button
                    className="btn-refresh-icon"
                    onClick={() => loadProjects()}
                    title="Refresh list"
                >
                    ↻
                </button>
            </div>

            <select
                value={projectId || ''}
                onChange={handleSelect}
                className="project-dropdown"
            >
                <option value="">Open existing...</option>
                {projects.map(p => {
                    const date = new Date(p.created_at).toLocaleDateString()
                    const desc = p.user_description
                        ? (p.user_description.length > 25 ? p.user_description.slice(0, 25) + '...' : p.user_description)
                        : (p.id.slice(0, 8))

                    // Status icons
                    const statusEmoji =
                        p.status === 'DONE' ? '✅' :
                            p.status === 'RUNNING' ? '⏳' :
                                p.status === 'FAILED' ? '❌' : '✨';

                    return (
                        <option key={p.id} value={p.id}>
                            {statusEmoji} {date} · {desc}
                        </option>
                    )
                })}
            </select>

            {projectId && (
                <div className="selected-project-compact">
                    <div className="project-info">
                        <span className={`status-dot ${project?.status}`}></span>
                        <code className="id">{projectId.slice(0, 8)}</code>
                    </div>
                    <button className="btn-new-minimal" onClick={resetProject}>
                        + NEW
                    </button>
                </div>
            )}

            {!projectId && projects.length === 0 && (
                <p className="empty-hint">No projects found.</p>
            )}
        </div>
    )
}

export default ProjectSelector
