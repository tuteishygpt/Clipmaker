/**
 * Cabinet Sidebar Navigation
 */
import { useBillingStore, SUBSCRIPTION_PLANS } from '../../stores/billingStore'

export default function CabinetSidebar({
    activeView,
    onNavigate,
    user,
    profile,
    credits,
    subscription,
    onSignOut
}) {
    const { getSubscriptionInfo } = useBillingStore()
    const subscriptionInfo = getSubscriptionInfo()

    const navItems = [
        { id: 'dashboard', icon: '📊', label: 'Dashboard' },
        { id: 'projects', icon: '🎬', label: 'Projects' },
        { id: 'credits', icon: '💎', label: 'Credits' },
        { id: 'subscription', icon: '⭐', label: 'Subscription' },
        { id: 'profile', icon: '👤', label: 'Profile' },
    ]

    return (
        <aside className="cabinet-sidebar">
            {/* Logo */}
            <div className="cabinet-logo">
                <span className="logo-icon">🎬</span>
                <span className="logo-text">Clipmaker</span>
            </div>

            {/* User Card */}
            <div className="user-card">
                <div className="user-avatar">
                    {profile?.avatar_url ? (
                        <img src={profile.avatar_url} alt="Avatar" />
                    ) : (
                        <span>{user?.email?.charAt(0).toUpperCase() || '?'}</span>
                    )}
                </div>
                <div className="user-info">
                    <span className="user-name">
                        {profile?.full_name || user?.email?.split('@')[0] || 'User'}
                    </span>
                    <span className="user-plan">
                        {subscriptionInfo.planName} Plan
                    </span>
                </div>
            </div>

            {/* Credits Display */}
            <div className="credits-card">
                <div className="credits-header">
                    <span className="credits-icon">💎</span>
                    <span className="credits-label">Credits</span>
                </div>
                <div className="credits-amount">
                    <span className="amount-value">{credits}</span>
                    <span className="amount-label">available</span>
                </div>
                <button
                    className="btn-add-credits"
                    onClick={() => onNavigate('credits')}
                >
                    + Add Credits
                </button>
            </div>

            {/* Navigation */}
            <nav className="cabinet-nav">
                {navItems.map(item => (
                    <button
                        key={item.id}
                        className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                        onClick={() => onNavigate(item.id)}
                    >
                        <span className="nav-icon">{item.icon}</span>
                        <span className="nav-label">{item.label}</span>
                    </button>
                ))}
            </nav>

            {/* Quick Actions */}
            <div className="sidebar-actions">
                <a href="/" className="btn-back-to-app">
                    <span className="nav-icon">🎥</span>
                    <span>Open Editor</span>
                </a>
            </div>

            {/* Sign Out */}
            <div className="sidebar-footer">
                <button className="btn-signout" onClick={onSignOut}>
                    <span className="nav-icon">🚪</span>
                    <span>Sign Out</span>
                </button>
            </div>
        </aside>
    )
}
