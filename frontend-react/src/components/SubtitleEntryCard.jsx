import React, { useRef, useEffect, useMemo, useState, memo } from 'react'
import { parseSrtTimeToSeconds } from './SubtitleVideoPlayer'

/**
 * Convert seconds to SRT time format: 00:00:00,000
 */
export function formatSecondsToSrt(seconds) {
    const t = Math.max(0, Number(seconds) || 0)
    const h = Math.floor(t / 3600)
    const m = Math.floor((t % 3600) / 60)
    const s = Math.floor(t % 60)
    const ms = Math.min(999, Math.round((t % 1) * 1000))
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')},${String(ms).padStart(3, '0')}`
}

/**
 * Ensure tags are balanced, unnested, and strictly lowercase: <h>...</h>
 */
export function sanitizeHighlightTags(text = '') {
    if (!text) return ''

    // 1. Normalize case to lowercase <h> and </h>
    let normalized = text.replace(/<h>/gi, '<h>').replace(/<\/h>/gi, '</h>')

    // 2. Eliminate nested tags (e.g. <h>word <h>nested</h> word</h>)
    let cleaned = ''
    let isInside = false
    const parts = normalized.split(/(<h>|<\/h>)/gi)

    for (const part of parts) {
        if (!part) continue
        if (part === '<h>') {
            if (!isInside) {
                cleaned += '<h>'
                isInside = true
            }
            // Ignore nested <h>
        } else if (part === '</h>') {
            if (isInside) {
                cleaned += '</h>'
                isInside = false
            }
            // Ignore orphaned </h>
        } else {
            cleaned += part
        }
    }

    // 3. Close open tag if still inside
    if (isInside) {
        cleaned += '</h>'
    }

    // 4. Remove empty tags: <h></h> or <h>\s*</h>
    cleaned = cleaned.replace(/<h>\s*<\/h>/gi, '')

    return cleaned
}

/**
 * Tokenize subtitle text into individual words while identifying <h> tags.
 */
export function extractWordTokens(text = '') {
    if (!text) return []

    // Case-insensitive match for <h>...</h>
    const parts = text.split(/(<h>.*?<\/h>)/gi)
    const tokens = []

    parts.forEach(part => {
        if (!part) return
        const isHighlight = /^<h>[\s\S]*<\/h>$/i.test(part)
        const innerContent = isHighlight ? part.slice(3, -4) : part

        // Split tokens by whitespace, preserving space tokens
        const words = innerContent.split(/(\s+)/)
        words.forEach(w => {
            if (!w) return
            const isWhitespace = /^\s+$/.test(w)
            tokens.push({
                raw: w,
                text: w,
                isWhitespace,
                isHighlighted: isHighlight && !isWhitespace
            })
        })
    })

    return tokens
}

