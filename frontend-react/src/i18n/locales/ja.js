export default {
    common: {
        save: '保存',
        saving: '保存中...',
        saved: '保存済み',
        unsaved: '未保存',
        cancel: 'キャンセル',
        delete: '削除',
        edit: '編集',
        close: '閉じる',
        loading: '読み込み中...',
        error: 'エラー',
        search: '検索...',
        apply: '適用',
        manageAccount: 'アカウント管理',
    },
    nav: {
        studio: 'スタジオ',
        subtitles: '字幕スタジオ',
        myAccount: 'マイアカウント',
        signIn: 'サインイン',
        login: 'ログイン',
        startFree: '無料で始める',
        openStudio: 'スタジオを開く',
        product: '製品情報',
        howItWorks: '使い方',
        examples: '作例紹介',
        pricing: '料金プラン',
        faq: 'よくある質問',
        tagline: 'AI搭載ミュージックビデオジェネレーター'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: 'カラオケ演出、アニメーション、Gemini AIでバズるショート動画字幕を作成',
        dropzoneTitle: 'ここに動画をドラッグ＆ドロップ',
        dropzoneSubtitle: 'またはクリックして動画ファイルを選択 (MP4, MOV, WebM)',
        speechLanguage: '音声の言語:',
        langAuto: '自動検出 (AI)',
        langBe: 'ベラルーシ語',
        langEn: '英語',
        langEs: 'スペイン語',
        langZh: '中国語',
        langFr: 'フランス語',
        langDe: 'ドイツ語',
        langJa: '日本語',
        langRu: 'ロシア語',
        langUk: 'ウクライナ語',
        langPl: 'ポーランド語',
        haveSrt: '.SRTファイルをお持ちの場合',
        
        // Transcribing screen
        uploadingTitle: '動画をサーバーへアップロード中...',
        transcribingTitle: 'Gemini AIが字幕を生成中...',
        uploadingDesc: '処理の準備と音声トラックの抽出を行っています。',
        transcribingDesc: '単語ごとの認識、タイムコードの算出、カラオケスタイルの適用を行っています。',
        skipToEditor: 'スキップしてエディターへ進む',
        
        // Top bar
        newVideo: '新規ビデオ',
        myVideos: 'マイビデオ',
        nextVideo: '次のビデオ',
        prevVideo: '前のビデオ',
        switchVideo: 'ビデオを切り替える',
        recentVideos: '最近のビデオ',
        noRecentVideos: '保存されたビデオはまだありません',
        searchVideosPlaceholder: 'ビデオを検索...',
        allProjectsInCabinet: 'キャビネットですべて開く',
        videoCount: '{current} / {total}',
        uploadNextVideo: '新しいファイルをアップロード',
        returnToDropzone: 'アップロードに戻る',
        autosaveSaving: '保存中...',
        autosaveSaved: '保存済み',
        downloadSrt: 'SRT',
        downloadSrtTitle: '.SRT形式で字幕をダウンロード',
        downloadVideo: '動画をダウンロード (MP4)',
        exportRender: 'エクスポート / レンダリング',
        exportMenu: 'エクスポート',
        exportVideo: '字幕付きビデオ (MP4)',
        exportVideoDesc: 'レンダリングしてダウンロード',
        exportVideoReadyDesc: 'ダウンロードの準備完了',
        exportSrt: '字幕 (.SRT)',
        exportSrtDesc: '字幕ファイルをダウンロード',
        rendering: 'レンダリング中 ({progress}%)',
        
        // Tabs
        tabs: {
            captions: '字幕一覧 ({count})',
            styling: 'スタイル',
            presets: 'プリセット'
        },
        
        // Captions tab
        searchPlaceholder: '字幕テキストを検索...',
        addCaption: '+ 字幕追加',
        noEntries: '字幕がありません。AI自動認識を開始するか、手動で追加してください。',
        transcribeAgain: 'AIで再認識する',
        
        // Styling tab
        fontAndText: 'フォント＆テキスト',
        fontFamily: 'フォント',
        fontSize: 'フォントサイズ',
        fontWeight: '太さ',
        weightNormal: '標準 (400)',
        weightBold: '太字 (700)',
        weightBlack: '極太 Black (900)',
        uppercase: 'すべて大文字表記 (UPPERCASE)',
        
        colorsAndStroke: 'カラー＆枠線',
        textColor: '文字色',
        strokeColor: '枠線の色',
        strokeWidth: '枠線の太さ',
        
        backgroundPlate: '背景プレート',
        enableBackground: '字幕の下に背景ボックスを表示',
        backgroundColor: '背景色',
        opacity: '不透明度',
        
        positioning: '配置・位置',
        position: '垂直位置',
        posBottom: '画面下部',
        posMiddle: '画面中央',
        posTop: '画面上部',
        marginY: '垂直余白 (Y)',
        
        karaokeAndAnimation: 'カラオケ＆アニメーション',
        karaokeHighlight: '発話中の単語をカラオケ風にハイライト',
        badgeColor: 'ハイライトカラー',
        
        // Preset cards
        presets: {
            viralTag: 'Shorts / TikTok 最適',
            neonTag: 'ネオン＆音楽',
            mrbeastTag: '迫力＆インパクト',
            netflixTag: 'ポッドキャスト＆シネマ',
            minimalTag: 'ミニマル＆スタイリッシュ',
            classicTag: '定番テレビ字幕',
            selected: '✓ 選択中',
            applyStyle: 'スタイルを適用'
        },
        
        // Entry card
        card: {
            startTimeTitle: '字幕開始時間 (00:00:00,000)',
            endTimeTitle: '字幕終了時間 (00:00:00,000)',
            durationTitle: '表示時間',
            secShort: '秒',
            seek: '▶ 再生位置へ',
            seekTitle: '動画のこの位置にシーク',
            deleteTitle: 'この字幕を削除',
            confirmDeleteTitle: '字幕を削除しますか？',
            confirmDelete: 'この字幕を削除してもよろしいですか？',
            placeholder: '字幕テキストを入力...',
            
            // Accents
            accentsTitle: '⚡ 単語アクセント:',
            accentsHint: '単語をクリックしてカラオケハイライトを設定',
            removeHighlightTitle: '「{text}」のハイライトを解除',
            addHighlightTitle: '「{text}」を鮮やかにハイライト',
            
            // Toolbar
            highlightFragment: '選択部分をハイライト',
            highlight: 'ハイライト',
            highlightFragmentTitle: '<h>タグで選択部分をハイライト',
            highlightFirstTitle: '最初の単語をハイライト',
            case: '大文字/小文字',
            caseTitle: '大文字・小文字を切り替え',
            clear: 'クリア',
            clearTitle: 'すべてのハイライトを解除',
            split: '分割',
            splitTitle: 'この字幕を2つに分割',
            merge: '結合',
            mergeTitle: '次の字幕と結合',
            
            // Pace badges
            paceOptimal: '快適',
            paceOptimalTitle: '{cps} 文字/秒 • {words} 単語 — 読みやすいペースです',
            paceFast: 'やや速い',
            paceFastTitle: '{cps} 文字/秒 • {words} 単語 — 話すテンポが速めです',
            paceTooFast: '速すぎる',
            paceTooFastTitle: '{cps} 文字/秒 • {words} 単語 — 視聴者が読みきれない可能性があります！'
        },
        
        // Timeline
        timeline: {
            singular: '件の字幕',
            plural: '件の字幕'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ 動画連動字幕プレビュー',
            previous: '◀ 前へ',
            next: '次へ ▶',
            counter: '字幕 {current} / {total}',
            empty: '(空)',
            tip: '💡 動画を再生して同期を確認するか、矢印ボタンで切り替えてください。'
        }
    },
    profile: {
        title: 'プロフィール',
        subtitle: 'アカウント情報を管理します',
        avatarAlt: 'アバター',
        memberSince: '登録日: {date}',
        editProfile: '✏️ プロフィールを編集',
        fullName: 'フルネーム',
        fullNamePlaceholder: '氏名を入力',
        company: '会社名',
        companyPlaceholder: '会社名を入力',
        website: 'ウェブサイト',
        websitePlaceholder: 'https://example.com',
        bio: '自己紹介',
        bioPlaceholder: '自己紹介を入力してください...',
        cancel: 'キャンセル',
        saveChanges: '変更を保存',
        saving: '保存中...',
        email: 'メールアドレス',
        profileUpdated: 'プロフィールが正常に更新されました！',
        security: 'セキュリティ',
        changePassword: 'パスワードの変更',
        changePasswordDesc: 'アカウントのパスワードを更新します',
        newPassword: '新しいパスワード',
        enterNewPassword: '新しいパスワードを入力',
        confirmPassword: 'パスワードの確認',
        confirmNewPassword: '新しいパスワードを再入力',
        updatePassword: 'パスワードを更新',
        updating: '更新中...',
        passwordUpdated: 'パスワードが正常に更新されました！',
        passwordsDoNotMatch: 'パスワードが一致しません',
        passwordTooShort: 'パスワードは8文字以上である必要があります',
        preferencesTitle: '環境設定',
        preferencesDesc: '表示言語や個人設定をカスタマイズします',
        languageLabel: '表示言語',
        languageDesc: 'ご希望の言語を選択してください。変更はスタジオ全体に即座に反映されます。',
        languageActiveBadge: '有効',
        languageUpdated: '言語設定が正常に更新されました！',
        dangerZone: '危険ゾーン',
        deleteAccount: 'アカウントを削除',
        deleteAccountDesc: 'アカウントおよび関連するすべてのデータを完全に削除します'
    }
}
