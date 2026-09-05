/**
 * Profile View
 * Manage user profile information and settings
 */
import { useState } from 'react'
import { useAuthStore } from '../../../stores/authStore'
import { useTranslation } from '../../../i18n'

export default function ProfileView() {
    const { user, profile, updateProfile, updatePassword } = useAuthStore()
    const { t, currentLang, setLanguage, availableLanguages } = useTranslation()

    const [isEditing, setIsEditing] = useState(false)
    const [isSaving, setIsSaving] = useState(false)
    const [message, setMessage] = useState({ type: null, text: '' })

    const [formData, setFormData] = useState({
        full_name: profile?.full_name || '',
        company: profile?.company || '',
        website: profile?.website || '',
        bio: profile?.bio || ''
    })

    const [passwordData, setPasswordData] = useState({
        newPassword: '',
        confirmPassword: ''
    })
    const [showPasswordForm, setShowPasswordForm] = useState(false)

    const handleInputChange = (e) => {
        const { name, value } = e.target
        setFormData(prev => ({ ...prev, [name]: value }))
    }

    const handleSaveProfile = async (e) => {
        e.preventDefault()
        setIsSaving(true)
        setMessage({ type: null, text: '' })

        try {
            const { error } = await updateProfile(formData)

            if (error) {
                setMessage({ type: 'error', text: error })
            } else {
                setMessage({ type: 'success', text: t('profile.profileUpdated') })
                setIsEditing(false)
            }
        } finally {
            setIsSaving(false)
        }
    }

    const handlePasswordChange = async (e) => {
        e.preventDefault()

        if (passwordData.newPassword !== passwordData.confirmPassword) {
            setMessage({ type: 'error', text: t('profile.passwordsDoNotMatch') })
            return
        }

        if (passwordData.newPassword.length < 8) {
            setMessage({ type: 'error', text: t('profile.passwordTooShort') })
            return
        }

        setIsSaving(true)
        setMessage({ type: null, text: '' })

        try {
            const { error } = await updatePassword(passwordData.newPassword)

            if (error) {
                setMessage({ type: 'error', text: error })
            } else {
                setMessage({ type: 'success', text: t('profile.passwordUpdated') })
                setPasswordData({ newPassword: '', confirmPassword: '' })
                setShowPasswordForm(false)
            }
        } finally {
            setIsSaving(false)
        }
    }

    return (
        <div className="profile-view">
            <div className="view-header">
                <div>
                    <h1>{t('profile.title')}</h1>
                    <p className="view-subtitle">{t('profile.subtitle')}</p>
                </div>
            </div>

            {message.text && (
                <div className={`alert ${message.type}`}>
                    <span className="alert-icon">
                        {message.type === 'success' ? '✓' : '⚠'}
                    </span>
                    {message.text}
                </div>
            )}

            {/* Profile Card */}
            <div className="profile-card">
                <div className="profile-header">
                    <div className="profile-avatar-large">
                        {profile?.avatar_url ? (
                            <img src={profile.avatar_url} alt={t('profile.avatarAlt')} />
                        ) : (
                            <span>{user?.email?.charAt(0).toUpperCase() || '?'}</span>
                        )}
                    </div>
                    <div className="profile-info">
                        <h2>{profile?.full_name || user?.email?.split('@')[0]}</h2>
                        <p className="profile-email">{user?.email}</p>
                        <p className="profile-joined">
                            {t('profile.memberSince', { date: new Date(user?.created_at || Date.now()).toLocaleDateString() })}
                        </p>
                    </div>
                    {!isEditing && (
                        <button
                            className="btn-edit"
                            onClick={() => setIsEditing(true)}
                        >
                            {t('profile.editProfile')}
                        </button>
                    )}
                </div>

                {isEditing ? (
                    <form onSubmit={handleSaveProfile} className="profile-form">
                        <div className="form-row">
                            <div className="form-field">
                                <label htmlFor="full_name">{t('profile.fullName')}</label>
                                <input
                                    id="full_name"
                                    name="full_name"
                                    type="text"
                                    value={formData.full_name}
                                    onChange={handleInputChange}
                                    placeholder={t('profile.fullNamePlaceholder')}
                                />
                            </div>
                            <div className="form-field">
                                <label htmlFor="company">{t('profile.company')}</label>
                                <input
                                    id="company"
                                    name="company"
                                    type="text"
                                    value={formData.company}
                                    onChange={handleInputChange}
                                    placeholder={t('profile.companyPlaceholder')}
                                />
                            </div>
                        </div>

                        <div className="form-field">
                            <label htmlFor="website">{t('profile.website')}</label>
                            <input
                                id="website"
                                name="website"
                                type="url"
                                value={formData.website}
                                onChange={handleInputChange}
                                placeholder={t('profile.websitePlaceholder')}
                            />
                        </div>

                        <div className="form-field">
                            <label htmlFor="bio">{t('profile.bio')}</label>
                            <textarea
                                id="bio"
                                name="bio"
                                value={formData.bio}
                                onChange={handleInputChange}
                                placeholder={t('profile.bioPlaceholder')}
                                rows={4}
                            />
                        </div>

                        <div className="form-actions">
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setIsEditing(false)}
                            >
                                {t('profile.cancel')}
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={isSaving}
                            >
                                {isSaving ? t('profile.saving') : t('profile.saveChanges')}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="profile-details">
                        <div className="detail-row">
                            <span className="detail-label">{t('profile.email')}</span>
                            <span className="detail-value">{user?.email}</span>
                        </div>
                        {profile?.company && (
                            <div className="detail-row">
                                <span className="detail-label">{t('profile.company')}</span>
                                <span className="detail-value">{profile.company}</span>
                            </div>
                        )}
                        {profile?.website && (
                            <div className="detail-row">
                                <span className="detail-label">{t('profile.website')}</span>
                                <a href={profile.website} target="_blank" rel="noopener noreferrer" className="detail-value link">
                                    {profile.website}
                                </a>
                            </div>
                        )}
                        {profile?.bio && (
                            <div className="detail-row">
                                <span className="detail-label">{t('profile.bio')}</span>
                                <span className="detail-value">{profile.bio}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Preferences / Interface Language */}
            <div className="settings-section">
                <h3>🌐 {t('profile.preferencesTitle')}</h3>
                <div className="language-preferences-card">
                    <div className="language-preferences-header">
                        <div>
                            <span className="language-pref-label">{t('profile.languageLabel')}</span>
                            <p className="language-pref-desc">{t('profile.languageDesc')}</p>
                        </div>
                    </div>
                    
                    <div className="languages-grid">
                        {availableLanguages.map((lang) => {
                            const isActive = currentLang === lang.code
                            return (
                                <button
                                    key={lang.code}
                                    type="button"
                                    className={`language-option-card ${isActive ? 'active' : ''}`}
                                    aria-pressed={isActive}
                                    onClick={() => {
                                        setLanguage(lang.code)
                                        setMessage({ type: 'success', text: t('profile.languageUpdated') })
                                    }}
                                >
                                    <span className="language-flag">{lang.flag}</span>
                                    <div className="language-meta">
                                        <span className="language-native-name">{lang.native}</span>
                                        <span className="language-english-name">{lang.label}</span>
                                    </div>
                                    {isActive && (
                                        <span className="language-active-badge">
                                            ✓ {t('profile.languageActiveBadge')}
                                        </span>
                                    )}
                                </button>
                            )
                        })}
                    </div>
                </div>
            </div>

            {/* Security Section */}
            <div className="settings-section">
                <h3>{t('profile.security')}</h3>

                {showPasswordForm ? (
                    <form onSubmit={handlePasswordChange} className="password-form">
                        <div className="form-field">
                            <label htmlFor="newPassword">{t('profile.newPassword')}</label>
                            <input
                                id="newPassword"
                                type="password"
                                value={passwordData.newPassword}
                                onChange={(e) => setPasswordData(prev => ({
                                    ...prev,
                                    newPassword: e.target.value
                                }))}
                                placeholder={t('profile.enterNewPassword')}
                                minLength={8}
                                required
                            />
                        </div>
                        <div className="form-field">
                            <label htmlFor="confirmPassword">{t('profile.confirmPassword')}</label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={passwordData.confirmPassword}
                                onChange={(e) => setPasswordData(prev => ({
                                    ...prev,
                                    confirmPassword: e.target.value
                                }))}
                                placeholder={t('profile.confirmNewPassword')}
                                required
                            />
                        </div>
                        <div className="form-actions">
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => {
                                    setShowPasswordForm(false)
                                    setPasswordData({ newPassword: '', confirmPassword: '' })
                                }}
                            >
                                {t('profile.cancel')}
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={isSaving}
                            >
                                {isSaving ? t('profile.updating') : t('profile.updatePassword')}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="security-options">
                        <button
                            className="btn-security"
                            onClick={() => setShowPasswordForm(true)}
                        >
                            <span className="security-icon">🔒</span>
                            <div className="security-info">
                                <span className="security-label">{t('profile.changePassword')}</span>
                                <span className="security-desc">{t('profile.changePasswordDesc')}</span>
                            </div>
                            <span className="security-arrow">→</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Account Actions */}
            <div className="settings-section danger-zone">
                <h3>{t('profile.dangerZone')}</h3>
                <div className="danger-actions">
                    <div className="danger-item">
                        <div className="danger-info">
                            <span className="danger-label">{t('profile.deleteAccount')}</span>
                            <span className="danger-desc">
                                {t('profile.deleteAccountDesc')}
                            </span>
                        </div>
                        <button className="btn-danger">{t('profile.deleteAccount')}</button>
                    </div>
                </div>
            </div>
        </div>
    )
}
