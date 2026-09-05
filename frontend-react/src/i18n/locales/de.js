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
        newVideo: 'Neues Video',
        myVideos: 'Meine Videos',
        nextVideo: 'Nächstes Video',
        prevVideo: 'Vorheriges Video',
        switchVideo: 'Video wechseln',
        recentVideos: 'Deine letzten Videos',
        noRecentVideos: 'Noch keine gespeicherten Videos',
        searchVideosPlaceholder: 'Videos suchen...',
        allProjectsInCabinet: 'Alle im Dashboard öffnen',
        videoCount: '{current} von {total}',
        uploadNextVideo: 'Neue Datei hochladen',
        returnToDropzone: 'Zurück zum Upload',
        autosaveSaving: 'Wird gespeichert...',
        autosaveSaved: 'Gespeichert',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Untertitel im .SRT-Format herunterladen',
        downloadVideo: 'Video herunterladen (MP4)',
        exportRender: 'Exportieren / Rendern',
        exportMenu: 'Exportieren',
        exportVideo: 'Video mit Untertiteln (MP4)',
        exportVideoDesc: 'Video rendern & herunterladen',
        exportVideoReadyDesc: 'Bereit zum Herunterladen',
        exportSrt: 'Untertitel (.SRT)',
        exportSrtDesc: 'Untertiteldatei herunterladen',
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
        title: 'Profil',
        subtitle: 'Verwalte deine Kontoinformationen',
        avatarAlt: 'Avatar',
        memberSince: 'Mitglied seit {date}',
        editProfile: '✏️ Profil bearbeiten',
        fullName: 'Vollständiger Name',
        fullNamePlaceholder: 'Dein vollständiger Name',
        company: 'Unternehmen',
        companyPlaceholder: 'Dein Unternehmen',
        website: 'Webseite',
        websitePlaceholder: 'https://deine-seite.de',
        bio: 'Biografie',
        bioPlaceholder: 'Erzähle uns von dir...',
        cancel: 'Abbrechen',
        saveChanges: 'Änderungen speichern',
        saving: 'Speichern...',
        email: 'E-Mail',
        profileUpdated: 'Profil erfolgreich aktualisiert!',
        security: 'Sicherheit',
        changePassword: 'Passwort ändern',
        changePasswordDesc: 'Aktualisiere dein Kontopasswort',
        newPassword: 'Neues Passwort',
        enterNewPassword: 'Neues Passwort eingeben',
        confirmPassword: 'Passwort bestätigen',
        confirmNewPassword: 'Neues Passwort bestätigen',
        updatePassword: 'Passwort aktualisieren',
        updating: 'Aktualisieren...',
        passwordUpdated: 'Passwort erfolgreich aktualisiert!',
        passwordsDoNotMatch: 'Passwörter stimmen nicht überein',
        passwordTooShort: 'Passwort muss mindestens 8 Zeichen lang sein',
        preferencesTitle: 'Einstellungen',
        preferencesDesc: 'Passe deine Oberflächensprache und App-Einstellungen an',
        languageLabel: 'Oberflächensprache',
        languageDesc: 'Wähle deine bevorzugte Sprache. Änderungen werden sofort angewendet.',
        languageActiveBadge: 'Aktiv',
        languageUpdated: 'Spracheinstellung erfolgreich aktualisiert!',
        dangerZone: 'Gefahrenzone',
        deleteAccount: 'Konto löschen',
        deleteAccountDesc: 'Lösche dein Konto und alle zugehörigen Daten unwiderruflich'
    }
}
