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
        newVideo: '新建视频',
        myVideos: '我的视频',
        nextVideo: '下一个视频',
        prevVideo: '上一个视频',
        switchVideo: '切换视频',
        recentVideos: '最近的视频',
        noRecentVideos: '暂无保存的视频',
        searchVideosPlaceholder: '搜索视频...',
        allProjectsInCabinet: '在个人中心查看全部',
        videoCount: '{current} / {total}',
        uploadNextVideo: '上传新文件',
        returnToDropzone: '返回上传',
        autosaveSaving: '保存中...',
        autosaveSaved: '已自动保存',
        downloadSrt: 'SRT',
        downloadSrtTitle: '导出 .SRT 字幕文件',
        downloadVideo: '下载视频 (MP4)',
        exportRender: '导出 / 渲染',
        exportMenu: '导出',
        exportVideo: '带字幕的视频 (MP4)',
        exportVideoDesc: '渲染并下载视频',
        exportVideoReadyDesc: '准备下载',
        exportSrt: '字幕文件 (.SRT)',
        exportSrtDesc: '下载字幕文件',
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
        title: '个人资料',
        subtitle: '管理您的帐户信息',
        avatarAlt: '头像',
        memberSince: '注册时间：{date}',
        editProfile: '✏️ 编辑资料',
        fullName: '全名',
        fullNamePlaceholder: '您的全名',
        company: '公司',
        companyPlaceholder: '您的公司',
        website: '网站',
        websitePlaceholder: 'https://your-website.com',
        bio: '个人简介',
        bioPlaceholder: '介绍一下你自己...',
        cancel: '取消',
        saveChanges: '保存更改',
        saving: '保存中...',
        email: '电子邮箱',
        profileUpdated: '个人资料更新成功！',
        security: '安全设置',
        changePassword: '修改密码',
        changePasswordDesc: '更新您的帐户密码',
        newPassword: '新密码',
        enterNewPassword: '输入新密码',
        confirmPassword: '确认密码',
        confirmNewPassword: '确认新密码',
        updatePassword: '更新密码',
        updating: '更新中...',
        passwordUpdated: '密码更新成功！',
        passwordsDoNotMatch: '两次输入的密码不一致',
        passwordTooShort: '密码长度至少为8个字符',
        preferencesTitle: '偏好设置',
        preferencesDesc: '管理界面语言与个人账户显示配置',
        languageLabel: '界面语言',
        languageDesc: '选择偏好的界面语言，设置将立即生效并保存在您的账户中。',
        languageActiveBadge: '当前生效',
        languageUpdated: '语言偏好设置已成功更新！',
        dangerZone: '危险区域',
        deleteAccount: '注销帐户',
        deleteAccountDesc: '永久删除您的帐户及所有关联数据'
    }
}
