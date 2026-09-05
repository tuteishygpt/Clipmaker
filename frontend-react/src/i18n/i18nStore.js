import { create } from 'zustand'
import en from './locales/en.js'
import be from './locales/be.js'
import es from './locales/es.js'
import zh from './locales/zh.js'
import fr from './locales/fr.js'
import de from './locales/de.js'
import ja from './locales/ja.js'

const dictionaries = { en, be, es, zh, fr, de, ja }

export const AVAILABLE_LANGUAGES = [
    { code: 'en', label: 'English', native: 'English', flag: '🇬🇧', short: 'EN' },
    { code: 'es', label: 'Spanish', native: 'Español', flag: '🇪🇸', short: 'ES' },
    { code: 'zh', label: 'Chinese', native: '简体中文', flag: '🇨🇳', short: 'ZH' },
    { code: 'fr', label: 'French', native: 'Français', flag: '🇫🇷', short: 'FR' },
    { code: 'de', label: 'German', native: 'Deutsch', flag: '🇩🇪', short: 'DE' },
    { code: 'ja', label: 'Japanese', native: '日本語', flag: '🇯🇵', short: 'JA' },
    { code: 'be', label: 'Belarusian', native: 'Беларуская', flag: '🇧🇾', short: 'BE' }
]

function applyDocumentLang(lang) {
    if (typeof document !== 'undefined' && document.documentElement) {
        document.documentElement.lang = lang
    }
}

function getInitialLanguage() {
    let lang = 'en'
    try {
        const saved = localStorage.getItem('clipmaker_lang')
        if (saved && dictionaries[saved]) {
            lang = saved
        }
    } catch (e) {
        // Ignore localStorage error (e.g. incognito)
    }
    applyDocumentLang(lang)
    return lang
}

function resolveKey(dict, path) {
    if (!dict || !path) return null
    const parts = path.split('.')
    let current = dict
    for (const part of parts) {
        if (current === undefined || current === null) return null
        current = current[part]
    }
    return current
}

function interpolate(text, params) {
    if (typeof text !== 'string' || !params) return text
    return text.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, key) => {
        return params[key] !== undefined ? params[key] : match
    })
}

export const useLanguageStore = create((set, get) => ({
    currentLang: getInitialLanguage(),
    
    setLanguage: (lang) => {
        if (!dictionaries[lang]) return
        try {
            localStorage.setItem('clipmaker_lang', lang)
        } catch (e) {
            // Ignore storage error
        }
        applyDocumentLang(lang)
        set({ currentLang: lang })
    },
    
    // Translation lookup helper
    t: (path, params = null) => {
        const { currentLang } = get()
        let val = resolveKey(dictionaries[currentLang], path)
        if (val === undefined || val === null) {
            // Fallback to English
            val = resolveKey(dictionaries.en, path)
        }
        if (val === undefined || val === null) {
            return path
        }
        return interpolate(val, params)
    },

    // Pluralization helper using native Intl.PluralRules (CLDR standard for all languages)
    formatCount: (count, pathPrefix) => {
        const { currentLang } = get()
        const c = Math.abs(Number(count) || 0)
        const dict = dictionaries[currentLang] || dictionaries.en

        let category = 'other'
        try {
            const pr = new Intl.PluralRules(currentLang)
            category = pr.select(c) // 'zero' | 'one' | 'two' | 'few' | 'many' | 'other'
        } catch (e) {
            category = c === 1 ? 'one' : 'other'
        }

        // Map CLDR categories to project form keys (singular, few, plural)
        const formMap = {
            one: 'singular',
            few: 'few',
            many: 'plural',
            other: 'plural'
        }
        const targetForm = formMap[category] || 'plural'

        const label = resolveKey(dict, `${pathPrefix}.${targetForm}`) ||
                      resolveKey(dict, `${pathPrefix}.plural`) ||
                      resolveKey(dict, `${pathPrefix}.singular`) ||
                      resolveKey(dictionaries.en, `${pathPrefix}.${targetForm}`) ||
                      resolveKey(dictionaries.en, `${pathPrefix}.plural`) ||
                      ''
        return `${count} ${label}`.trim()
    }
}))
