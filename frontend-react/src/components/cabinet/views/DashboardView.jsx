/**
 * Dashboard View
 * Overview of user's account status and quick actions
 */
import { useAuthStore } from '../../../stores/authStore'
import { useBillingStore } from '../../../stores/billingStore'

export default function DashboardView({ onNavigate }) {
    const { user, profile } = useAuthStore()
    const { credits, transactions, canGenerate, generationBlockReason, getSubscriptionInfo } = useBillingStore()

    const subscriptionInfo = getSubscriptionInfo()
    const recentTransactions = transactions.slice(0, 5)

    // Calculate stats
    const totalGenerated = transactions.filter(t => t.type === 'generation_deduct').length

    return (
        <div className="dashboard-view">
            <div className="view-header">
                <h1>Welcome back, {profile?.full_name || user?.email?.split('@')[0]}!</h1>
                <p className="view-subtitle">Here's an overview of your account</p>
            </div>

            {/* Generation Status Banner */}
            {!canGenerate && (
                <div className="status-banner warning">
                    <span className="banner-icon">⚠️</span>
                    <div className="banner-content">
                        <strong>Generation Unavailable</strong>
                        <p>{generationBlockReason}</p>
                    </div>
                    <button
                        className="btn-banner-action"
                        onClick={() => onNavigate(credits <= 0 ? 'credits' : 'subscription')}
                    >
                        {credits <= 0 ? 'Buy Credits' : 'Manage Subscription'}
                    </button>
                </div>
            )}

            {canGenerate && (
                <div className="status-banner success">
                    <span className="banner-icon">✅</span>
                    <div className="banner-content">
                        <strong>Ready to Generate</strong>
                        <p>You have {credits} credits available. Start creating!</p>
                    </div>
                    <a href="/" className="btn-banner-action primary">
                        Open Editor
                    </a>
                </div>
            )}

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-icon credits">💎</div>
                    <div className="stat-content">
                        <span className="stat-value">{credits}</span>
                        <span className="stat-label">Credits Available</span>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon subscription">⭐</div>
                    <div className="stat-content">
                        <span className="stat-value">{subscriptionInfo.planName}</span>
                        <span className="stat-label">Current Plan</span>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon projects">🎬</div>
                    <div className="stat-content">
                        <span className="stat-value">{totalGenerated}</span>
                        <span className="stat-label">Images Generated</span>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-icon renewal">📅</div>
                    <div className="stat-content">
                        <span className="stat-value">
                            {subscriptionInfo.daysUntilRenewal !== null
                                ? `${subscriptionInfo.daysUntilRenewal} days`
                                : 'N/A'}
                        </span>
                        <span className="stat-label">Until Renewal</span>
                    </div>
                </div>
            </div>

            {/* Quick Actions */}
            <section className="dashboard-section">
                <h2>Quick Actions</h2>
                <div className="quick-actions">
                    <button
                        className="action-card"
                        onClick={() => onNavigate('projects')}
                    >
                        <span className="action-icon">🎬</span>
                        <span className="action-label">View Projects</span>
                    </button>
                    <button
                        className="action-card"
                        onClick={() => onNavigate('credits')}
                    >
                        <span className="action-icon">💎</span>
                        <span className="action-label">Buy Credits</span>
                    </button>
                    <button
                        className="action-card"
                        onClick={() => onNavigate('subscription')}
                    >
                        <span className="action-icon">⭐</span>
                        <span className="action-label">Upgrade Plan</span>
                    </button>
                    <a href="/" className="action-card">
                        <span className="action-icon">🎥</span>
                        <span className="action-label">Create New</span>
                    </a>
                </div>
            </section>

            {/* Recent Activity */}
            <section className="dashboard-section">
                <div className="section-header">
                    <h2>Recent Activity</h2>
                    <button
                        className="btn-link"
                        onClick={() => onNavigate('credits')}
                    >
                        View All →
                    </button>
                </div>

                {recentTransactions.length > 0 ? (
                    <div className="activity-list">
                        {recentTransactions.map(tx => (
                            <div key={tx.id} className="activity-item">
                                <span className={`activity-icon ${tx.amount > 0 ? 'credit' : 'debit'}`}>
                                    {tx.amount > 0 ? '+' : '−'}
                                </span>
                                <div className="activity-content">
                                    <span className="activity-description">{tx.description}</span>
                                    <span className="activity-date">
                                        {new Date(tx.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <span className={`activity-amount ${tx.amount > 0 ? 'credit' : 'debit'}`}>
                                    {tx.amount > 0 ? '+' : ''}{tx.amount}
                                </span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="empty-state">
                        <span className="empty-icon">📭</span>
                        <p>No recent activity</p>
                    </div>
                )}
            </section>
        </div>
    )
}
