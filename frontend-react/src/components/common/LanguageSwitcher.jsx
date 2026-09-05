import { useTranslation } from '../../i18n'
import './LanguageSwitcher.css'

export default function LanguageSwitcher({ className = '' }) {
    const { currentLang, setLanguage, availableLanguages } = useTranslation()

    return (
        <div className={`lang-switcher-root ${className}`}>
            <span className="lang-switcher-icon" title="Language / Мова">🌐</span>
            <div className="lang-switcher-buttons">
                {availableLanguages.map((lang) => (
                    <button
                        key={lang.code}
                        type="button"
                        className={`lang-btn ${currentLang === lang.code ? 'active' : ''}`}
                        onClick={() => setLanguage(lang.code)}
                        title={lang.label}
                    >
                        {lang.short}
                    </button>
                ))}
            </div>
        </div>
    )
}
