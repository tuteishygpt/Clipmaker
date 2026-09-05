export default {
    common: {
        save: 'Enregistrer',
        saving: 'Enregistrement...',
        saved: 'Enregistré',
        unsaved: 'Non enregistré',
        cancel: 'Annuler',
        delete: 'Supprimer',
        edit: 'Modifier',
        close: 'Fermer',
        loading: 'Chargement...',
        error: 'Erreur',
        search: 'Rechercher...',
        apply: 'Appliquer',
        manageAccount: 'Gérer le compte',
    },
    nav: {
        studio: 'Studio',
        subtitles: 'Sous-titres',
        myAccount: 'Mon compte',
        signIn: 'Connexion',
        login: 'Connexion',
        startFree: 'Commencer gratuitement',
        openStudio: 'Ouvrir Studio',
        product: 'Produit',
        howItWorks: 'Comment ça marche',
        examples: 'Exemples',
        pricing: 'Tarifs',
        faq: 'FAQ',
        tagline: 'Générateur de clips musicaux propulsé par l\'IA'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'Créez des sous-titres viraux avec karaoké, animations et l\'IA de Gemini',
        dropzoneTitle: 'Glissez-déposez votre vidéo ici',
        dropzoneSubtitle: 'ou cliquez pour parcourir les fichiers (MP4, MOV, WebM)',
        speechLanguage: 'Langue de la vidéo :',
        langAuto: 'Détection automatique (IA)',
        langBe: 'Biélorusse',
        langEn: 'Anglais',
        langEs: 'Espagnol',
        langZh: 'Chinois',
        langFr: 'Français',
        langDe: 'Allemand',
        langJa: 'Japonais',
        langRu: 'Russe',
        langUk: 'Ukrainien',
        langPl: 'Polonais',
        haveSrt: 'J\'ai déjà un fichier .SRT',
        
        // Transcribing screen
        uploadingTitle: 'Téléversement de la vidéo en cours...',
        transcribingTitle: 'Gemini AI génère les sous-titres...',
        uploadingDesc: 'Préparation du fichier et extraction de la piste audio.',
        transcribingDesc: 'Reconnaissance des mots, calcul des codes temporels et application du style karaoké.',
        skipToEditor: 'Passer et ouvrir l\'éditeur',
        
        // Top bar
        newVideo: 'Nouvelle vidéo',
        myVideos: 'Mes vidéos',
        nextVideo: 'Vidéo suivante',
        prevVideo: 'Vidéo précédente',
        switchVideo: 'Changer de vidéo',
        recentVideos: 'Vos vidéos récentes',
        noRecentVideos: 'Aucune vidéo enregistrée pour le moment',
        searchVideosPlaceholder: 'Rechercher des vidéos...',
        allProjectsInCabinet: 'Tout ouvrir dans l\'espace personnel',
        videoCount: '{current} sur {total}',
        uploadNextVideo: 'Téléverser un nouveau fichier',
        returnToDropzone: 'Retour au téléversement',
        autosaveSaving: 'Enregistrement...',
        autosaveSaved: 'Enregistré',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Télécharger les sous-titres en format .SRT',
        downloadVideo: 'Télécharger la vidéo (MP4)',
        exportRender: 'Exporter / Rendre',
        exportMenu: 'Exporter',
        exportVideo: 'Vidéo avec sous-titres (MP4)',
        exportVideoDesc: 'Rendre et télécharger la vidéo',
        exportVideoReadyDesc: 'Prêt à télécharger',
        exportSrt: 'Sous-titres (.SRT)',
        exportSrtDesc: 'Télécharger le fichier de sous-titres',
        rendering: 'Rendu en cours ({progress}%)',
        
        // Tabs
        tabs: {
            captions: 'Sous-titres ({count})',
            styling: 'Style',
            presets: 'Modèles'
        },
        
        // Captions tab
        searchPlaceholder: 'Rechercher dans le texte...',
        addCaption: '+ Ajouter',
        noEntries: 'Aucun sous-titre pour le moment. Lancez l\'IA ou ajoutez une ligne manuellement.',
        transcribeAgain: 'Transcrire avec l\'IA',
        
        // Styling tab
        fontAndText: 'Police & Texte',
        fontFamily: 'Police',
        fontSize: 'Taille de police',
        fontWeight: 'Graisse',
        weightNormal: 'Normal (400)',
        weightBold: 'Gras (700)',
        weightBlack: 'Extra Gras Black (900)',
        uppercase: 'Tout en MAJUSCULES',
        
        colorsAndStroke: 'Couleurs & Contour',
        textColor: 'Couleur du texte',
        strokeColor: 'Couleur du contour',
        strokeWidth: 'Épaisseur du contour',
        
        backgroundPlate: 'Fond de texte',
        enableBackground: 'Activer le rectangle de fond sous les sous-titres',
        backgroundColor: 'Couleur de fond',
        opacity: 'Opacité',
        
        positioning: 'Positionnement',
        position: 'Position',
        posBottom: 'Bas',
        posMiddle: 'Centre',
        posTop: 'Haut',
        marginY: 'Marge verticale (Y)',
        
        karaokeAndAnimation: 'Karaoké & Animation',
        karaokeHighlight: 'Mise en valeur karaoké du mot actif',
        badgeColor: 'Couleur du surlignage',
        
        // Preset cards
        presets: {
            viralTag: 'Top pour Shorts / Reels',
            neonTag: 'Néon & Musique',
            mrbeastTag: 'Dynamique & Percutant',
            netflixTag: 'Podcasts & Cinéma',
            minimalTag: 'Épuré & Esthétique',
            classicTag: 'Télévision Classique',
            selected: '✓ Sélectionné',
            applyStyle: 'Appliquer le style'
        },
        
        // Entry card
        card: {
            startTimeTitle: 'Début du sous-titre (00:00:00,000)',
            endTimeTitle: 'Fin du sous-titre (00:00:00,000)',
            durationTitle: 'Durée',
            secShort: 's',
            seek: '▶ Aller à',
            seekTitle: 'Se positionner à ce moment dans la vidéo',
            deleteTitle: 'Supprimer ce sous-titre',
            confirmDeleteTitle: 'Supprimer ce sous-titre ?',
            confirmDelete: 'Voulez-vous vraiment supprimer ce sous-titre ?',
            placeholder: 'Saisissez le texte du sous-titre...',
            
            // Accents
            accentsTitle: '⚡ Accents des mots :',
            accentsHint: 'cliquez sur un mot pour le mettre en avant en karaoké',
            removeHighlightTitle: 'Retirer la mise en valeur de "{text}"',
            addHighlightTitle: 'Mettre en valeur "{text}"',
            
            // Toolbar
            highlightFragment: 'Mettre en valeur la sélection',
            highlight: 'Mettre en valeur',
            highlightFragmentTitle: 'Mettre en valeur le fragment sélectionné avec la balise <h>',
            highlightFirstTitle: 'Mettre en valeur le premier mot',
            case: 'Casse',
            caseTitle: 'Changer la casse : MAJUSCULES / Phrase',
            clear: 'Effacer',
            clearTitle: 'Supprimer toutes les mises en valeur',
            split: 'Diviser',
            splitTitle: 'Diviser ce sous-titre en deux parties',
            merge: 'Fusionner',
            mergeTitle: 'Fusionner avec le sous-titre suivant',
            
            // Pace badges
            paceOptimal: 'Optimal',
            paceOptimalTitle: '{cps} car/s • {words} mots — rythme de lecture agréable',
            paceFast: 'Rapide',
            paceFastTitle: '{cps} car/s • {words} mots — débit de parole rapide',
            paceTooFast: 'Trop rapide',
            paceTooFastTitle: '{cps} car/s • {words} mots — le spectateur risque de ne pas avoir le temps de lire !'
        },
        
        // Timeline
        timeline: {
            singular: 'sous-titre',
            plural: 'sous-titres'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ Aperçu des sous-titres avec vidéo',
            previous: '◀ Précédent',
            next: 'Suivant ▶',
            counter: 'Sous-titre {current} sur {total}',
            empty: '(vide)',
            tip: '💡 Lancez la vidéo pour vérifier la synchronisation ou naviguez avec les flèches.'
        }
    },
    profile: {
        title: 'Profil',
        subtitle: 'Gérez les informations de votre compte',
        avatarAlt: 'Avatar',
        memberSince: 'Membre depuis le {date}',
        editProfile: '✏️ Modifier le profil',
        fullName: 'Nom complet',
        fullNamePlaceholder: 'Votre nom complet',
        company: 'Entreprise',
        companyPlaceholder: 'Votre entreprise',
        website: 'Site web',
        websitePlaceholder: 'https://votre-site.com',
        bio: 'Biographie',
        bioPlaceholder: 'Parlez-nous de vous...',
        cancel: 'Annuler',
        saveChanges: 'Enregistrer les modifications',
        saving: 'Enregistrement...',
        email: 'E-mail',
        profileUpdated: 'Profil mis à jour avec succès !',
        security: 'Sécurité',
        changePassword: 'Changer le mot de passe',
        changePasswordDesc: 'Mettez à jour le mot de passe de votre compte',
        newPassword: 'Nouveau mot de passe',
        enterNewPassword: 'Entrez le nouveau mot de passe',
        confirmPassword: 'Confirmer le mot de passe',
        confirmNewPassword: 'Confirmez le nouveau mot de passe',
        updatePassword: 'Mettre à jour le mot de passe',
        updating: 'Mise à jour...',
        passwordUpdated: 'Mot de passe mis à jour avec succès !',
        passwordsDoNotMatch: 'Les mots de passe ne correspondent pas',
        passwordTooShort: 'Le mot de passe doit comporter au moins 8 caractères',
        preferencesTitle: 'Préférences',
        preferencesDesc: 'Personnalisez la langue de votre interface et vos paramètres',
        languageLabel: 'Langue de l\'interface',
        languageDesc: 'Sélectionnez votre langue préférée. Les modifications sont appliquées immédiatement.',
        languageActiveBadge: 'Actif',
        languageUpdated: 'Préférence linguistique mise à jour avec succès !',
        dangerZone: 'Zone dangereuse',
        deleteAccount: 'Supprimer le compte',
        deleteAccountDesc: 'Supprimer définitivement votre compte et toutes les données associées'
    }
}
