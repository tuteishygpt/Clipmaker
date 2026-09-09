import { useProjectStore } from '../stores/projectStore'
import { useTranslation } from '../i18n'
import SceneCard from './SceneCard'

function Scenes() {
    const { segments, projectId } = useProjectStore()
    const { t } = useTranslation()

    if (!segments || !Array.isArray(segments) || segments.length === 0) {
        return (
            <div className="scenes">
                <p className="muted">{t('studio.scenes.notReady')}</p>
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
