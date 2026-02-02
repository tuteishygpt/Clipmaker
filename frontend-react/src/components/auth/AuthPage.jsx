/**
 * Authentication Page Component
 * Handles Sign In, Sign Up, and Password Reset
 */
import { useState } from 'react'
import { useAuthStore } from '../../stores/authStore'
import { isSupabaseConfigured } from '../../lib/supabase'
import '../cabinet/CabinetStyles.css'

export default function AuthPage({ onSuccess }) {
    const [mode, setMode] = useState('signin') // 'signin' | 'signup' | 'reset'
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [confirmPassword, setConfirmPassword] = useState('')
    const [fullName, setFullName] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [message, setMessage] = useState({ type: null, text: '' })

    const { signIn, signUp, signInWithOAuth, resetPassword, error, clearError } = useAuthStore()

    const handleSubmit = async (e) => {
        e.preventDefault()
        setMessage({ type: null, text: '' })
        clearError()

        if (!isSupabaseConfigured()) {
            setMessage({
                type: 'error',
                text: 'Authentication is not configured. Please set up Supabase credentials.'
            })
            return
        }

        setIsSubmitting(true)

        try {
            if (mode === 'signin') {
                const { error } = await signIn(email, password)
                if (error) {
                    setMessage({ type: 'error', text: error })
                } else {
                    onSuccess?.()
                }
            } else if (mode === 'signup') {
                if (password !== confirmPassword) {
                    setMessage({ type: 'error', text: 'Passwords do not match' })
                    setIsSubmitting(false)
                    return
                }
                if (password.length < 8) {
                    setMessage({ type: 'error', text: 'Password must be at least 8 characters' })
                    setIsSubmitting(false)
                    return
                }

                const { error } = await signUp(email, password, { full_name: fullName })
                if (error) {
                    setMessage({ type: 'error', text: error })
                } else {
                    setMessage({
                        type: 'success',
                        text: 'Account created! Please check your email to verify your account.'
                    })
                }
            } else if (mode === 'reset') {
                const { error } = await resetPassword(email)
                if (error) {
                    setMessage({ type: 'error', text: error })
                } else {
                    setMessage({
                        type: 'success',
                        text: 'Password reset link sent! Check your email.'
                    })
                }
            }
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleOAuth = async (provider) => {
        clearError()
        await signInWithOAuth(provider)
    }

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-header">
                    <div className="auth-logo">
                        <span className="logo-icon">🎬</span>
                        <h1>Studio</h1>
                    </div>
                    <p className="auth-subtitle">
                        {mode === 'signin' && 'Welcome back! Sign in to continue.'}
                        {mode === 'signup' && 'Create your account to get started.'}
                        {mode === 'reset' && 'Enter your email to reset your password.'}
                    </p>
                </div>

                {message.text && (
                    <div className={`auth-message ${message.type}`}>
                        <span className="message-icon">
                            {message.type === 'success' ? '✓' : '⚠'}
                        </span>
                        {message.text}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form">
                    {mode === 'signup' && (
                        <div className="form-field">
                            <label htmlFor="fullName">Full Name</label>
                            <input
                                id="fullName"
                                type="text"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                placeholder="Enter your full name"
                                required
                            />
                        </div>
                    )}

                    <div className="form-field">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="your@email.com"
                            required
                        />
                    </div>

                    {mode !== 'reset' && (
                        <div className="form-field">
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter your password"
                                required
                                minLength={8}
                            />
                        </div>
                    )}

                    {mode === 'signup' && (
                        <div className="form-field">
                            <label htmlFor="confirmPassword">Confirm Password</label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="Confirm your password"
                                required
                            />
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn-auth-primary"
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? (
                            <>
                                <span className="spinner"></span>
                                Processing...
                            </>
                        ) : (
                            <>
                                {mode === 'signin' && 'Sign In'}
                                {mode === 'signup' && 'Create Account'}
                                {mode === 'reset' && 'Send Reset Link'}
                            </>
                        )}
                    </button>
                </form>

                {mode === 'signin' && (
                    <button
                        className="btn-forgot"
                        onClick={() => setMode('reset')}
                    >
                        Forgot your password?
                    </button>
                )}

                {mode !== 'reset' && (
                    <>
                        <div className="auth-divider">
                            <span>or continue with</span>
                        </div>

                        <div className="oauth-buttons">
                            <button
                                className="btn-oauth"
                                onClick={() => handleOAuth('google')}
                                type="button"
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20">
                                    <path fill="#4285f4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                                    <path fill="#34a853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                                    <path fill="#fbbc05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                                    <path fill="#ea4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                                </svg>
                                Google
                            </button>
                            <button
                                className="btn-oauth"
                                onClick={() => handleOAuth('github')}
                                type="button"
                            >
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                                </svg>
                                GitHub
                            </button>
                        </div>
                    </>
                )}

                <div className="auth-footer">
                    {mode === 'signin' && (
                        <p>
                            Don't have an account?{' '}
                            <button onClick={() => setMode('signup')}>Sign up</button>
                        </p>
                    )}
                    {mode === 'signup' && (
                        <p>
                            Already have an account?{' '}
                            <button onClick={() => setMode('signin')}>Sign in</button>
                        </p>
                    )}
                    {mode === 'reset' && (
                        <p>
                            Remember your password?{' '}
                            <button onClick={() => setMode('signin')}>Sign in</button>
                        </p>
                    )}
                </div>
            </div>
        </div>
    )
}
