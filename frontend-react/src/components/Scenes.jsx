import { useProjectStore } from '../stores/projectStore'
import SceneCard from './SceneCard'

function Scenes() {
    const { segments } = useProjectStore()

    if (segments.length === 0) {
        return (
            <div className="scenes">
                <p className="muted">Scenes not ready yet.</p>
            </div>
        )
    }

    return (
        <div className="scenes">
            {segments.map((segment) => (
                <SceneCard key={segment.id} segment={segment} />
            ))}
        </div>
    )
}

export default Scenes
