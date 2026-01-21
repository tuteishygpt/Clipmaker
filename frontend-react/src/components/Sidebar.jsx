import ProjectPanel from './panels/ProjectPanel'
import AudioPanel from './panels/AudioPanel'
import ActionsPanel from './panels/ActionsPanel'

function Sidebar() {
    return (
        <div className="sidebar">
            <ProjectPanel />
            <AudioPanel />
            <ActionsPanel />
        </div>
    )
}

export default Sidebar
