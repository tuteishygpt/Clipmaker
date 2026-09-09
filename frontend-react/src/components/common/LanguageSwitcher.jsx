import { useState, useRef, useEffect } from 'react'
import { useTranslation } from '../../i18n'
import './LanguageSwitcher.css'

export default function LanguageSwitcher({ className = '', compact = false }) {
    const { currentLang, setLanguage, availableLanguages } = useTranslation()
    const [isOpen, setIsOpen] = useState(false)
    const containerRef = useRef(null)

    const activeLanguage = availableLanguages.find(l => l.code === currentLang) || availableLanguages[0]

    useEffect(() => {
        function handleClickOutside(e) {
            if (containerRef.current && !containerRef.current.contains(e.target)) {
                setIsOpen(false)
            }
        }
        function handleKeyDown(e) {
            if (e.key === 'Escape') {
                setIsOpen(false)
            }
        }
        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside)
            document.addEventListener('keydown', handleKeyDown)
        }
        return () => {
            document.removeEventListener('mousedown', handleClickOutside)
            document.removeEventListener('keydown', handleKeyDown)
        }
    }, [isOpen])

    const handleSelect = (code) => {
        setLanguage(code)
        setIsOpen(false)
    }

    return (
        <div className={`lang-switcher-container ${className}`} ref={containerRef}>
            <button
                type="button"
                className={`lang-switcher-trigger ${compact ? 'compact' : ''} ${isOpen ? 'active' : ''}`}
                onClick={() => setIsOpen(prev => !prev)}
                aria-haspopup="listbox"
                aria-expanded={isOpen}
                title={activeLanguage.native}
            >
                <span className="lang-flag">{activeLanguage.flag}</span>
                <span className="lang-code">{activeLanguage.short}</span>
                <span className="lang-caret">▾</span>
            </button>

            {isOpen && (
                <div className="lang-dropdown-menu" role="listbox">
                    {availableLanguages.map((lang) => {
                        const isSelected = lang.code === currentLang
                        return (
                            <button
                                key={lang.code}
                                type="button"
                                role="option"
                                aria-selected={isSelected}
                                className={`lang-dropdown-item ${isSelected ? 'selected' : ''}`}
                                onClick={() => handleSelect(lang.code)}
                            >
                                <span className="lang-item-flag">{lang.flag}</span>
                                <span className="lang-item-name">{lang.native}</span>
                                <span className="lang-item-code">{lang.short}</span>
                            </button>
                        )
                    })}
                </div>
            )}
        </div>
    )
}
