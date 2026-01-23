/**
 * User Cabinet Layout
 * Main container for the user dashboard with navigation
 */
import { useState, useEffect } from 'react'
import { useAuthStore } from '../../stores/authStore'
import { useBillingStore } from '../../stores/billingStore'
import CabinetSidebar from './CabinetSidebar'
import DashboardView from './views/DashboardView'
import ProjectsView from './views/ProjectsView'
import CreditsView from './views/CreditsView'
import SubscriptionView from './views/SubscriptionView'
import ProfileView from './views/ProfileView'
import './CabinetStyles.css'

export default function CabinetLayout() {
    const [activeView, setActiveView] = useState('dashboard')
    const { user, profile, signOut, loadProfile } = useAuthStore()
    const { credits, subscription, loadBillingData, loadTransactions } = useBillingStore()

    // Load user data on mount
    useEffect(() => {
        if (user?.id) {
            loadProfile()
            loadBillingData(user.id)
            loadTransactions(user.id)
        }
    }, [user?.id, loadProfile, loadBillingData, loadTransactions])

    const handleSignOut = async () => {
        await signOut()
    }

    const renderView = () => {
        switch (activeView) {
            case 'dashboard':
                return <DashboardView onNavigate={setActiveView} />
            case 'projects':
                return <ProjectsView />
            case 'credits':
                return <CreditsView />
            case 'subscription':
                return <SubscriptionView />
            case 'profile':
                return <ProfileView />
            default:
                return <DashboardView onNavigate={setActiveView} />
        }
    }

    return (
        <div className="cabinet-layout">
            <CabinetSidebar
                activeView={activeView}
                onNavigate={setActiveView}
                user={user}
                profile={profile}
                credits={credits}
                subscription={subscription}
                onSignOut={handleSignOut}
            />

            <main className="cabinet-main">
                <div className="cabinet-content">
                    {renderView()}
                </div>
            </main>
        </div>
    )
}
