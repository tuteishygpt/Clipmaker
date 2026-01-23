/**
 * Profile View
 * Manage user profile information and settings
 */
import { useState } from 'react'
import { useAuthStore } from '../../../stores/authStore'

export default function ProfileView() {
    const { user, profile, updateProfile, updatePassword } = useAuthStore()

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
                setMessage({ type: 'success', text: 'Profile updated successfully!' })
                setIsEditing(false)
            }
        } finally {
            setIsSaving(false)
        }
    }

    const handlePasswordChange = async (e) => {
        e.preventDefault()

        if (passwordData.newPassword !== passwordData.confirmPassword) {
            setMessage({ type: 'error', text: 'Passwords do not match' })
            return
        }

        if (passwordData.newPassword.length < 8) {
            setMessage({ type: 'error', text: 'Password must be at least 8 characters' })
            return
        }

        setIsSaving(true)
        setMessage({ type: null, text: '' })

        try {
            const { error } = await updatePassword(passwordData.newPassword)

            if (error) {
                setMessage({ type: 'error', text: error })
            } else {
                setMessage({ type: 'success', text: 'Password updated successfully!' })
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
                    <h1>Profile</h1>
                    <p className="view-subtitle">Manage your account information</p>
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
                            <img src={profile.avatar_url} alt="Avatar" />
                        ) : (
                            <span>{user?.email?.charAt(0).toUpperCase() || '?'}</span>
                        )}
                    </div>
                    <div className="profile-info">
                        <h2>{profile?.full_name || user?.email?.split('@')[0]}</h2>
                        <p className="profile-email">{user?.email}</p>
                        <p className="profile-joined">
                            Member since {new Date(user?.created_at || Date.now()).toLocaleDateString()}
                        </p>
                    </div>
                    {!isEditing && (
                        <button
                            className="btn-edit"
                            onClick={() => setIsEditing(true)}
                        >
                            ✏️ Edit Profile
                        </button>
                    )}
                </div>

                {isEditing ? (
                    <form onSubmit={handleSaveProfile} className="profile-form">
                        <div className="form-row">
                            <div className="form-field">
                                <label htmlFor="full_name">Full Name</label>
                                <input
                                    id="full_name"
                                    name="full_name"
                                    type="text"
                                    value={formData.full_name}
                                    onChange={handleInputChange}
                                    placeholder="Your full name"
                                />
                            </div>
                            <div className="form-field">
                                <label htmlFor="company">Company</label>
                                <input
                                    id="company"
                                    name="company"
                                    type="text"
                                    value={formData.company}
                                    onChange={handleInputChange}
                                    placeholder="Your company"
                                />
                            </div>
                        </div>

                        <div className="form-field">
                            <label htmlFor="website">Website</label>
                            <input
                                id="website"
                                name="website"
                                type="url"
                                value={formData.website}
                                onChange={handleInputChange}
                                placeholder="https://your-website.com"
                            />
                        </div>

                        <div className="form-field">
                            <label htmlFor="bio">Bio</label>
                            <textarea
                                id="bio"
                                name="bio"
                                value={formData.bio}
                                onChange={handleInputChange}
                                placeholder="Tell us about yourself..."
                                rows={4}
                            />
                        </div>

                        <div className="form-actions">
                            <button
                                type="button"
                                className="btn-secondary"
                                onClick={() => setIsEditing(false)}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={isSaving}
                            >
                                {isSaving ? 'Saving...' : 'Save Changes'}
                            </button>
                        </div>
                    </form>
                ) : (
                    <div className="profile-details">
                        <div className="detail-row">
                            <span className="detail-label">Email</span>
                            <span className="detail-value">{user?.email}</span>
                        </div>
                        {profile?.company && (
                            <div className="detail-row">
                                <span className="detail-label">Company</span>
                                <span className="detail-value">{profile.company}</span>
                            </div>
                        )}
                        {profile?.website && (
                            <div className="detail-row">
                                <span className="detail-label">Website</span>
                                <a href={profile.website} target="_blank" rel="noopener noreferrer" className="detail-value link">
                                    {profile.website}
                                </a>
                            </div>
                        )}
                        {profile?.bio && (
                            <div className="detail-row">
                                <span className="detail-label">Bio</span>
                                <span className="detail-value">{profile.bio}</span>
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Security Section */}
            <div className="settings-section">
                <h3>Security</h3>

                {showPasswordForm ? (
                    <form onSubmit={handlePasswordChange} className="password-form">
                        <div className="form-field">
                            <label htmlFor="newPassword">New Password</label>
                            <input
                                id="newPassword"
                                type="password"
                                value={passwordData.newPassword}
                                onChange={(e) => setPasswordData(prev => ({
                                    ...prev,
                                    newPassword: e.target.value
                                }))}
                                placeholder="Enter new password"
                                minLength={8}
                                required
                            />
                        </div>
                        <div className="form-field">
                            <label htmlFor="confirmPassword">Confirm Password</label>
                            <input
                                id="confirmPassword"
                                type="password"
                                value={passwordData.confirmPassword}
                                onChange={(e) => setPasswordData(prev => ({
                                    ...prev,
                                    confirmPassword: e.target.value
                                }))}
                                placeholder="Confirm new password"
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
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn-primary"
                                disabled={isSaving}
                            >
                                {isSaving ? 'Updating...' : 'Update Password'}
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
                                <span className="security-label">Change Password</span>
                                <span className="security-desc">Update your account password</span>
                            </div>
                            <span className="security-arrow">→</span>
                        </button>
                    </div>
                )}
            </div>

            {/* Account Actions */}
            <div className="settings-section danger-zone">
                <h3>Danger Zone</h3>
                <div className="danger-actions">
                    <div className="danger-item">
                        <div className="danger-info">
                            <span className="danger-label">Delete Account</span>
                            <span className="danger-desc">
                                Permanently delete your account and all associated data
                            </span>
                        </div>
                        <button className="btn-danger">Delete Account</button>
                    </div>
                </div>
            </div>
        </div>
    )
}
