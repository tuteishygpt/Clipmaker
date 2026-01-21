import { useState } from 'react'
import { useProjectStore } from '../../stores/projectStore'

function ProjectPanel() {
    const {
        projects,
        project,
        projectId,
        openProject,
        createProject,
        loadProjects
    } = useProjectStore()

    const [selectedId, setSelectedId] = useState('')
    const [format, setFormat] = useState('9:16')
    const [style, setStyle] = useState('cinematic')
    const [renderPreset, setRenderPreset] = useState('fast')
    const [subtitles, setSubtitles] = useState(true)
    const [userDescription, setUserDescription] = useState('')
    const [characterDescription, setCharacterDescription] = useState('')

    const handleOpen = async () => {
        if (selectedId) {
            await openProject(selectedId)
        }
    }

    const handleCreate = async () => {
        await createProject({
            format,
            style,
            subtitles,
            user_description: userDescription,
            character_description: characterDescription,
            render_preset: renderPreset
        })
    }

    return (
        <section className="panel">
            <h2>Project</h2>

            <div className="form-row compact">
                <select
                    value={selectedId}
                    onChange={(e) => setSelectedId(e.target.value)}
                    style={{ flexGrow: 1 }}
                >
                    <option value="">Select a project...</option>
                    {projects.map(p => (
                        <option key={p.id} value={p.id}>
                            {new Date(p.created_at).toLocaleString()} - {p.status}
                        </option>
                    ))}
                </select>
                <button onClick={handleOpen}>Open</button>
            </div>

            <hr className="divider" />

            <h3 className="section-subtitle">Create New</h3>

            <div className="form-row compact">
                <label>
                    Format
                    <select value={format} onChange={(e) => setFormat(e.target.value)}>
                        <option value="9:16">9:16 (Story)</option>
                        <option value="16:9">16:9 (Landscape)</option>
                    </select>
                </label>
                <label>
                    Style
                    <select value={style} onChange={(e) => setStyle(e.target.value)}>
                        <option value="cinematic">Cinematic</option>
                        <option value="anime">Anime</option>
                        <option value="illustration">Illustration</option>
                        <option value="abstract">Abstract</option>
                        <option value="cyberpunk">Cyberpunk</option>
                        <option value="watercolor">Watercolor</option>
                        <option value="horror">Horror / Dark</option>
                        <option value="minimalist">Minimalist</option>
                    </select>
                </label>
            </div>

            <div className="form-row compact">
                <label>
                    Render Speed
                    <select value={renderPreset} onChange={(e) => setRenderPreset(e.target.value)}>
                        <option value="fast">Fast (Balanced)</option>
                        <option value="veryfast">Very Fast</option>
                        <option value="ultrafast">Ultra Fast (Low Quality)</option>
                    </select>
                </label>
            </div>

            <div className="form-row compact">
                <label className="checkbox">
                    <input
                        type="checkbox"
                        checked={subtitles}
                        onChange={(e) => setSubtitles(e.target.checked)}
                    />
                    Subtitles
                </label>
            </div>

            <div className="form-row">
                <label style={{ display: 'block', marginBottom: '4px' }}>
                    Clip Idea / Narrative
                </label>
                <textarea
                    value={userDescription}
                    onChange={(e) => setUserDescription(e.target.value)}
                    rows={3}
                    placeholder="Describe what happens in the video (e.g. 'A robot exploring a ruined city', 'Abstract shapes dancing to the beat')..."
                    className="textarea"
                />
            </div>

            <div className="form-row">
                <label style={{ display: 'block', marginBottom: '4px' }}>
                    Character Description
                </label>
                <textarea
                    value={characterDescription}
                    onChange={(e) => setCharacterDescription(e.target.value)}
                    rows={2}
                    placeholder="Describe the main character (e.g. 'Young woman with blue hair', 'A cute robot'). Leaves consistent across scenes."
                    className="textarea"
                />
            </div>

            <button onClick={handleCreate} className="full-width">
                Create Project
            </button>

            {projectId && (
                <div className="muted">
                    Project: {projectId} (status: {project?.status})
                </div>
            )}
        </section>
    )
}

export default ProjectPanel
