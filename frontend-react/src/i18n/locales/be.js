export default {
    common: {
        save: 'Захаваць',
        saving: 'Захаванне...',
        saved: 'Захавана',
        unsaved: 'Не захавана',
        cancel: 'Адмена',
        delete: 'Выдаліць',
        edit: 'Рэдагаваць',
        close: 'Закрыць',
        loading: 'Загрузка...',
        error: 'Памылка',
        search: 'Пошук...',
        apply: 'Ужыць',
        manageAccount: 'Кіраванне акаўнтам',
    },
    nav: {
        studio: 'Студыя',
        subtitles: 'Субцітры',
        myAccount: 'Мой акаўнт',
        signIn: 'Увайсці',
        login: 'Уваход',
        startFree: 'Пачаць бясплатна',
        openStudio: 'Адкрыць студыю',
        product: 'Прадукт',
        howItWorks: 'Як гэта працуе',
        examples: 'Прыклады',
        pricing: 'Тарыфы',
        faq: 'Пытанні і адказы',
        tagline: 'Генератар музычных відэа на базе AI'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'Стварайце вірусныя субцітры з караоке, анімацыямі і штучным інтэлектам Gemini',
        dropzoneTitle: 'Перацягніце відэа сюды',
        dropzoneSubtitle: 'альбо клікніце для выбару файла (MP4, MOV, WebM)',
        speechLanguage: 'Мова маўлення:',
        langAuto: 'Аўтавызначэнне (AI)',
        langBe: 'Беларуская',
        langEn: 'English',
        langEs: 'Іспанская',
        langZh: 'Кітайская',
        langFr: 'Французская',
        langDe: 'Нямецкая',
        langJa: 'Японская',
        langRu: 'Русский',
        langUk: 'Українська',
        langPl: 'Polski',
        haveSrt: 'У мяне ўжо ёсць .SRT',
        
        // Transcribing screen
        uploadingTitle: 'Загрузка відэа на сервер...',
        transcribingTitle: 'Gemini AI стварае субцітры...',
        uploadingDesc: 'Рыхтуем файл да апрацоўкі і вымаем аўдыядарожку.',
        transcribingDesc: 'Распазнаем кожнае слова, разлічваем таймкоды і прымяняем прэсет караоке.',
        skipToEditor: 'Прапусціць і перайсці ў рэдактар',
        
        // Top bar
        newVideo: 'Новае відэа',
        myVideos: 'Мае відэа',
        nextVideo: 'Наступнае відэа',
        prevVideo: 'Папярэдняе відэа',
        switchVideo: 'Пераключыць відэа',
        recentVideos: 'Вашы нядаўнія відэа',
        noRecentVideos: 'Няма захаваных відэа',
        searchVideosPlaceholder: 'Пошук відэа...',
        allProjectsInCabinet: 'Адкрыць усе ў кабінеце',
        videoCount: '{current} з {total}',
        uploadNextVideo: 'Загрузіць новы файл',
        returnToDropzone: 'Вярнуцца да загрузкі',
        autosaveSaving: 'Захаванне...',
        autosaveSaved: 'Захавана',
        downloadSrt: 'SRT',
        downloadSrtTitle: 'Спампаваць субцітры ў фармаце .SRT',
        downloadVideo: 'Спампаваць відэа (MP4)',
        exportRender: 'Экспарт / Рэндэр',
        exportMenu: 'Экспарт',
        exportVideo: 'Відэа з субцітрамі (MP4)',
        exportVideoDesc: 'Рэндэрынг і спампоўка',
        exportVideoReadyDesc: 'Гатова да спампоўкі',
        exportSrt: 'Субцітры (.SRT)',
        exportSrtDesc: 'Спампаваць файл субцітраў',
        rendering: 'Рэндэрынг ({progress}%)',
        
        // Tabs
        tabs: {
            captions: 'Субцітры ({count})',
            styling: 'Стыль',
            presets: 'Прэсеты'
        },
        
        // Captions tab
        searchPlaceholder: 'Пошук у тэксце...',
        addCaption: '+ Дадаць',
        noEntries: 'Няма субцітраў. Запусціце распазнаванне альбо дадайце радок уручную.',
        transcribeAgain: 'Распазнаць праз AI',
        
        // Styling tab
        fontAndText: 'Шрыфт і тэкст',
        fontFamily: 'Шрыфт',
        fontSize: 'Памер шрыфту',
        fontWeight: 'Тлустасць',
        weightNormal: 'Звычайны (400)',
        weightBold: 'Тлусты (700)',
        weightBlack: 'Звыш-тлусты Black (900)',
        uppercase: 'Усе літары вялікія (UPPERCASE)',
        
        colorsAndStroke: 'Колеры і абводка',
        textColor: 'Колер тэксту',
        strokeColor: 'Колер абводкі',
        strokeWidth: 'Шырыня абводкі',
        
        backgroundPlate: 'Фонавая плашка',
        enableBackground: 'Уключыць фон пад субцітрамі',
        backgroundColor: 'Колер фону',
        opacity: 'Празрыстасць',
        
        positioning: 'Пазіцыянаванне',
        position: 'Пазіцыя',
        posBottom: 'Ніз экрана',
        posMiddle: 'Цэнтр экрана',
        posTop: 'Верх экрана',
        marginY: 'Водступ (Y)',
        
        karaokeAndAnimation: 'Караоке і анімацыя',
        karaokeHighlight: 'Караоке-падсветка актыўнага слова',
        badgeColor: 'Колер бэйджа',
        
        // Preset cards
        presets: {
            viralTag: 'Топ для Shorts / Reels',
            neonTag: 'Ззянне і музыка',
            mrbeastTag: 'Дынаміка і ўвага',
            netflixTag: 'Падкасты і кіно',
            minimalTag: 'Эстэтыка і блогі',
            classicTag: 'Зразумелы тэлевізар',
            selected: '✓ Выбрана',
            applyStyle: 'Ужыць стыль'
        },
        
        // Entry card
        card: {
            startTimeTitle: 'Пачатак субцітра (00:00:00,000)',
            endTimeTitle: 'Канец субцітра (00:00:00,000)',
            durationTitle: 'Працягласць',
            secShort: 'с',
            seek: '▶ Перайсці',
            seekTitle: 'Перайсці да гэтага моманту на відэа',
            deleteTitle: 'Выдаліць гэты субцітр',
            placeholder: 'Увядзіце тэкст субцітра...',
            
            // Accents
            accentsTitle: '⚡ Акцэнты слоў:',
            accentsHint: 'клікніце на слова для караоке-вылучэння',
            removeHighlightTitle: 'Зняць вылучэнне з «{text}»',
            addHighlightTitle: 'Вылучыць «{text}» яркім колерам',
            
            // Toolbar
            highlightFragment: 'Вылучыць фрагмент',
            highlight: 'Вылучыць',
            highlightFragmentTitle: 'Вылучыць выдзелены фрагмент тэгам <h>',
            highlightFirstTitle: 'Вылучыць першае слова',
            case: 'Рэгістр',
            caseTitle: 'Змяніць рэгістр: УСЕ ВЯЛІКІЯ / Як у сказе',
            clear: 'Ачысціць',
            clearTitle: 'Зняць усе вылучэнні',
            split: 'Разбіць',
            splitTitle: 'Разбіць гэты субцітр на два асобныя',
            merge: 'Аб\'яднаць',
            mergeTitle: 'Аб\'яднаць з наступным субцітрам',
            
            // Pace badges
            paceOptimal: 'Звычайна',
            paceOptimalTitle: '{cps} сімв/с • {words} сл. — чытаецца камфортна',
            paceFast: 'Хутка',
            paceFastTitle: '{cps} сімв/с • {words} сл. — хуткі тэмп маўлення',
            paceTooFast: 'Занадта хутка',
            paceTooFastTitle: '{cps} сімв/с • {words} сл. — глядач можа не паспець прачытаць!'
        },
        
        // Timeline
        timeline: {
            singular: 'субцітр',
            few: 'субцітры',
            plural: 'субцітраў'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ Перадпрагляд субцітраў з відэа',
            previous: '◀ Папярэдні',
            next: 'Наступны ▶',
            counter: 'Субцітр {current} з {total}',
            empty: '(пуста)',
            tip: '💡 Запусціце відэа для прагляду сінхранізацыі або пераключайце субцітры стрэлкамі.'
        }
    },
    profile: {
        preferencesTitle: 'Налады',
        preferencesDesc: 'Персаналізацыя мовы інтэрфейсу і параметраў прыкладання',
        languageLabel: 'Мова інтэрфейсу',
        languageDesc: 'Выберыце зручную мову. Змены адразу прымяняюцца ва ўсёй студыі.',
        languageActiveBadge: 'Актыўная',
        languageUpdated: 'Мова паспяхова абноўленая!'
    }
}
