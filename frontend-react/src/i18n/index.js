import { useLanguageStore, AVAILABLE_LANGUAGES } from './i18nStore'

export function useTranslation() {
    const currentLang = useLanguageStore((state) => state.currentLang)
    const setLanguage = useLanguageStore((state) => state.setLanguage)
    const t = useLanguageStore((state) => state.t)
    const formatCount = useLanguageStore((state) => state.formatCount)

    return {
        t,
        formatCount,
        currentLang,
        setLanguage,
        availableLanguages: AVAILABLE_LANGUAGES
    }
}

export { AVAILABLE_LANGUAGES, useLanguageStore }
