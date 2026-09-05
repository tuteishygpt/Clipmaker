export default {
    common: {
        save: 'Save',
        saving: 'Saving...',
        saved: 'Saved',
        unsaved: 'Unsaved',
        cancel: 'Cancel',
        delete: 'Delete',
        edit: 'Edit',
        close: 'Close',
        loading: 'Loading...',
        error: 'Error',
        search: 'Search...',
        apply: 'Apply',
        manageAccount: 'Manage Account',
    },
    nav: {
        studio: 'Studio',
        subtitles: 'Subtitles',
        myAccount: 'My Account',
        signIn: 'Sign In',
        login: 'Login',
        startFree: 'Start free',
        openStudio: 'Open Studio',
        product: 'Product',
        howItWorks: 'How it works',
        examples: 'Examples',
        pricing: 'Pricing',
        faq: 'FAQ',
        tagline: 'AI-powered music video generator'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'Create viral subtitles with karaoke, animations, and Gemini AI',
        dropzoneTitle: 'Drag & drop video here',
        dropzoneSubtitle: 'or click to browse file (MP4, MOV, WebM)',
        speechLanguage: 'Spoken language:',
        langAuto: 'Auto-detect (AI)',
        langBe: 'Belarusian',
        langEn: 'English',
        langEs: 'Spanish',
        langZh: 'Chinese',
        langFr: 'French',
        langDe: 'German',
        langJa: 'Japanese',
        langRu: 'Russian',
        langUk: 'Ukrainian',
        langPl: 'Polish',
        haveSrt: 'I already have .SRT',
        
        // Transcribing screen
        uploadingTitle: 'Uploading video to server...',
        transcribingTitle: 'Gemini AI is generating subtitles...',
        uploadingDesc: 'Preparing file for processing and extracting audio track.',
        transcribingDesc: 'Recognizing each word, computing timestamps, and applying karaoke preset.',
        skipToEditor: 'Skip and open editor',
        
        // Top bar
        newVideo: 'New Video',
        myVideos: 'My Videos',
        nextVideo: 'Next Video',
        prevVideo: 'Previous Video',
        switchVideo: 'Switch Video',
        recentVideos: 'Your Recent Videos',
        noRecentVideos: 'No saved videos yet',
        searchVideosPlaceholder: 'Search videos...',
        allProjectsInCabinet: 'Open all in Cabinet',
        videoCount: '{current} of {total}',
        uploadNextVideo: 'Upload new file',
        returnToDropzone: 'Return to upload',
        autosaveSaving: 'Saving...',
        autosaveSaved: 'Saved',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Download subtitles in .SRT format',
        downloadVideo: 'Download video (MP4)',
        exportRender: 'Export / Render',
        exportMenu: 'Export',
        exportVideo: 'Video with Subtitles (MP4)',
        exportVideoDesc: 'Render & download video',
        exportVideoReadyDesc: 'Ready to download',
        exportSrt: 'Subtitles (.SRT)',
        exportSrtDesc: 'Download subtitle file',
        rendering: 'Rendering ({progress}%)',
        
        // Tabs
        tabs: {
            captions: 'Subtitles ({count})',
            styling: 'Style',
            presets: 'Presets'
        },
        
        // Captions tab
        searchPlaceholder: 'Search text...',
        addCaption: '+ Add',
        noEntries: 'No subtitles yet. Start AI recognition or add a line manually.',
        transcribeAgain: 'Transcribe with AI',
        
        // Styling tab
        fontAndText: 'Font & Text',
        fontFamily: 'Font',
        fontSize: 'Font Size',
        fontWeight: 'Font Weight',
        weightNormal: 'Regular (400)',
        weightBold: 'Bold (700)',
        weightBlack: 'Extra Bold Black (900)',
        uppercase: 'UPPERCASE all letters',
        
        colorsAndStroke: 'Colors & Stroke',
        textColor: 'Text Color',
        strokeColor: 'Stroke Color',
        strokeWidth: 'Stroke Width',
        
        backgroundPlate: 'Background Box',
        enableBackground: 'Enable background box under subtitles',
        backgroundColor: 'Background Color',
        opacity: 'Opacity',
        
        positioning: 'Positioning',
        position: 'Position',
        posBottom: 'Bottom',
        posMiddle: 'Center',
        posTop: 'Top',
        marginY: 'Margin (Y)',
        
        karaokeAndAnimation: 'Karaoke & Animation',
        karaokeHighlight: 'Karaoke highlight active word',
        badgeColor: 'Badge Color',
        
        // Preset cards
        presets: {
            viralTag: 'Top for Shorts / Reels',
            neonTag: 'Glow & Music',
            mrbeastTag: 'Dynamics & Attention',
            netflixTag: 'Podcasts & Cinema',
            minimalTag: 'Aesthetic & Vlogs',
            classicTag: 'Classic TV',
            selected: '✓ Selected',
            applyStyle: 'Apply Style'
        },
        
        // Entry card
        card: {
            startTimeTitle: 'Subtitle start (00:00:00,000)',
            endTimeTitle: 'Subtitle end (00:00:00,000)',
            durationTitle: 'Duration',
            secShort: 's',
            seek: '▶ Jump',
            seekTitle: 'Jump to this timestamp in video',
            deleteTitle: 'Delete this subtitle',
            placeholder: 'Enter subtitle text...',
            
            // Accents
            accentsTitle: '⚡ Word accents:',
            accentsHint: 'click a word for karaoke highlight',
            removeHighlightTitle: 'Remove highlight from "{text}"',
            addHighlightTitle: 'Highlight "{text}" with bright color',
            
            // Toolbar
            highlightFragment: 'Highlight fragment',
            highlight: 'Highlight',
            highlightFragmentTitle: 'Highlight selected fragment with <h> tag',
            highlightFirstTitle: 'Highlight first word',
            case: 'Case',
            caseTitle: 'Cycle case: UPPERCASE / Sentence case',
            clear: 'Clear',
            clearTitle: 'Remove all word highlights',
            split: 'Split',
            splitTitle: 'Split this subtitle into two parts',
            merge: 'Merge',
            mergeTitle: 'Merge with the next subtitle',
            
            // Pace badges
            paceOptimal: 'Optimal',
            paceOptimalTitle: '{cps} char/s • {words} words — comfortable reading pace',
            paceFast: 'Fast',
            paceFastTitle: '{cps} char/s • {words} words — fast speech tempo',
            paceTooFast: 'Too fast',
            paceTooFastTitle: '{cps} char/s • {words} words — viewer might not have time to read!'
        },
        
        // Timeline
        timeline: {
            singular: 'subtitle',
            plural: 'subtitles'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ Subtitle preview with video',
            previous: '◀ Previous',
            next: 'Next ▶',
            counter: 'Subtitle {current} of {total}',
            empty: '(empty)',
            tip: '💡 Play the video to preview synchronization or switch subtitles with arrow keys.'
        }
    },
    profile: {
        preferencesTitle: 'Preferences',
        preferencesDesc: 'Customize your interface language and personal app settings',
        languageLabel: 'Interface Language',
        languageDesc: 'Select your preferred language. Changes apply immediately across the entire studio.',
        languageActiveBadge: 'Active',
        languageUpdated: 'Language preference updated successfully!'
    }
}
