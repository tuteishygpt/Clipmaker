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
                <h3>Open Existing</h3>
                <button
                    className="btn-refresh"
                    onClick={loadProjects}
                    title="Refresh projects"
                >
                    ↻
                </button>
            </div>

            <select
                value={projectId || ''}
                onChange={handleSelect}
                className="project-dropdown"
            >
                <option value="">Select a project...</option>
                {projects.map(p => (
                    <option key={p.id} value={p.id}>
                        {new Date(p.created_at).toLocaleDateString()} · {p.status}
                    </option>
                ))}
            </select>

            {projectId && (
                <div className="selected-project-card">
                    <div className="project-meta">
                        <span className="label">Current Project</span>
                        <code className="id">{projectId.slice(0, 8)}...</code>
                        {project?.status && (
                            <span className={`status-tag ${project.status}`}>{project.status}</span>
                        )}
                    </div>
                    <button className="btn-reset" onClick={resetProject} title="Start New Project">
                        NEW
                    </button>
                </div>
            )}

            {!projectId && projects.length === 0 && (
                <p className="empty-hint">No projects yet. Create one below ↓</p>
            )}
        </div>
    )
}

export default ProjectSelector