function SubtitleEntryCard({
    entry,
    idx,
    isActive,
    styling = {},
    onUpdate,
    onDelete,
    onSeek,
    onSplit,
    onMergeNext,
    hasNext,
    isUserTypingRef
}) {
    const textareaRef = useRef(null)
    const selectionTimeoutRef = useRef(null)
    const [hasSelection, setHasSelection] = useState(false)
    const [selectionRange, setSelectionRange] = useState({ start: 0, end: 0 })

    // Auto-adjust textarea height to fit content smoothly without resize handle
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            const scrollHeight = textareaRef.current.scrollHeight
            textareaRef.current.style.height = `${Math.max(52, scrollHeight)}px`
        }
    }, [entry.text])

    // Clean up timers on unmount
    useEffect(() => {
        return () => {
            if (selectionTimeoutRef.current) clearTimeout(selectionTimeoutRef.current)
        }
    }, [])

    // Calculate duration & reading pace
    const startSec = parseSrtTimeToSeconds(entry.start_time)
    const endSec = parseSrtTimeToSeconds(entry.end_time)
    const durationSec = Math.max(0.1, endSec - startSec)
    const cleanText = (entry.text || '').replace(/<\/?h>/gi, '').trim()
    const wordCount = cleanText ? cleanText.split(/\s+/).filter(Boolean).length : 0
    const charCount = cleanText.length

    // Characters per second (CPS)
    const cps = durationSec > 0 ? (charCount / durationSec).toFixed(1) : 0
    let paceBadge = { label: 'Звычайна', class: 'pace-optimal', icon: '🟢', title: `${cps} сімв/с • ${wordCount} сл. — чытаецца камфортна` }
    if (cps > 24) {
        paceBadge = { label: 'Занадта хутка', class: 'pace-too-fast', icon: '🔴', title: `${cps} сімв/с • ${wordCount} сл. — глядач можа не паспець прачытаць!` }
    } else if (cps > 17) {
        paceBadge = { label: 'Хутка', class: 'pace-fast', icon: '🟡', title: `${cps} сімв/с • ${wordCount} сл. — хуткі тэмп маўлення` }
    } else if (charCount === 0) {
        paceBadge = null
    }

    // Word tokens for interactive chips (filtering out pure punctuation chips like standalone ",")
    const wordTokens = useMemo(() => {
        return extractWordTokens(entry.text).filter(t => {
            if (t.isWhitespace) return false
            // Avoid standalone punctuation like "," or "..." as chip
            return !/^[\p{P}\p{S}]+$/u.test(t.text.trim())
        })
    }, [entry.text])

    const highlightedWordsCount = wordTokens.filter(t => t.isHighlighted).length

    // Toggle highlight on a specific word chip
    const handleToggleWordHighlight = (wordIdx) => {
        const tokens = extractWordTokens(entry.text)
        let eligibleIdx = 0

        for (let i = 0; i < tokens.length; i++) {
            const isEligible = !tokens[i].isWhitespace && !/^[\p{P}\p{S}]+$/u.test(tokens[i].text.trim())
            if (isEligible) {
                if (eligibleIdx === wordIdx) {
                    tokens[i].isHighlighted = !tokens[i].isHighlighted
                    break
                }
                eligibleIdx++
            }
        }

        // Reconstruct string
        const newText = tokens.map(t => {
            if (t.isWhitespace) return t.raw
            return t.isHighlighted ? `<h>${t.text}</h>` : t.text
        }).join('')

        onUpdate(entry.id, 'text', sanitizeHighlightTags(newText))
    }

    // Handle cursor selection detection
    const handleSelectText = () => {
        const ta = textareaRef.current
        if (!ta) return
        const start = ta.selectionStart
        const end = ta.selectionEnd
        if (end > start) {
            setHasSelection(true)
            setSelectionRange({ start, end })
        } else {
            setHasSelection(false)
        }
    }

    // Highlight or toggle selected text
    const handleHighlightSelectedOrFirst = () => {
        const ta = textareaRef.current
        if (hasSelection && ta && selectionRange.end > selectionRange.start) {
            const before = entry.text.slice(0, selectionRange.start)
            const selected = entry.text.slice(selectionRange.start, selectionRange.end)
            const after = entry.text.slice(selectionRange.end)

            // Remove any tags inside selection before wrapping to avoid nesting
            const cleanSelection = selected.replace(/<\/?h>/gi, '')

            let newText
            if (/<h>/i.test(selected) || /<\/h>/i.test(selected)) {
                // If selection contains tags, toggle them off
                newText = before + cleanSelection + after
            } else {
                // Wrap in tag
                newText = before + `<h>${cleanSelection}</h>` + after
            }

            onUpdate(entry.id, 'text', sanitizeHighlightTags(newText))
            setHasSelection(false)
            return
        }

        // Fallback: toggle highlight on first word if no text selected
        if (wordTokens.length > 0) {
            handleToggleWordHighlight(0)
        }
    }

    // Clear all highlight tags
    const handleClearHighlights = () => {
        const cleared = entry.text.replace(/<\/?h>/gi, '')
        onUpdate(entry.id, 'text', cleared)
    }

    // Cycle text case (UPPERCASE -> Sentence case) with STRICT <h> preservation & Unicode support
    const handleCycleCase = () => {
        const text = entry.text || ''
        const clean = text.replace(/<\/?h>/gi, '')
        const isUpper = clean === clean.toUpperCase() && clean !== clean.toLowerCase()

        if (isUpper) {
            // Convert to Sentence case (lower, with capitalized first letter of phrase)
            let lower = text.toLowerCase()
            lower = lower.replace(/<h>/gi, '<h>').replace(/<\/h>/gi, '</h>')

            // Capitalize first non-tag letter using Unicode property \p{L}
            let capitalized = false
            const parts = lower.split(/(<h>.*?<\/h>)/gi)
            const transformedParts = parts.map(part => {
                if (capitalized) return part
                const isHl = /^<h>[\s\S]*<\/h>$/i.test(part)
                const content = isHl ? part.slice(3, -4) : part

                const match = content.match(/\p{L}/u)
                if (match && !capitalized) {
                    capitalized = true
                    const letterIndex = match.index
                    const newContent = content.slice(0, letterIndex) + match[0].toUpperCase() + content.slice(letterIndex + 1)
                    return isHl ? `<h>${newContent}</h>` : newContent
                }
                return part
            })

            onUpdate(entry.id, 'text', sanitizeHighlightTags(transformedParts.join('')))
        } else {
            // Convert to UPPERCASE, but ensure <h> and </h> remain strictly lowercase
            const upper = text.toUpperCase()
                .replace(/<H>/g, '<h>')
                .replace(/<\/H>/g, '</h>')
            onUpdate(entry.id, 'text', sanitizeHighlightTags(upper))
        }
    }

    // Trigger split at cursor or middle
    const handleTriggerSplit = () => {
        if (!onSplit) return
        const ta = textareaRef.current
        const cursor = ta ? ta.selectionStart : null
        onSplit(entry.id, cursor)
    }

    // Custom highlight styling colors from studio presets with unified defaults
    const highlightBg = styling?.highlight_bg_color || '#FF0000'
    const highlightColor = styling?.highlight_font_color || '#FFFFFF'

    return (
        <div
            data-entry-id={entry.id}
            className={`caption-card ${isActive ? 'active' : ''}`}
        >
            {/* 1. Header: Number, Timestamps, Pace & Main Actions */}
            <div className="caption-card-header">
                <div className="caption-header-left">
                    <span className="caption-index-badge">#{idx + 1}</span>
                    <div className="caption-card-time">
                        <input
                            type="text"
                            value={entry.start_time}
                            title="Пачатак субцітра (00:00:00,000)"
                            onFocus={() => { if (isUserTypingRef) isUserTypingRef.current = true }}
                            onBlur={() => { if (isUserTypingRef) isUserTypingRef.current = false }}
                            onChange={(e) => onUpdate(entry.id, 'start_time', e.target.value)}
                        />
                        <span className="time-arrow">→</span>
                        <input
                            type="text"
                            value={entry.end_time}
                            title="Канец субцітра (00:00:00,000)"
                            onFocus={() => { if (isUserTypingRef) isUserTypingRef.current = true }}
                            onBlur={() => { if (isUserTypingRef) isUserTypingRef.current = false }}
                            onChange={(e) => onUpdate(entry.id, 'end_time', e.target.value)}
                        />
                    </div>
                    <span className="caption-duration-badge" title="Працягласць">
                        {durationSec.toFixed(1)}с
                    </span>

                    {paceBadge && (
                        <span className={`pace-badge ${paceBadge.class}`} title={paceBadge.title}>
                            <span className="pace-dot">{paceBadge.icon}</span>
                            <span className="pace-text">{paceBadge.label}</span>
                        </span>
                    )}
                </div>

                <div className="caption-card-actions">
                    <button
                        type="button"
                        className="btn-card-seek"
                        onClick={() => onSeek?.(startSec)}
                        title="Перайсці да гэтага моманту на відэа"
                    >
                        ▶ Перайсці
                    </button>
                    <button
                        type="button"
                        className="btn-card-delete"
                        onClick={() => onDelete?.(entry.id)}
                        title="Выдаліць гэты субцітр"
                    >
                        🗑️
                    </button>
                </div>
            </div>

            {/* 2. Text Editor Area */}
            <div className="caption-text-area-wrapper">
                <textarea
                    ref={textareaRef}
                    className="caption-textarea"
                    value={entry.text}
                    onFocus={() => { if (isUserTypingRef) isUserTypingRef.current = true }}
                    onBlur={() => {
                        if (isUserTypingRef) isUserTypingRef.current = false
                        if (selectionTimeoutRef.current) clearTimeout(selectionTimeoutRef.current)
                        selectionTimeoutRef.current = setTimeout(() => setHasSelection(false), 250)
                    }}
                    onSelect={handleSelectText}
                    onKeyUp={handleSelectText}
                    onMouseUp={handleSelectText}
                    onChange={(e) => onUpdate(entry.id, 'text', e.target.value)}
                    placeholder="Увядзіце тэкст субцітра..."
                    rows={1}
                />
            </div>

            {/* 3. Interactive Word Accent Chips Bar */}
            {wordTokens.length > 0 && (
                <div className="caption-words-accent-bar">
                    <div className="accent-bar-header">
                        <span className="accent-bar-title">
                            ⚡ Акцэнты слоў:
                        </span>
                        <span className="accent-bar-hint">
                            клікніце на слова для караоке-вылучэння
                        </span>
                    </div>

                    <div className="caption-word-chips-list">
                        {wordTokens.map((t, wIdx) => {
                            return (
                                <button
                                    key={wIdx}
                                    type="button"
                                    className={`word-chip ${t.isHighlighted ? 'highlighted' : ''}`}
                                    style={t.isHighlighted ? {
                                        backgroundColor: highlightBg,
                                        color: highlightColor,
                                        borderColor: highlightBg,
                                        boxShadow: `0 2px 10px ${highlightBg}55`
                                    } : undefined}
                                    onClick={() => handleToggleWordHighlight(wIdx)}
                                    title={t.isHighlighted
                                        ? `Зняць вылучэнне з «${t.text}»`
                                        : `Вылучыць «${t.text}» яркім колерам`}
                                >
                                    {t.isHighlighted && <span className="chip-sparkle">✨</span>}
                                    <span className="chip-text">{t.text}</span>
                                    {t.isHighlighted && <span className="chip-remove">×</span>}
                                </button>
                            )
                        })}
                    </div>
                </div>
            )}

            {/* 4. Creator Toolbar: Split, Merge, Case, Clear */}
            <div className="caption-card-footer-toolbar">
                <div className="toolbar-left-group">
                    <button
                        type="button"
                        className={`btn-toolbar-action ${hasSelection ? 'pulse-active' : ''}`}
                        onClick={handleHighlightSelectedOrFirst}
                        title={hasSelection ? 'Вылучыць выдзелены фрагмент тэгам <h>' : 'Вылучыць першае слова'}
                    >
                        ✨ {hasSelection ? 'Вылучыць фрагмент' : 'Вылучыць'}
                    </button>

                    <button
                        type="button"
                        className="btn-toolbar-action"
                        onClick={handleCycleCase}
                        title="Змяніць рэгістр: УСЕ ВЯЛІКІЯ / Як у сказе"
                    >
                        🔤 Рэгістр
                    </button>

                    {highlightedWordsCount > 0 && (
                        <button
                            type="button"
                            className="btn-toolbar-action btn-clear-tags"
                            onClick={handleClearHighlights}
                            title="Зняць усе вылучэнні"
                        >
                            🧹 Ачысціць
                        </button>
                    )}
                </div>

                <div className="toolbar-right-group">
                    <button
                        type="button"
                        className="btn-toolbar-action"
                        onClick={handleTriggerSplit}
                        title="Разбіць гэты субцітр на два асобныя"
                    >
                        ✂️ Разбіць
                    </button>

                    {hasNext && (
                        <button
                            type="button"
                            className="btn-toolbar-action"
                            onClick={() => onMergeNext?.(entry.id)}
                            title="Аб'яднаць з наступным субцітрам"
                        >
                            🔗 Аб'яднаць
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}

export default memo(SubtitleEntryCard)
