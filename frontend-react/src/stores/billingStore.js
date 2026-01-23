/**
 * Billing Store
 * Manages credits, subscriptions, and transaction history
 */
import { create } from 'zustand'
import { isSupabaseConfigured } from '../lib/supabase'
import * as api from '../api/index.js'

// Subscription plans configuration
export const SUBSCRIPTION_PLANS = {
    free: {
        id: 'free',
        name: 'Free',
        price: 0,
        creditsPerMonth: 10,
        features: ['10 credits/month', 'Standard quality', 'Community support'],
        canGenerate: true
    },
    starter: {
        id: 'starter',
        name: 'Starter',
        price: 9.99,
        creditsPerMonth: 100,
        features: ['100 credits/month', 'HD quality', 'Email support', 'Priority queue'],
        canGenerate: true
    },
    pro: {
        id: 'pro',
        name: 'Pro',
        price: 29.99,
        creditsPerMonth: 500,
        features: ['500 credits/month', '4K quality', 'Priority support', 'API access', 'Custom styles'],
        canGenerate: true
    },
    enterprise: {
        id: 'enterprise',
        name: 'Enterprise',
        price: 99.99,
        creditsPerMonth: 2000,
        features: ['2000 credits/month', '4K+ quality', 'Dedicated support', 'White label', 'Custom integrations'],
        canGenerate: true
    }
}

// Transaction types
export const TRANSACTION_TYPES = {
    CREDIT_PURCHASE: 'credit_purchase',
    SUBSCRIPTION_CREDIT: 'subscription_credit',
    GENERATION_DEDUCT: 'generation_deduct',
    REFUND: 'refund',
    BONUS: 'bonus',
    ADJUSTMENT: 'adjustment'
}

export const useBillingStore = create((set, get) => ({
    // State
    credits: 0,
    subscription: null,
    transactions: [],
    isLoading: false,
    error: null,
    canGenerate: false,
    generationBlockReason: null,

    // Load billing data for current user
    loadBillingData: async (userId) => {
        if (!isSupabaseConfigured() || !userId) {
            set({ isLoading: false })
            return
        }

        set({ isLoading: true, error: null })

        try {
            const accountStatus = await api.getAccountStatus()

            if (accountStatus) {
                const credits = accountStatus.credits ?? 0
                const subscription = accountStatus.subscription || null

                set({
                    credits,
                    subscription: subscription ? {
                        plan_id: subscription.plan_id,
                        status: subscription.status,
                        current_period_end: subscription.renewal_date
                    } : null,
                    canGenerate: accountStatus.can_generate,
                    generationBlockReason: accountStatus.generation_block_reason,
                    isLoading: false
                })
            }
        } catch (error) {
            console.error('Failed to load billing data:', error)
            set({ error: error.message, isLoading: false })
        }
    },

    // Load transaction history
    loadTransactions: async (userId, limit = 50) => {
        if (!isSupabaseConfigured() || !userId) return

        try {
            const data = await api.getTransactions(limit)
            set({ transactions: data || [] })
        } catch (error) {
            console.error('Failed to load transactions:', error)
        }
    },

    // Get formatted subscription info
    getSubscriptionInfo: () => {
        const { subscription } = get()

        if (!subscription) {
            return {
                planName: 'No Plan',
                status: 'inactive',
                renewalDate: null,
                daysUntilRenewal: null
            }
        }

        const plan = SUBSCRIPTION_PLANS[subscription.plan_id] || SUBSCRIPTION_PLANS.free
        const renewalDate = new Date(subscription.current_period_end)
        const now = new Date()
        const daysUntilRenewal = Math.ceil((renewalDate - now) / (1000 * 60 * 60 * 24))

        return {
            planName: plan.name,
            planId: subscription.plan_id,
            status: subscription.status,
            renewalDate: renewalDate.toLocaleDateString(),
            daysUntilRenewal: Math.max(0, daysUntilRenewal),
            price: plan.price,
            features: plan.features,
            creditsPerMonth: plan.creditsPerMonth
        }
    },

    // Clear billing data (on logout)
    clearBillingData: () => {
        set({
            credits: 0,
            subscription: null,
            transactions: [],
            canGenerate: false,
            generationBlockReason: null,
            error: null
        })
    }
}))
