export default {
    common: {
        save: '保存',
        saving: '保存中...',
        saved: '已保存',
        unsaved: '未保存',
        cancel: '取消',
        delete: '删除',
        edit: '编辑',
        close: '关闭',
        loading: '加载中...',
        error: '错误',
        search: '搜索...',
        apply: '应用',
        manageAccount: '管理账户',
    },
    nav: {
        studio: '工作室',
        subtitles: '字幕工具',
        myAccount: '我的账户',
        signIn: '登录',
        login: '登录',
        startFree: '免费开始',
        openStudio: '进入工作室',
        product: '产品介绍',
        howItWorks: '工作原理',
        examples: '案例展示',
        pricing: '价格方案',
        faq: '常见问题',
        tagline: 'AI 驱动的音乐视频生成平台'
    },
    subtitles: {
        title: 'Subtitle Studio',
        heroTitle: 'Subtitle Studio',
        heroSubtitle: '借助 Gemini AI、卡拉OK动态与动画效果，打造火爆短视频字幕',
        dropzoneTitle: '将视频拖放至此处',
        dropzoneSubtitle: '或点击选择视频文件 (MP4, MOV, WebM)',
        speechLanguage: '音频语言:',
        langAuto: '自动识别 (AI)',
        langBe: '白俄罗斯语',
        langEn: '英语',
        langEs: '西班牙语',
        langZh: '中文 (简体)',
        langFr: '法语',
        langDe: '德语',
        langJa: '日语',
        langRu: '俄语',
        langUk: '乌克兰语',
        langPl: '波兰语',
        haveSrt: '已有 .SRT 字幕文件',
        
        // Transcribing screen
        uploadingTitle: '正在上传视频至服务器...',
        transcribingTitle: 'Gemini AI 正在生成字幕...',
        uploadingDesc: '准备处理文件并提取音频轨道。',
        transcribingDesc: '正在精确识别每个词、计算时间轴并应用卡拉OK高亮预设。',
        skipToEditor: '跳过并直接进入编辑器',
        
        // Top bar
        autosaveSaving: '保存中...',
        autosaveSaved: '已自动保存',
        downloadSrt: 'SRT',
        downloadSrtTitle: '导出 .SRT 字幕文件',
        downloadVideo: '下载视频 (MP4)',
        exportRender: '导出 / 渲染',
        rendering: '渲染中 ({progress}%)',
        
        // Tabs
        tabs: {
            captions: '字幕列表 ({count})',
            styling: '样式外观',
            presets: '预设模板'
        },
        
        // Captions tab
        searchPlaceholder: '搜索字幕内容...',
        addCaption: '+ 添加字幕',
        noEntries: '暂无字幕。请启动 AI 识别或手动添加行。',
        transcribeAgain: '使用 AI 重新转录',
        
        // Styling tab
        fontAndText: '字体与排版',
        fontFamily: '字体',
        fontSize: '字号大小',
        fontWeight: '字重粗细',
        weightNormal: '常规 (400)',
        weightBold: '粗体 (700)',
        weightBlack: '特粗 Black (900)',
        uppercase: '全部大写 (UPPERCASE)',
        
        colorsAndStroke: '文字颜色与描边',
        textColor: '文字颜色',
        strokeColor: '描边颜色',
        strokeWidth: '描边粗细',
        
        backgroundPlate: '背景底色块',
        enableBackground: '开启字幕背景衬底',
        backgroundColor: '背景颜色',
        opacity: '不透明度',
        
        positioning: '位置与边距',
        position: '垂直位置',
        posBottom: '底部',
        posMiddle: '居中',
        posTop: '顶部',
        marginY: '垂直边距 (Y)',
        
        karaokeAndAnimation: '卡拉OK与动画',
        karaokeHighlight: '卡拉OK当前词高亮发光',
        badgeColor: '高亮标记颜色',
        
        // Preset cards
        presets: {
            viralTag: 'Shorts / TikTok 热门',
            neonTag: '霓虹音乐潮流',
            mrbeastTag: '醒目动感强力',
            netflixTag: '播客与电影质感',
            minimalTag: '极简美学清新',
            classicTag: '经典电视字幕',
            selected: '✓ 已选择',
            applyStyle: '应用此样式'
        },
        
        // Entry card
        card: {
            startTimeTitle: '字幕起始时间 (00:00:00,000)',
            endTimeTitle: '字幕结束时间 (00:00:00,000)',
            durationTitle: '时长',
            secShort: '秒',
            seek: '▶ 定位',
            seekTitle: '跳转到视频该时刻',
            deleteTitle: '删除此字幕',
            placeholder: '输入字幕文本...',
            
            // Accents
            accentsTitle: '⚡ 词重点标注:',
            accentsHint: '点击词块可快速设置卡拉OK高亮',
            removeHighlightTitle: '取消「{text}」的高亮',
            addHighlightTitle: '高亮突出「{text}」',
            
            // Toolbar
            highlightFragment: '高亮所选片段',
            highlight: '高亮词',
            highlightFragmentTitle: '使用 <h> 标签高亮选中的片段',
            highlightFirstTitle: '高亮首个词',
            case: '大小写',
            caseTitle: '切换大小写格式',
            clear: '清除',
            clearTitle: '清除所有高亮标记',
            split: '拆分',
            splitTitle: '将当前字幕拆分为两段',
            merge: '合并',
            mergeTitle: '与下一条字幕合并',
            
            // Pace badges
            paceOptimal: '适中',
            paceOptimalTitle: '{cps} 字符/秒 • {words} 词 — 阅读速度舒适',
            paceFast: '偏快',
            paceFastTitle: '{cps} 字符/秒 • {words} 词 — 语速较快',
            paceTooFast: '过快',
            paceTooFastTitle: '{cps} 字符/秒 • {words} 词 — 观众可能来不及阅读！'
        },
        
        // Timeline
        timeline: {
            singular: '条字幕',
            plural: '条字幕'
        },
        
        // Editor modal preview
        previewNav: {
            badgeText: '👁️ 实时视频字幕预览',
            previous: '◀ 上一条',
            next: '下一条 ▶',
            counter: '字幕 {current} / {total}',
            empty: '(空)',
            tip: '💡 播放视频即可预览同步效果，或使用左右箭头切换字幕。'
        }
    },
    profile: {
        preferencesTitle: '偏好设置',
        preferencesDesc: '管理界面语言与个人账户显示配置',
        languageLabel: '界面语言',
        languageDesc: '选择偏好的界面语言，设置将立即生效并保存在您的账户中。',
        languageActiveBadge: '当前语言',
        languageUpdated: '语言偏好设置已成功更新！'
    }
}
