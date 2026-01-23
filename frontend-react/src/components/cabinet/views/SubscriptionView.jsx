/**
 * Subscription View
 * Manage subscription plan, view benefits, and upgrade/downgrade
 */
import { useState } from 'react'
import { useAuthStore } from '../../../stores/authStore'
import { useBillingStore, SUBSCRIPTION_PLANS } from '../../../stores/billingStore'

export default function SubscriptionView() {
    const { user } = useAuthStore()
    const { subscription, getSubscriptionInfo, canGenerate, generationBlockReason } = useBillingStore()
    const [selectedPlan, setSelectedPlan] = useState(null)
    const [billingCycle, setBillingCycle] = useState('monthly') // monthly | yearly

    const subscriptionInfo = getSubscriptionInfo()
    const currentPlanId = subscription?.plan_id || 'free'

    const handleSubscribe = async (planId) => {
        // In a real implementation, this would integrate with a payment provider
        alert(`Subscription integration: Subscribe to ${SUBSCRIPTION_PLANS[planId].name} plan`)
    }

    const handleCancelSubscription = async () => {
        if (!confirm('Are you sure you want to cancel your subscription?')) return
        alert('Subscription cancellation would be processed here')
    }

    const getYearlyPrice = (monthlyPrice) => {
        return (monthlyPrice * 12 * 0.8).toFixed(2) // 20% discount for yearly
    }

    return (
        <div className="subscription-view">
            <div className="view-header">
                <div>
                    <h1>Subscription</h1>
                    <p className="view-subtitle">Manage your subscription plan</p>
                </div>
            </div>

            {/* Current Plan Card */}
            <div className="current-plan-card">
                <div className="plan-badge">
                    <span className="plan-icon">⭐</span>
                    <span className="plan-name">{subscriptionInfo.planName}</span>
                </div>

                <div className="plan-details">
                    <div className="plan-detail">
                        <span className="detail-label">Status</span>
                        <span className={`detail-value status-${subscriptionInfo.status}`}>
                            {subscriptionInfo.status === 'active' ? '✓ Active' : 'Inactive'}
                        </span>
                    </div>
                    {subscriptionInfo.renewalDate && (
                        <div className="plan-detail">
                            <span className="detail-label">Next Renewal</span>
                            <span className="detail-value">{subscriptionInfo.renewalDate}</span>
                        </div>
                    )}
                    <div className="plan-detail">
                        <span className="detail-label">Monthly Credits</span>
                        <span className="detail-value">{subscriptionInfo.creditsPerMonth}</span>
                    </div>
                </div>

                {!canGenerate && generationBlockReason && (
                    <div className="plan-warning">
                        <span className="warning-icon">⚠️</span>
                        <span>{generationBlockReason}</span>
                    </div>
                )}

                {subscription && subscription.status === 'active' && (
                    <button
                        className="btn-cancel"
                        onClick={handleCancelSubscription}
                    >
                        Cancel Subscription
                    </button>
                )}
            </div>

            {/* Billing Cycle Toggle */}
            <div className="billing-toggle">
                <button
                    className={`toggle-btn ${billingCycle === 'monthly' ? 'active' : ''}`}
                    onClick={() => setBillingCycle('monthly')}
                >
                    Monthly
                </button>
                <button
                    className={`toggle-btn ${billingCycle === 'yearly' ? 'active' : ''}`}
                    onClick={() => setBillingCycle('yearly')}
                >
                    Yearly <span className="discount-badge">Save 20%</span>
                </button>
            </div>

            {/* Plans Grid */}
            <div className="plans-grid">
                {Object.values(SUBSCRIPTION_PLANS).map(plan => {
                    const isCurrentPlan = plan.id === currentPlanId
                    const price = billingCycle === 'yearly'
                        ? getYearlyPrice(plan.price)
                        : plan.price

                    return (
                        <div
                            key={plan.id}
                            className={`plan-card ${isCurrentPlan ? 'current' : ''} ${plan.id === 'pro' ? 'recommended' : ''}`}
                        >
                            {plan.id === 'pro' && (
                                <span className="recommended-badge">Recommended</span>
                            )}
                            {isCurrentPlan && (
                                <span className="current-badge">Current Plan</span>
                            )}

                            <div className="plan-header">
                                <h3 className="plan-title">{plan.name}</h3>
                                <div className="plan-price">
                                    {plan.price > 0 ? (
                                        <>
                                            <span className="price-currency">$</span>
                                            <span className="price-amount">{price}</span>
                                            <span className="price-period">
                                                /{billingCycle === 'yearly' ? 'year' : 'month'}
                                            </span>
                                        </>
                                    ) : (
                                        <span className="price-free">Free</span>
                                    )}
                                </div>
                            </div>

                            <div className="plan-credits">
                                <span className="credits-icon">💎</span>
                                <span className="credits-amount">{plan.creditsPerMonth}</span>
                                <span className="credits-period">credits/month</span>
                            </div>

                            <ul className="plan-features">
                                {plan.features.map((feature, idx) => (
                                    <li key={idx}>
                                        <span className="feature-check">✓</span>
                                        {feature}
                                    </li>
                                ))}
                            </ul>

                            <button
                                className={`btn-plan ${isCurrentPlan ? 'current' : plan.id === 'pro' ? 'primary' : 'secondary'}`}
                                onClick={() => !isCurrentPlan && handleSubscribe(plan.id)}
                                disabled={isCurrentPlan}
                            >
                                {isCurrentPlan ? 'Current Plan' : plan.price === 0 ? 'Get Started' : 'Subscribe'}
                            </button>
                        </div>
                    )
                })}
            </div>

            {/* FAQ Section */}
            <div className="subscription-faq">
                <h3>Frequently Asked Questions</h3>
                <div className="faq-list">
                    <div className="faq-item">
                        <h4>What happens when I run out of credits?</h4>
                        <p>You won't be able to generate new content until you either purchase more credits or wait for your monthly subscription credits to renew.</p>
                    </div>
                    <div className="faq-item">
                        <h4>Do unused credits roll over?</h4>
                        <p>Subscription credits expire at the end of each billing period. Purchased credits never expire.</p>
                    </div>
                    <div className="faq-item">
                        <h4>Can I cancel anytime?</h4>
                        <p>Yes! You can cancel your subscription at any time. Your access continues until the end of your current billing period.</p>
                    </div>
                    <div className="faq-item">
                        <h4>How do I upgrade or downgrade?</h4>
                        <p>Simply select a new plan and your subscription will be updated. Upgrades take effect immediately, downgrades take effect at the next billing cycle.</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
