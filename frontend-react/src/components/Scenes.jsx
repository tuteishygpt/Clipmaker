import { useProjectStore } from '../stores/projectStore'
import SceneCard from './SceneCard'

function Scenes() {
    const { segments, projectId } = useProjectStore()

    if (!segments || !Array.isArray(segments) || segments.length === 0) {
        return (
            <div className="scenes">
                <p className="muted">Scenes not ready yet.</p>
            </div>
        )
    }

    // Filter out invalid segments to prevent crashes
    const validSegments = segments.filter(s => s && s.id);

    return (
        <div className="scenes">
            {validSegments.map((segment) => (
                <SceneCard key={`${projectId}-${segment.id}`} segment={segment} />
            ))}
        </div>
    )
}

export default Scenes
