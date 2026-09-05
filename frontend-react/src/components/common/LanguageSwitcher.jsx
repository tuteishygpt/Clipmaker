import { useTranslation } from '../../i18n'
import './LanguageSwitcher.css'

export default function LanguageSwitcher({ className = '' }) {
    const { currentLang, setLanguage, availableLanguages } = useTranslation()

    return (
        <div className={`lang-switcher-root ${className}`}>
            <span className="lang-switcher-icon" title="Language">🌐</span>
            <select
                className="lang-switcher-select"
                value={currentLang}
                onChange={(e) => setLanguage(e.target.value)}
                aria-label="Language selection"
            >
                {availableLanguages.map((lang) => (
                    <option key={lang.code} value={lang.code}>
                        {lang.flag} {lang.native} ({lang.short})
                    </option>
                ))}
            </select>
        </div>
    )
}
