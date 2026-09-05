export default {
    common: {
        save: 'Speichern',
        saving: 'Wird gespeichert...',
        saved: 'Gespeichert',
        unsaved: 'Nicht gespeichert',
        cancel: 'Abbrechen',
        delete: 'Löschen',
        edit: 'Bearbeiten',
        close: 'Schließen',
        loading: 'Wird geladen...',
        error: 'Fehler',
        search: 'Suchen...',
        apply: 'Anwenden',
        manageAccount: 'Konto verwalten',
    },
    nav: {
        studio: 'Studio',
        subtitles: 'Untertitel',
        myAccount: 'Mein Konto',
        signIn: 'Anmelden',
        login: 'Login',
        startFree: 'Kostenlos starten',
        openStudio: 'Studio öffnen',
        product: 'Produkt',
        howItWorks: 'Funktionsweise',
        examples: 'Beispiele',
        pricing: 'Preise',
        faq: 'FAQ',
        tagline: 'KI-gestützter Musikvideo-Generator'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'Erstelle virale Untertitel mit Karaoke-Effekten, Animationen und Gemini KI',
        dropzoneTitle: 'Video hierher ziehen und ablegen',
        dropzoneSubtitle: 'oder klicken, um eine Datei auszuwählen (MP4, MOV, WebM)',
        speechLanguage: 'Gesprochene Sprache:',
        langAuto: 'Automatische Erkennung (KI)',
        langBe: 'Weißrussisch',
        langEn: 'Englisch',
        langEs: 'Spanisch',
        langZh: 'Chinesisch',
        langFr: 'Französisch',
        langDe: 'Deutsch',
        langJa: 'Japanisch',
        langRu: 'Russisch',
        langUk: 'Ukrainisch',
        langPl: 'Polnisch',
        haveSrt: 'Ich habe bereits eine .SRT-Datei',
        
        // Transcribing screen
        uploadingTitle: 'Video wird auf den Server geladen...',
        transcribingTitle: 'Gemini KI generiert Untertitel...',
        uploadingDesc: 'Datei wird vorbereitet und die Tonspur extrahiert.',
        transcribingDesc: 'Jedes Wort wird erkannt, Timecodes berechnet und das Karaoke-Design angewendet.',
        skipToEditor: 'Überspringen und Editor öffnen',
        
        // Top bar
        autosaveSaving: 'Wird gespeichert...',
        autosaveSaved: 'Gespeichert',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Untertitel im .SRT-Format herunterladen',
        downloadVideo: 'Video herunterladen (MP4)',
        exportRender: 'Exportieren / Rendern',
        rendering: 'Wird gerendert ({progress}%)',
        
        // Tabs
        tabs: {
            captions: 'Untertitel ({count})',
            styling: 'Stil',
            presets: 'Vorlagen'
        },
        
        // Captions tab
        searchPlaceholder: 'Text durchsuchen...',
        addCaption: '+ Hinzufügen',
        noEntries: 'Noch keine Untertitel vorhanden. Starte die KI-Erkennung oder füge manuell eine Zeile hinzu.',
        transcribeAgain: 'Mit KI neu transkribieren',
        
        // Styling tab
        fontAndText: 'Schriftart & Text',
        fontFamily: 'Schriftart',
        fontSize: 'Schriftgröße',
        fontWeight: 'Schriftstärke',
        weightNormal: 'Normal (400)',
        weightBold: 'Fett (700)',
        weightBlack: 'Extra Fett Black (900)',
        uppercase: 'Alles in GROSSBUCHSTABEN',
        
        colorsAndStroke: 'Farben & Kontur',
        textColor: 'Textfarbe',
        strokeColor: 'Konturfarbe',
        strokeWidth: 'Konturstärke',
        
        backgroundPlate: 'Hintergrundbox',
        enableBackground: 'Hintergrundbox unter Untertiteln aktivieren',
        backgroundColor: 'Hintergrundfarbe',
        opacity: 'Deckkraft',
        
        positioning: 'Positionierung',
        position: 'Position',
        posBottom: 'Unten',
        posMiddle: 'Mitte',
        posTop: 'Oben',
        marginY: 'Vertikaler Abstand (Y)',
        
        karaokeAndAnimation: 'Karaoke & Animation',
        karaokeHighlight: 'Aktives Wort mit Karaoke-Effekt hervorheben',
        badgeColor: 'Farbe des Highlights',
        
        // Preset cards
        presets: {
            viralTag: 'Ideal für Shorts / Reels',
            neonTag: 'Glanz & Musik',
            mrbeastTag: 'Dynamisch & Aufmerksamkeitsstark',
            netflixTag: 'Podcasts & Kino',
            minimalTag: 'Ästhetisch & Schlicht',
            classicTag: 'Klassisches Fernsehen',
            selected: '✓ Ausgewählt',
            applyStyle: 'Stil anwenden'
        },
        
        // Entry card
        card: {
            startTimeTitle: 'Startzeit des Untertitels (00:00:00,000)',
            endTimeTitle: 'Endzeit des Untertitels (00:00:00,000)',
            durationTitle: 'Dauer',
            secShort: 's',
            seek: '▶ Zu dieser Stelle',
            seekTitle: 'Zu dieser Stelle im Video springen',
            deleteTitle: 'Diesen Untertitel löschen',
            placeholder: 'Untertiteltext eingeben...',
            
            // Accents
            accentsTitle: '⚡ Wort-Akzente:',
            accentsHint: 'klicke auf ein Wort für das Karaoke-Highlight',
            removeHighlightTitle: 'Hervorhebung von "{text}" entfernen',
            addHighlightTitle: '"{text}" farbig hervorheben',
            
            // Toolbar
            highlightFragment: 'Auswahl hervorheben',
            highlight: 'Hervorheben',
            highlightFragmentTitle: 'Ausgewählten Textabschnitt mit <h>-Tag hervorheben',
            highlightFirstTitle: 'Erstes Wort hervorheben',
            case: 'Groß-/Kleinschreibung',
            caseTitle: 'Groß- und Kleinschreibung wechseln',
            clear: 'Löschen',
            clearTitle: 'Alle Markierungen aufheben',
            split: 'Teilen',
            splitTitle: 'Diesen Untertitel in zwei Teile aufteilen',
            merge: 'Zusammenfügen',
            mergeTitle: 'Mit dem nächsten Untertitel zusammenfügen',
            
            // Pace badges
            paceOptimal: 'Optimal',
            paceOptimalTitle: '{cps} Z/s • {words} W. — angenehme Lesegeschwindigkeit',
            paceFast: 'Schnell',
            paceFastTitle: '{cps} Z/s • {words} W. — schnelles Sprechtempo',
            paceTooFast: 'Zu schnell',
            paceTooFastTitle: '{cps} Z/s • {words} W. — Zuschauer schaffen es eventuell nicht zu lesen!'
        },
        
        // Timeline
        timeline: {
            singular: 'Untertitel',
            plural: 'Untertitel'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ Untertitel-Vorschau mit Video',
            previous: '◀ Vorheriger',
            next: 'Nächster ▶',
            counter: 'Untertitel {current} von {total}',
            empty: '(leer)',
            tip: '💡 Starte das Video zur Synchronitätsprüfung oder wechsle mit Pfeiltasten.'
        }
    },
    profile: {
        preferencesTitle: 'Einstellungen',
        preferencesDesc: 'Passe die Benutzeroberfläche und deine persönlichen Kontoeinstellungen an',
        languageLabel: 'Oberflächensprache',
        languageDesc: 'Wähle deine bevorzugte Sprache. Änderungen werden sofort im gesamten Studio wirksam.',
        languageActiveBadge: 'Aktiv',
        languageUpdated: 'Spracheinstellung erfolgreich gespeichert!'
    }
}
