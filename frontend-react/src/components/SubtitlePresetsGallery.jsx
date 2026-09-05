import './SubtitlePresetsGallery.css'

export const STUDIO_PRESETS = [
    {
        id: 'viral',
        name: 'TikTok Viral',
        tag: 'Топ для Shorts / Reels',
        icon: '🔥',
        previewText: 'VIRAL HOOK',
        previewStyle: {
            fontFamily: 'Montserrat, sans-serif',
            fontWeight: 900,
            color: '#FFE600',
            textShadow: '0 0 4px #000, 0 0 8px #000',
            textTransform: 'uppercase'
        },
        badgeStyle: {
            backgroundColor: '#FF0000',
            color: '#FFFFFF'
        },
        styling: {
            font_family: 'Montserrat',
            font_size: 52,
            font_weight: '900',
            font_color: '#FFE600',
            stroke_color: '#000000',
            stroke_width: 4,
            background_enabled: false,
            position: 'middle',
            margin_y: 60,
            text_align: 'center',
            uppercase: true,
            animation: 'pop',
            highlight_active_word: true,
            highlight_font_color: '#FFFFFF',
            highlight_bg_color: '#FF0000',
            highlight_bg_padding: 8,
            highlight_bg_radius: 8
        }
    },
    {
        id: 'neon',
        name: 'Cyber Neon',
        tag: 'Ззянне і музыка',
        icon: '⚡',
        previewText: 'NEON WAVE',
        previewStyle: {
            fontFamily: 'Outfit, sans-serif',
            fontWeight: 700,
            color: '#00FFF0',
            textShadow: '0 0 6px #D900FF, 0 0 12px #D900FF',
            textTransform: 'uppercase'
        },
        badgeStyle: {
            backgroundColor: '#D900FF',
            color: '#FFFFFF'
        },
        styling: {
            font_family: 'Outfit',
            font_size: 48,
            font_weight: 'bold',
            font_color: '#00FFF0',
            stroke_color: '#1a0033',
            stroke_width: 4,
            background_enabled: false,
            position: 'bottom',
            margin_y: 70,
            text_align: 'center',
            uppercase: true,
            animation: 'pop',
            highlight_active_word: true,
            highlight_font_color: '#FFFFFF',
            highlight_bg_color: '#D900FF',
            highlight_bg_padding: 8,
            highlight_bg_radius: 12
        }
    },
    {
        id: 'mrbeast',
        name: 'MrBeast Bold',
        tag: 'Дынаміка і ўвага',
        icon: '💪',
        previewText: 'CRAZY DEAL',
        previewStyle: {
            fontFamily: 'Impact, sans-serif',
            fontWeight: 900,
            color: '#FFFFFF',
            textShadow: '0 0 6px #000, 0 0 10px #000',
            textTransform: 'uppercase'
        },
        badgeStyle: {
            backgroundColor: '#FFE600',
            color: '#000000'
        },
        styling: {
            font_family: 'Impact',
            font_size: 56,
            font_weight: '900',
            font_color: '#FFFFFF',
            stroke_color: '#000000',
            stroke_width: 5,
            background_enabled: false,
            position: 'bottom',
            margin_y: 80,
            text_align: 'center',
            uppercase: true,
            animation: 'pop',
            highlight_active_word: true,
            highlight_font_color: '#000000',
            highlight_bg_color: '#FFE600',
            highlight_bg_padding: 8,
            highlight_bg_radius: 8
        }
    },
    {
        id: 'netflix',
        name: 'Netflix Cinema',
        tag: 'Падкасты і кіно',
        icon: '🍿',
        previewText: 'Cinematic dialog',
        previewStyle: {
            fontFamily: 'Roboto, sans-serif',
            fontWeight: 700,
            color: '#FFFFFF',
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: '4px 10px',
            borderRadius: '4px'
        },
        styling: {
            font_family: 'Roboto',
            font_size: 42,
            font_weight: 'bold',
            font_color: '#FFFFFF',
            stroke_color: '#000000',
            stroke_width: 0,
            background_enabled: true,
            background_color: '#000000',
            background_opacity: 0.8,
            background_padding: 10,
            background_radius: 6,
            position: 'bottom',
            margin_y: 60,
            text_align: 'center',
            uppercase: false,
            animation: 'none',
            highlight_active_word: false
        }
    },
    {
        id: 'minimal',
        name: 'Minimal Clean',
        tag: 'Эстэтыка і блогі',
        icon: '✨',
        previewText: 'Aesthetic mood',
        previewStyle: {
            fontFamily: 'Inter, sans-serif',
            fontWeight: 400,
            color: '#F0F0F0',
            textShadow: '0 0 2px #000'
        },
        styling: {
            font_family: 'Inter',
            font_size: 38,
            font_weight: 'normal',
            font_color: '#F0F0F0',
            stroke_color: '#000000',
            stroke_width: 1,
            background_enabled: false,
            position: 'bottom',
            margin_y: 50,
            text_align: 'center',
            uppercase: false,
            animation: 'none',
            highlight_active_word: false
        }
    },
    {
        id: 'classic',
        name: 'Classic TV',
        tag: 'Зразумелы тэлевізар',
        icon: '📺',
        previewText: 'Classic TV Sub',
        previewStyle: {
            fontFamily: 'Arial, sans-serif',
            fontWeight: 700,
            color: '#FFFF00',
            textShadow: '0 0 4px #000, 0 0 8px #000'
        },
        styling: {
            font_family: 'Arial',
            font_size: 46,
            font_weight: 'bold',
            font_color: '#FFFF00',
            stroke_color: '#000000',
            stroke_width: 3,
            background_enabled: false,
            position: 'bottom',
            margin_y: 55,
            text_align: 'center',
            uppercase: false,
            animation: 'none',
            highlight_active_word: false
        }
    }
]

export default function SubtitlePresetsGallery({ currentStyling, onApplyPreset }) {
    return (
        <div className="presets-gallery-grid">
            {STUDIO_PRESETS.map((preset) => {
                const isCurrent = currentStyling?.font_family === preset.styling.font_family &&
                    currentStyling?.highlight_active_word === preset.styling.highlight_active_word &&
                    currentStyling?.font_color === preset.styling.font_color

                return (
                    <div
                        key={preset.id}
                        className={`preset-card ${isCurrent ? 'active' : ''}`}
                        onClick={() => onApplyPreset(preset.styling)}
                    >
                        <div className="preset-card-header">
                            <span className="preset-icon">{preset.icon}</span>
                            <div className="preset-meta">
                                <span className="preset-title">{preset.name}</span>
                                <span className="preset-tag">{preset.tag}</span>
                            </div>
                        </div>

                        {/* Live mini-preview of text and badge */}
                        <div className="preset-visual-preview">
                            <span style={preset.previewStyle}>
                                {preset.previewText}
                            </span>
                            {preset.badgeStyle && (
                                <span
                                    className="preset-preview-badge"
                                    style={preset.badgeStyle}
                                >
                                    WORD
                                </span>
                            )}
                        </div>

                        <div className="preset-card-footer">
                            <span className="preset-apply-btn">
                                {isCurrent ? '✓ Выбрана' : 'Ужыць стыль'}
                            </span>
                        </div>
                    </div>
                )
            })}
        </div>
    )
}
