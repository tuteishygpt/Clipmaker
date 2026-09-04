/**
 * Projects View
 * List and manage user's projects with generation history
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../../../stores/authStore'
import { isSupabaseConfigured } from '../../../lib/supabase'
import * as api from '../../../api/index.js'

export default function ProjectsView() {
    const { user } = useAuthStore()
    const [projects, setProjects] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [selectedProject, setSelectedProject] = useState(null)
    const [filter, setFilter] = useState('all') // all, recent, completed
    const [searchQuery, setSearchQuery] = useState('')

    useEffect(() => {
        if (user?.id) {
            loadProjects()
        }
    }, [user?.id])

    const loadProjects = async () => {
        if (!isSupabaseConfigured()) {
            setIsLoading(false)
            return
        }

        try {
            const data = await api.getUserProjects()
            setProjects(data || [])
        } catch (error) {
            console.error('Failed to load projects:', error)
        } finally {
            setIsLoading(false)
        }
    }

    const deleteProject = async (projectId) => {
        if (!confirm('Are you sure you want to delete this project?')) return
        // TODO: Implement deleteProject in API
        alert('Delete implementation pending backend update')
    }

    const filteredProjects = projects.filter(p => {
        // Apply search filter
        if (searchQuery && !p.title.toLowerCase().includes(searchQuery.toLowerCase())) {
            return false
        }
        // Apply status filter
        if (filter === 'recent') {
            const weekAgo = new Date()
            weekAgo.setDate(weekAgo.getDate() - 7)
            return new Date(p.updated_at) > weekAgo
        }
        if (filter === 'completed') {
            return p.status === 'completed'
        }
        return true
    })

    if (isLoading) {
        return (
            <div className="view-loading">
                <div className="spinner large"></div>
                <p>Loading projects...</p>
            </div>
        )
    }

    return (
        <div className="projects-view">
            <div className="view-header">
                <div>
                    <h1>Projects</h1>
                    <p className="view-subtitle">Manage your video generation projects</p>
                </div>
                <div style={{ display: 'flex', gap: '10px' }}>
                    <Link to="/subtitles" className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <span>📝</span>
                        <span>+ Add Subtitles to Video</span>
                    </Link>
                    <Link to="/studio?new=true" className="btn-primary">
                        <span>+ New Project</span>
                    </Link>
                </div>
            </div>

            {/* Filters */}
            <div className="projects-toolbar">
                <div className="search-box">
                    <span className="search-icon">🔍</span>
                    <input
                        type="text"
                        placeholder="Search projects..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                    />
                </div>
                <div className="filter-tabs">
                    <button
                        className={`filter-tab ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        All
                    </button>
                    <button
                        className={`filter-tab ${filter === 'recent' ? 'active' : ''}`}
                        onClick={() => setFilter('recent')}
                    >
                        Recent
                    </button>
                    <button
                        className={`filter-tab ${filter === 'completed' ? 'active' : ''}`}
                        onClick={() => setFilter('completed')}
                    >
                        Completed
                    </button>
                </div>
            </div>

            <div className="projects-container">
                {/* Projects List */}
                <div className="projects-list">
                    {filteredProjects.length > 0 ? (
                        filteredProjects.map(project => {
                            const isStandalone = Boolean(project.standalone_mode || project.settings?.standalone_mode)
                            const projectUrl = isStandalone
                                ? `/subtitles?project=${project.project_id}`
                                : `/studio?project=${project.project_id}`

                            return (
                                <div
                                    key={project.id}
                                    className={`project-card ${selectedProject?.id === project.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedProject(project)}
                                >
                                    <div className="project-thumbnail">
                                        {project.thumbnail_url ? (
                                            <img src={project.thumbnail_url} alt={project.title} />
                                        ) : (
                                            <span className="thumbnail-placeholder">{isStandalone ? '📝' : '🎬'}</span>
                                        )}
                                    </div>
                                    <div className="project-info">
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                            <h3 className="project-title" style={{ margin: 0 }}>{project.title}</h3>
                                            {isStandalone && (
                                                <span
                                                    className="project-badge subtitles-badge"
                                                    style={{
                                                        backgroundColor: 'rgba(110, 0, 255, 0.2)',
                                                        color: '#b388ff',
                                                        padding: '2px 8px',
                                                        borderRadius: '4px',
                                                        fontSize: '11px',
                                                        fontWeight: 600,
                                                        border: '1px solid rgba(110, 0, 255, 0.4)'
                                                    }}
                                                >
                                                    📝 Subtitles
                                                </span>
                                            )}
                                        </div>
                                        <div className="project-meta">
                                            <span className={`project-status status-${project.status}`}>
                                                {project.status}
                                            </span>
                                            <span className="project-date">
                                                {new Date(project.updated_at).toLocaleDateString()}
                                            </span>
                                        </div>
                                    </div>
                                    <div className="project-actions">
                                        <Link
                                            to={projectUrl}
                                            className="btn-icon"
                                            title={isStandalone ? "Open in Subtitles Studio" : "Open in Editor"}
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            {isStandalone ? '📝' : '🎥'}
                                        </Link>
                                        <button
                                            className="btn-icon danger"
                                            title="Delete"
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                deleteProject(project.id)
                                            }}
                                        >
                                            🗑️
                                        </button>
                                    </div>
                                </div>
                            )
                        })
                    ) : (
                        <div className="empty-state">
                            <span className="empty-icon">📁</span>
                            <h3>No projects found</h3>
                            <p>
                                {searchQuery
                                    ? 'Try a different search term'
                                    : 'Start by creating your first project'
                                }
                            </p>
                            {!searchQuery && (
                                <Link to="/studio?new=true" className="btn-primary">Create Project</Link>
                            )}
                        </div>
                    )}
                </div>

                {/* Project Details Panel */}
                {selectedProject && (
                    <div className="project-details-panel">
                        <div className="panel-header">
                            <h2>{selectedProject.title}</h2>
                            <button
                                className="btn-close"
                                onClick={() => setSelectedProject(null)}
                            >
                                ✕
                            </button>
                        </div>

                        <div className="panel-content">
                            <div className="detail-section">
                                <h4>Project Information</h4>
                                <div className="detail-grid">
                                    <div className="detail-item">
                                        <span className="detail-label">Status</span>
                                        <span className={`detail-value status-${selectedProject.status}`}>
                                            {selectedProject.status}
                                        </span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="detail-label">Created</span>
                                        <span className="detail-value">
                                            {new Date(selectedProject.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="detail-label">Last Updated</span>
                                        <span className="detail-value">
                                            {new Date(selectedProject.updated_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                    <div className="detail-item">
                                        <span className="detail-label">Visual Style</span>
                                        <span className="detail-value">
                                            {selectedProject.settings?.visual_style || 'Default'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {selectedProject.settings && (
                                <div className="detail-section">
                                    <h4>Settings</h4>
                                    <div className="settings-display">
                                        <pre>{JSON.stringify(selectedProject.settings, null, 2)}</pre>
                                    </div>
                                </div>
                            )}

                            <div className="detail-section">
                                <h4>Generation History</h4>
                                <p className="history-placeholder">
                                    Generation history will be available here.
                                </p>
                            </div>
                        </div>

                        <div className="panel-footer">
                            <Link
                                to={selectedProject.standalone_mode || selectedProject.settings?.standalone_mode
                                    ? `/subtitles?project=${selectedProject.project_id}`
                                    : `/studio?project=${selectedProject.project_id}`}
                                className="btn-primary full-width"
                            >
                                {selectedProject.standalone_mode || selectedProject.settings?.standalone_mode
                                    ? 'Open in Subtitles Studio'
                                    : 'Open in Editor'}
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
