/**
 * Authentication Store
 * Manages user authentication state with Supabase
 */
import { create } from 'zustand'
import { supabase, isSupabaseConfigured } from '../lib/supabase'
import * as api from '../api/index.js'

export const useAuthStore = create((set, get) => ({
    // State
    user: null,
    session: null,
    profile: null,
    isLoading: true,
    error: null,
    isInitialized: false,

    // Initialize auth state
    initialize: async () => {
        if (!isSupabaseConfigured()) {
            set({ isLoading: false, isInitialized: true })
            return
        }

        try {
            // Get initial session
            const { data: { session }, error } = await supabase.auth.getSession()

            if (error) throw error

            if (session) {
                set({
                    user: session.user,
                    session,
                    isLoading: false,
                    isInitialized: true
                })
                // Load user profile
                await get().loadProfile()
            } else {
                set({ isLoading: false, isInitialized: true })
            }

            // Listen for auth changes
            supabase.auth.onAuthStateChange(async (event, session) => {
                console.log('Auth state changed:', event)

                if (session) {
                    set({ user: session.user, session })
                    await get().loadProfile()
                } else {
                    set({
                        user: null,
                        session: null,
                        profile: null
                    })
                }
            })
        } catch (error) {
            console.error('Auth initialization error:', error)
            set({ error: error.message, isLoading: false, isInitialized: true })
        }
    },

    // Load user profile from database
    loadProfile: async () => {
        const { user } = get()
        if (!user || !isSupabaseConfigured()) return

        try {
            const accountStatus = await api.getAccountStatus()

            if (accountStatus && accountStatus.profile) {
                set({ profile: accountStatus.profile })
            }
        } catch (error) {
            console.error('Failed to load profile:', error)
        }
    },

    // Sign up with email
    signUp: async (email, password, metadata = {}) => {
        if (!isSupabaseConfigured()) {
            set({ error: 'Supabase is not configured' })
            return { error: 'Supabase is not configured' }
        }

        set({ isLoading: true, error: null })

        try {
            const { data, error } = await supabase.auth.signUp({
                email,
                password,
                options: {
                    data: metadata
                }
            })

            if (error) throw error

            set({ isLoading: false })
            return { data, error: null }
        } catch (error) {
            set({ error: error.message, isLoading: false })
            return { data: null, error: error.message }
        }
    },

    // Sign in with email
    signIn: async (email, password) => {
        if (!isSupabaseConfigured()) {
            set({ error: 'Supabase is not configured' })
            return { error: 'Supabase is not configured' }
        }

        set({ isLoading: true, error: null })

        try {
            const { data, error } = await supabase.auth.signInWithPassword({
                email,
                password
            })

            if (error) throw error

            set({
                user: data.user,
                session: data.session,
                isLoading: false
            })

            await get().loadProfile()
            return { data, error: null }
        } catch (error) {
            set({ error: error.message, isLoading: false })
            return { data: null, error: error.message }
        }
    },

    // Sign in with OAuth (Google, GitHub, etc.)
    signInWithOAuth: async (provider) => {
        if (!isSupabaseConfigured()) {
            return { error: 'Supabase is not configured' }
        }

        try {
            const { data, error } = await supabase.auth.signInWithOAuth({
                provider,
                options: {
                    redirectTo: `${window.location.origin}/cabinet`
                }
            })

            if (error) throw error
            return { data, error: null }
        } catch (error) {
            set({ error: error.message })
            return { data: null, error: error.message }
        }
    },

    // Sign out
    signOut: async () => {
        if (!isSupabaseConfigured()) return

        try {
            await supabase.auth.signOut()
            set({
                user: null,
                session: null,
                profile: null,
                error: null
            })
        } catch (error) {
            set({ error: error.message })
        }
    },

    // Reset password
    resetPassword: async (email) => {
        if (!isSupabaseConfigured()) {
            return { error: 'Supabase is not configured' }
        }

        try {
            const { error } = await supabase.auth.resetPasswordForEmail(email, {
                redirectTo: `${window.location.origin}/reset-password`
            })

            if (error) throw error
            return { error: null }
        } catch (error) {
            return { error: error.message }
        }
    },

    // Update password
    updatePassword: async (newPassword) => {
        if (!isSupabaseConfigured()) {
            return { error: 'Supabase is not configured' }
        }

        try {
            const { error } = await supabase.auth.updateUser({
                password: newPassword
            })

            if (error) throw error
            return { error: null }
        } catch (error) {
            return { error: error.message }
        }
    },

    // Update profile
    updateProfile: async (updates) => {
        const { user } = get()
        if (!user || !isSupabaseConfigured()) {
            return { error: 'Not authenticated' }
        }

        try {
            const data = await api.updateProfile(updates)

            set({ profile: data })
            return { data, error: null }
        } catch (error) {
            return { data: null, error: error.message }
        }
    },

    // Clear error
    clearError: () => set({ error: null })
}))
