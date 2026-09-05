export default {
    common: {
        save: 'Guardar',
        saving: 'Guardando...',
        saved: 'Guardado',
        unsaved: 'Sin guardar',
        cancel: 'Cancelar',
        delete: 'Eliminar',
        edit: 'Editar',
        close: 'Cerrar',
        loading: 'Cargando...',
        error: 'Error',
        search: 'Buscar...',
        apply: 'Aplicar',
        manageAccount: 'Administrar cuenta',
    },
    nav: {
        studio: 'Estudio',
        subtitles: 'Subtítulos',
        myAccount: 'Mi cuenta',
        signIn: 'Iniciar sesión',
        login: 'Acceso',
        startFree: 'Empezar gratis',
        openStudio: 'Abrir Estudio',
        product: 'Producto',
        howItWorks: 'Cómo funciona',
        examples: 'Ejemplos',
        pricing: 'Precios',
        faq: 'Preguntas frecuentes',
        tagline: 'Generador de videos musicales con IA'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'Crea subtítulos virales con karaoke, animaciones e inteligencia artificial de Gemini',
        dropzoneTitle: 'Arrastra y suelta tu video aquí',
        dropzoneSubtitle: 'o haz clic para explorar archivos (MP4, MOV, WebM)',
        speechLanguage: 'Idioma del audio:',
        langAuto: 'Detección automática (IA)',
        langBe: 'Bielorruso',
        langEn: 'Inglés',
        langEs: 'Español',
        langZh: 'Chino',
        langFr: 'Francés',
        langDe: 'Alemán',
        langJa: 'Japonés',
        langRu: 'Ruso',
        langUk: 'Ucraniano',
        langPl: 'Polaco',
        haveSrt: 'Ya tengo archivo .SRT',
        
        // Transcribing screen
        uploadingTitle: 'Subiendo video al servidor...',
        transcribingTitle: 'Gemini AI está generando los subtítulos...',
        uploadingDesc: 'Preparando el archivo para su procesamiento y extrayendo el audio.',
        transcribingDesc: 'Reconociendo cada palabra, calculando tiempos y aplicando el estilo karaoke.',
        skipToEditor: 'Saltar y abrir el editor',
        
        // Top bar
        autosaveSaving: 'Guardando...',
        autosaveSaved: 'Guardado',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Descargar subtítulos en formato .SRT',
        downloadVideo: 'Descargar video (MP4)',
        exportRender: 'Exportar / Renderizar',
        rendering: 'Renderizando ({progress}%)',
        
        // Tabs
        tabs: {
            captions: 'Subtítulos ({count})',
            styling: 'Estilo',
            presets: 'Estilos rápidos'
        },
        
        // Captions tab
        searchPlaceholder: 'Buscar texto...',
        addCaption: '+ Añadir',
        noEntries: 'Aún no hay subtítulos. Inicia el reconocimiento por IA o agrega una línea manual.',
        transcribeAgain: 'Transcribir con IA',
        
        // Styling tab
        fontAndText: 'Fuente y Texto',
        fontFamily: 'Tipografía',
        fontSize: 'Tamaño de fuente',
        fontWeight: 'Grosor',
        weightNormal: 'Normal (400)',
        weightBold: 'Negrita (700)',
        weightBlack: 'Extra Negrita (900)',
        uppercase: 'Todo en MAYÚSCULAS',
        
        colorsAndStroke: 'Colores y Borde',
        textColor: 'Color del texto',
        strokeColor: 'Color del borde',
        strokeWidth: 'Grosor del borde',
        
        backgroundPlate: 'Fondo de subtítulo',
        enableBackground: 'Activar caja de fondo tras los subtítulos',
        backgroundColor: 'Color de fondo',
        opacity: 'Opacidad',
        
        positioning: 'Posición',
        position: 'Ubicación vertical',
        posBottom: 'Abajo',
        posMiddle: 'Centro',
        posTop: 'Arriba',
        marginY: 'Margen vertical (Y)',
        
        karaokeAndAnimation: 'Karaoke y Animación',
        karaokeHighlight: 'Resaltar palabra activa con efecto karaoke',
        badgeColor: 'Color del resalte',
        
        // Preset cards
        presets: {
            viralTag: 'Ideal para Shorts / Reels',
            neonTag: 'Brillo y Música',
            mrbeastTag: 'Dinámico y Llamativo',
            netflixTag: 'Podcasts y Cine',
            minimalTag: 'Estético y Limpio',
            classicTag: 'Televisión Clásica',
            selected: '✓ Seleccionado',
            applyStyle: 'Aplicar estilo'
        },
        
        // Entry card
        card: {
            startTimeTitle: 'Inicio del subtítulo (00:00:00,000)',
            endTimeTitle: 'Fin del subtítulo (00:00:00,000)',
            durationTitle: 'Duración',
            secShort: 's',
            seek: '▶ Saltar',
            seekTitle: 'Ir a este momento en el video',
            deleteTitle: 'Eliminar este subtítulo',
            placeholder: 'Escribe el texto del subtítulo...',
            
            // Accents
            accentsTitle: '⚡ Acentos de palabras:',
            accentsHint: 'haz clic en una palabra para resaltar en karaoke',
            removeHighlightTitle: 'Quitar resalte de "{text}"',
            addHighlightTitle: 'Resaltar "{text}" con color brillante',
            
            // Toolbar
            highlightFragment: 'Resaltar selección',
            highlight: 'Resaltar',
            highlightFragmentTitle: 'Resaltar fragmento seleccionado con etiqueta <h>',
            highlightFirstTitle: 'Resaltar la primera palabra',
            case: 'Mayúsculas/Minúsculas',
            caseTitle: 'Cambiar mayúsculas y minúsculas',
            clear: 'Limpiar',
            clearTitle: 'Quitar todos los resaltes',
            split: 'Dividir',
            splitTitle: 'Dividir este subtítulo en dos partes',
            merge: 'Unir',
            mergeTitle: 'Unir con el siguiente subtítulo',
            
            // Pace badges
            paceOptimal: 'Óptimo',
            paceOptimalTitle: '{cps} car/s • {words} palabras — ritmo de lectura cómodo',
            paceFast: 'Rápido',
            paceFastTitle: '{cps} car/s • {words} palabras — ritmo de habla rápido',
            paceTooFast: 'Demasiado rápido',
            paceTooFastTitle: '{cps} car/s • {words} palabras — ¡el espectador podría no alcanzar a leer!'
        },
        
        // Timeline
        timeline: {
            singular: 'subtítulo',
            plural: 'subtítulos'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ Vista previa de subtítulos con video',
            previous: '◀ Anterior',
            next: 'Siguiente ▶',
            counter: 'Subtítulo {current} de {total}',
            empty: '(vacío)',
            tip: '💡 Reproduce el video para comprobar sincronización o navega con las flechas.'
        }
    },
    profile: {
        preferencesTitle: 'Preferencias',
        preferencesDesc: 'Personaliza el idioma de la interfaz y la configuración de tu cuenta',
        languageLabel: 'Idioma de la interfaz',
        languageDesc: 'Selecciona tu idioma preferido. Los cambios se aplican al instante en toda la aplicación.',
        languageActiveBadge: 'Activo',
        languageUpdated: '¡Preferencia de idioma guardada!'
    }
}
