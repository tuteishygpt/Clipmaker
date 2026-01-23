/**
 * Credits View
 * Manage credits, view transaction history, and purchase more
 */
import { useState, useEffect } from 'react'
import { useAuthStore } from '../../../stores/authStore'
import { useBillingStore, TRANSACTION_TYPES } from '../../../stores/billingStore'

// Credit packages available for purchase
const CREDIT_PACKAGES = [
    { id: 'credits_10', credits: 10, price: 2.99, popular: false },
    { id: 'credits_50', credits: 50, price: 9.99, popular: true, savings: '33%' },
    { id: 'credits_100', credits: 100, price: 17.99, popular: false, savings: '40%' },
    { id: 'credits_500', credits: 500, price: 74.99, popular: false, savings: '50%' },
]

export default function CreditsView() {
    const { user } = useAuthStore()
    const { credits, transactions, loadTransactions, isLoading } = useBillingStore()
    const [activeTab, setActiveTab] = useState('balance') // balance | history | buy
    const [selectedPackage, setSelectedPackage] = useState(null)

    useEffect(() => {
        if (user?.id) {
            loadTransactions(user.id, 100)
        }
    }, [user?.id, loadTransactions])

    const getTransactionIcon = (type) => {
        switch (type) {
            case TRANSACTION_TYPES.CREDIT_PURCHASE:
                return '💰'
            case TRANSACTION_TYPES.SUBSCRIPTION_CREDIT:
                return '⭐'
            case TRANSACTION_TYPES.GENERATION_DEDUCT:
                return '🎨'
            case TRANSACTION_TYPES.REFUND:
                return '↩️'
            case TRANSACTION_TYPES.BONUS:
                return '🎁'
            default:
                return '💎'
        }
    }

    const formatTransactionType = (type) => {
        switch (type) {
            case TRANSACTION_TYPES.CREDIT_PURCHASE:
                return 'Purchase'
            case TRANSACTION_TYPES.SUBSCRIPTION_CREDIT:
                return 'Subscription'
            case TRANSACTION_TYPES.GENERATION_DEDUCT:
                return 'Generation'
            case TRANSACTION_TYPES.REFUND:
                return 'Refund'
            case TRANSACTION_TYPES.BONUS:
                return 'Bonus'
            default:
                return 'Adjustment'
        }
    }

    const handlePurchase = async (pkg) => {
        setSelectedPackage(pkg)
        // In a real implementation, this would integrate with a payment provider
        // like Stripe, Paddle, or LemonSqueezy
        alert(`Payment integration: Purchase ${pkg.credits} credits for $${pkg.price}`)
    }

    return (
        <div className="credits-view">
            <div className="view-header">
                <div>
                    <h1>Credits</h1>
                    <p className="view-subtitle">Manage your generation credits</p>
                </div>
            </div>

            {/* Credits Overview Card */}
            <div className="credits-overview-card">
                <div className="overview-content">
                    <div className="credits-display">
                        <span className="credits-icon-large">💎</span>
                        <div className="credits-numbers">
                            <span className="credits-balance">{credits}</span>
                            <span className="credits-label">Credits Available</span>
                        </div>
                    </div>
                    <div className="credits-info">
                        <p>Each image generation uses <strong>1 credit</strong></p>
                        <p className="credits-tip">💡 Tip: Subscribe to get monthly credits at a discounted rate</p>
                    </div>
                </div>
                <button
                    className="btn-primary large"
                    onClick={() => setActiveTab('buy')}
                >
                    + Buy More Credits
                </button>
            </div>

            {/* Tab Navigation */}
            <div className="credits-tabs">
                <button
                    className={`tab-btn ${activeTab === 'balance' ? 'active' : ''}`}
                    onClick={() => setActiveTab('balance')}
                >
                    📊 Overview
                </button>
                <button
                    className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
                    onClick={() => setActiveTab('history')}
                >
                    📜 Transaction History
                </button>
                <button
                    className={`tab-btn ${activeTab === 'buy' ? 'active' : ''}`}
                    onClick={() => setActiveTab('buy')}
                >
                    💳 Buy Credits
                </button>
            </div>

            {/* Tab Content */}
            <div className="credits-content">
                {activeTab === 'balance' && (
                    <div className="balance-tab">
                        <div className="usage-stats">
                            <h3>Usage Statistics</h3>
                            <div className="stats-row">
                                <div className="usage-stat">
                                    <span className="stat-icon">🎨</span>
                                    <div className="stat-info">
                                        <span className="stat-number">
                                            {transactions.filter(t => t.type === TRANSACTION_TYPES.GENERATION_DEDUCT).length}
                                        </span>
                                        <span className="stat-desc">Total Generations</span>
                                    </div>
                                </div>
                                <div className="usage-stat">
                                    <span className="stat-icon">📅</span>
                                    <div className="stat-info">
                                        <span className="stat-number">
                                            {transactions.filter(t => {
                                                const date = new Date(t.created_at)
                                                const now = new Date()
                                                return date.getMonth() === now.getMonth() &&
                                                    date.getFullYear() === now.getFullYear() &&
                                                    t.type === TRANSACTION_TYPES.GENERATION_DEDUCT
                                            }).length}
                                        </span>
                                        <span className="stat-desc">This Month</span>
                                    </div>
                                </div>
                                <div className="usage-stat">
                                    <span className="stat-icon">💰</span>
                                    <div className="stat-info">
                                        <span className="stat-number">
                                            {transactions
                                                .filter(t => t.type === TRANSACTION_TYPES.CREDIT_PURCHASE)
                                                .reduce((sum, t) => sum + t.amount, 0)}
                                        </span>
                                        <span className="stat-desc">Credits Purchased</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div className="recent-activity">
                            <h3>Recent Activity</h3>
                            {transactions.slice(0, 10).map(tx => (
                                <div key={tx.id} className="activity-row">
                                    <span className="activity-icon">{getTransactionIcon(tx.type)}</span>
                                    <div className="activity-info">
                                        <span className="activity-desc">{tx.description}</span>
                                        <span className="activity-time">
                                            {new Date(tx.created_at).toLocaleString()}
                                        </span>
                                    </div>
                                    <span className={`activity-amount ${tx.amount > 0 ? 'positive' : 'negative'}`}>
                                        {tx.amount > 0 ? '+' : ''}{tx.amount}
                                    </span>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {activeTab === 'history' && (
                    <div className="history-tab">
                        <div className="transactions-table">
                            <div className="table-header">
                                <span className="col-date">Date</span>
                                <span className="col-type">Type</span>
                                <span className="col-description">Description</span>
                                <span className="col-amount">Amount</span>
                                <span className="col-balance">Balance</span>
                            </div>
                            <div className="table-body">
                                {transactions.length > 0 ? (
                                    transactions.map(tx => (
                                        <div key={tx.id} className="table-row">
                                            <span className="col-date">
                                                {new Date(tx.created_at).toLocaleDateString()}
                                            </span>
                                            <span className="col-type">
                                                <span className="type-badge">
                                                    {getTransactionIcon(tx.type)} {formatTransactionType(tx.type)}
                                                </span>
                                            </span>
                                            <span className="col-description">{tx.description}</span>
                                            <span className={`col-amount ${tx.amount > 0 ? 'positive' : 'negative'}`}>
                                                {tx.amount > 0 ? '+' : ''}{tx.amount}
                                            </span>
                                            <span className="col-balance">{tx.balance_after}</span>
                                        </div>
                                    ))
                                ) : (
                                    <div className="empty-state">
                                        <span className="empty-icon">📭</span>
                                        <p>No transactions yet</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {activeTab === 'buy' && (
                    <div className="buy-tab">
                        <h3>Choose a Credit Package</h3>
                        <p className="buy-subtitle">Get more credits to continue generating amazing content</p>

                        <div className="packages-grid">
                            {CREDIT_PACKAGES.map(pkg => (
                                <div
                                    key={pkg.id}
                                    className={`package-card ${pkg.popular ? 'popular' : ''} ${selectedPackage?.id === pkg.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedPackage(pkg)}
                                >
                                    {pkg.popular && <span className="popular-badge">Most Popular</span>}
                                    {pkg.savings && <span className="savings-badge">Save {pkg.savings}</span>}

                                    <div className="package-credits">
                                        <span className="package-icon">💎</span>
                                        <span className="package-amount">{pkg.credits}</span>
                                        <span className="package-label">credits</span>
                                    </div>

                                    <div className="package-price">
                                        <span className="price-currency">$</span>
                                        <span className="price-amount">{pkg.price}</span>
                                    </div>

                                    <div className="package-rate">
                                        ${(pkg.price / pkg.credits).toFixed(2)} per credit
                                    </div>

                                    <button
                                        className={`btn-package ${pkg.popular ? 'primary' : 'secondary'}`}
                                        onClick={() => handlePurchase(pkg)}
                                    >
                                        Buy Now
                                    </button>
                                </div>
                            ))}
                        </div>

                        <div className="payment-info">
                            <p>🔒 Secure payment powered by Stripe</p>
                            <p>Credits are added instantly after payment</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
