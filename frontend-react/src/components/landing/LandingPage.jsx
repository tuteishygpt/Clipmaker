import { useEffect, useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import LandingFooter from './LandingFooter'
import LandingNav from './LandingNav'

const socialProof = [
    'Independent artists',
    'Beatmakers',
    'Labels & collectives',
    'Creative studios'
]

const features = [
    {
        title: 'Audio-first generation',
        description: 'Upload a track and let HukFlow map beats and energy to visual scenes.',
        icon: '🎵'
    },
    {
        title: 'Scene-by-scene control',
        description: 'Adjust, reorder, and fine-tune every generated moment in one timeline.',
        icon: '🎬'
    },
    {
        title: 'Visual consistency tools',
        description: 'Keep a cohesive look across your video with style and motion settings.',
        icon: '🎨'
    },
    {
        title: 'Fast previews',
        description: 'Iterate quickly with previews that keep you in the creative flow.',
        icon: '⚡'
    }
]

const autoFeatures = [
    {
        title: 'Music-to-Video in Minutes',
        description: 'Upload a track and get a finished video fast.',
        icon: '⚡'
    },
    {
        title: 'Beat-Synced AI Visuals',
        description: 'Cuts and transitions follow beats, drops, and choruses.',
        icon: '🎛️'
    },
    {
        title: 'Social Formats Ready',
        description: 'Export 16:9, 9:16, and 1:1 for YouTube/TikTok/Reels.',
        icon: '📐'
    },
    {
        title: 'Release Promo Pack',
        description: '15/30/60s teasers plus an animated cover option.',
        icon: '🚀'
    },
    {
        title: 'Lyric Video (Optional)',
        description: 'Add lyrics to get timed on-screen lines.',
        icon: '🎤'
    },
    {
        title: 'Style Presets',
        description: 'Cinematic, lo-fi, neon, fantasy, abstract, and more.',
        icon: '🎨'
    },
    {
        title: 'VJ Loops for Live Shows',
        description: 'Loopable visuals for sets and stage screens.',
        icon: '🔁'
    },
    {
        title: 'Brand Controls',
        description: 'Colors, logo, watermark for labels and brands.',
        icon: '🏷️'
    },
    {
        title: 'HD / 4K Export',
        description: 'High-quality renders ready to publish.',
        icon: '🖥️'
    }
]

const steps = [
    {
        title: 'Upload your audio',
        description: 'Drop in a track and let HukFlow analyze structure and tempo.',
        icon: '📤'
    },
    {
        title: 'Generate and refine',
        description: 'Choose a visual direction, then tweak scenes to match your sound.',
        icon: '✨'
    },
    {
        title: 'Export when ready',
        description: 'Lock in your final cut and deliver a ready-to-share video.',
        icon: '🎬'
    }
]

const faqs = [
    {
        question: 'What do free credits include?',
        answer: 'Free credits let you test the core workflow, generate previews, and explore scene editing before upgrading.'
    },
    {
        question: 'Do I need to install anything?',
        answer: 'No. HukFlow runs in the browser so you can start creating right away.'
    },
    {
        question: 'Can I edit the generated scenes?',
        answer: 'Yes. You can adjust timing, reorder scenes, and refine the visuals before exporting.'
    },
    {
        question: 'What video formats are supported?',
        answer: 'We support vertical (9:16), horizontal (16:9), and square (1:1) formats for all major social platforms.'
    },
    {
        question: 'How long does video generation take?',
        answer: 'Most videos are generated in under 5 minutes, depending on length and complexity.'
    }
]

// Fallback examples if API fails 
const fallbackExamples = [
    {
        id: 'demo-1',
        title: 'Neon Pulse',
        format: '9:16',
        style: 'cinematic',
        gradient: 'linear-gradient(135deg, rgba(99,102,241,0.9), rgba(139,92,246,0.7))'
    },
    {
        id: 'demo-2',
        title: 'Midnight Drift',
        format: '16:9',
        style: 'cinematic',
        gradient: 'linear-gradient(135deg, rgba(14,165,233,0.9), rgba(56,189,248,0.7))'
    },
    {
        id: 'demo-3',
        title: 'Analog Bloom',
        format: '9:16',
        style: 'lo-fi',
        gradient: 'linear-gradient(135deg, rgba(244,63,94,0.9), rgba(251,113,133,0.7))'
    },
    {
        id: 'demo-4',
        title: 'Velvet Echo',
        format: '1:1',
        style: 'abstract',
        gradient: 'linear-gradient(135deg, rgba(16,185,129,0.9), rgba(52,211,153,0.7))'
    }
]

function VideoShowcaseCard({ item, isPlaying, onPlay, onPause }) {
    const videoRef = useRef(null)
    const [isLoaded, setIsLoaded] = useState(false)
    const [hasError, setHasError] = useState(false)

    const isVertical = item.format === '9:16'
    const isSquare = item.format === '1:1'

    useEffect(() => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.play().catch(() => setHasError(true))
            } else {
                videoRef.current.pause()
            }
        }
    }, [isPlaying])

    const formatLabel = isVertical ? 'Vertical' : isSquare ? 'Square' : 'Horizontal'

    return (
        <article
            className={`showcase-card ${isVertical ? 'vertical' : isSquare ? 'square' : 'horizontal'} ${isPlaying ? 'playing' : ''}`}
            onMouseEnter={onPlay}
            onMouseLeave={onPause}
        >
            <div className="showcase-media">
                {item.video_url && !hasError ? (
                    <>
                        <video
                            ref={videoRef}
                            src={item.video_url}
                            muted
                            loop
                            playsInline
                            preload="metadata"
                            onLoadedData={() => setIsLoaded(true)}
                            onError={() => setHasError(true)}
                            className={isLoaded ? 'loaded' : ''}
                        />
                        {!isLoaded && (
                            <div className="showcase-placeholder" style={{ backgroundImage: item.gradient }}>
                                <div className="showcase-loader">
                                    <span className="loader-ring"></span>
                                </div>
                            </div>
                        )}
                    </>
                ) : (
                    <div className="showcase-placeholder" style={{ backgroundImage: item.gradient || 'linear-gradient(135deg, rgba(99,102,241,0.9), rgba(139,92,246,0.7))' }}>
                        <span className="showcase-icon">▶</span>
                    </div>
                )}
                <div className="showcase-overlay">
                    <span className="showcase-play-icon">{isPlaying ? '⏸' : '▶'}</span>
                </div>
                <div className="showcase-badge">
                    <span className="badge-format">{formatLabel}</span>
                    <span className="badge-style">{item.style}</span>
                </div>
            </div>
            <div className="showcase-info">
                <h4 className="showcase-title">{item.title}</h4>
                <p className="showcase-format-label">{item.format}</p>
            </div>
        </article>
    )
}

function LandingPage() {
    const [activeFaq, setActiveFaq] = useState(-1)
    const [showcaseItems, setShowcaseItems] = useState([])
    const [loadingShowcase, setLoadingShowcase] = useState(true)
    const [playingVideo, setPlayingVideo] = useState(null)
    const heroVideoRef = useRef(null)

    useEffect(() => {
        document.body.classList.add('landing-body')
        return () => document.body.classList.remove('landing-body')
    }, [])

    // Fetch showcase videos from API
    useEffect(() => {
        async function fetchShowcase() {
            try {
                const response = await fetch('/api/showcase')
                if (response.ok) {
                    const data = await response.json()
                    if (data.length > 0) {
                        setShowcaseItems(data)
                    } else {
                        setShowcaseItems(fallbackExamples)
                    }
                } else {
                    setShowcaseItems(fallbackExamples)
                }
            } catch (error) {
                console.error('Failed to fetch showcase:', error)
                setShowcaseItems(fallbackExamples)
            } finally {
                setLoadingShowcase(false)
            }
        }
        fetchShowcase()
    }, [])

    return (
        <div className="landing-page">
            <LandingNav />

            <main className="landing-main">
                {/* Hero Section - Enhanced */}
                <section className="landing-hero">
                    <div className="hero-bg-effects">
                        <div className="hero-glow hero-glow-1"></div>
                        <div className="hero-glow hero-glow-2"></div>
                        <div className="hero-grid-pattern"></div>
                    </div>
                    <div className="container hero-grid">
                        <div className="hero-copy">
                            <div className="hero-badge">
                                <span className="badge-dot"></span>
                                <span>AI Music Video Generator</span>
                            </div>
                            <h1>
                                <span className="hero-title-line">Make your music</span>
                                <span className="hero-title-gradient">visible</span>
                            </h1>
                            <p className="hero-subtitle">
                                Transform your audio into stunning music videos with AI-powered visuals,
                                beat-synced transitions, and professional-grade output — all in minutes.
                            </p>
                            <div className="hero-actions">
                                <Link className="btn btn-primary btn-glow" to="/auth">
                                    <span>Start free</span>
                                    <span className="btn-arrow">→</span>
                                </Link>
                                <a className="btn btn-glass" href="#examples">
                                    <span className="btn-play-icon">▶</span>
                                    <span>Watch examples</span>
                                </a>
                            </div>
                            <div className="hero-stats">
                                <div className="stat-item">
                                    <span className="stat-number">500+</span>
                                    <span className="stat-label">Videos created</span>
                                </div>
                                <div className="stat-divider"></div>
                                <div className="stat-item">
                                    <span className="stat-number">&lt;5min</span>
                                    <span className="stat-label">Generation time</span>
                                </div>
                                <div className="stat-divider"></div>
                                <div className="stat-item">
                                    <span className="stat-number">3</span>
                                    <span className="stat-label">Video formats</span>
                                </div>
                            </div>
                        </div>
                        <div className="hero-visual" aria-hidden="true">
                            <div className="hero-phone-mockup">
                                <div className="phone-notch"></div>
                                <div className="phone-screen">
                                    {showcaseItems.length > 0 && showcaseItems[0].video_url ? (
                                        <video
                                            ref={heroVideoRef}
                                            src={showcaseItems[0].video_url}
                                            autoPlay
                                            muted
                                            loop
                                            playsInline
                                            className="hero-video"
                                        />
                                    ) : (
                                        <div className="hero-wave-container">
                                            <div className="hero-wave"></div>
                                            <div className="hero-wave hero-wave-2"></div>
                                            <div className="hero-wave hero-wave-3"></div>
                                        </div>
                                    )}
                                </div>
                                <div className="phone-controls">
                                    <div className="control-dot"></div>
                                    <div className="control-line"></div>
                                </div>
                            </div>
                            <div className="hero-floating-cards">
                                <div className="floating-card card-1">
                                    <span className="card-icon">🎵</span>
                                    <span>Beat detected</span>
                                </div>
                                <div className="floating-card card-2">
                                    <span className="card-icon">✨</span>
                                    <span>Scene generated</span>
                                </div>
                                <div className="floating-card card-3">
                                    <span className="card-icon">🎬</span>
                                    <span>Ready to export</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Social Proof */}
                <section className="landing-section section-trusted" id="social-proof">
                    <div className="container">
                        <p className="trusted-label">Trusted by creators worldwide</p>
                        <div className="social-proof">
                            {socialProof.map((item) => (
                                <div key={item} className="social-proof-card">
                                    <span className="proof-icon">✓</span>
                                    {item}
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Video Examples Gallery */}
                <section className="landing-section section-examples" id="examples">
                    <div className="container">
                        <div className="section-header section-header-center">
                            <span className="section-eyebrow">Gallery</span>
                            <h2>See what's possible</h2>
                            <p>Real videos created with HukFlow. Hover to preview.</p>
                        </div>

                        {loadingShowcase ? (
                            <div className="showcase-loading">
                                <div className="showcase-loader">
                                    <span className="loader-ring"></span>
                                </div>
                                <p>Loading examples...</p>
                            </div>
                        ) : (
                            <div className="showcase-grid" role="list">
                                {showcaseItems.map((item, index) => (
                                    <VideoShowcaseCard
                                        key={item.id}
                                        item={item}
                                        isPlaying={playingVideo === item.id}
                                        onPlay={() => setPlayingVideo(item.id)}
                                        onPause={() => setPlayingVideo(null)}
                                    />
                                ))}
                            </div>
                        )}

                        <div className="examples-cta">
                            <Link className="btn btn-primary" to="/auth">Create your first video</Link>
                        </div>
                    </div>
                </section>

                {/* Auto Features */}
                <section className="landing-section section-features-dark" id="auto-features">
                    <div className="container">
                        <div className="section-header section-header-center">
                            <span className="section-eyebrow">Features</span>
                            <h2>Turn your music into video — automatically</h2>
                            <p>
                                Upload an audio file and we generate visuals synced to rhythm and mood, then render a
                                ready-to-post video.
                            </p>
                        </div>
                        <div className="auto-feature-grid">
                            {autoFeatures.map((feature) => (
                                <article key={feature.title} className="auto-feature-card">
                                    <span className="feature-icon" aria-hidden="true">{feature.icon}</span>
                                    <div>
                                        <h3>{feature.title}</h3>
                                        <p>{feature.description}</p>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                {/* How It Works */}
                <section className="landing-section section-how" id="how-it-works">
                    <div className="container">
                        <div className="section-header section-header-center">
                            <span className="section-eyebrow">How It Works</span>
                            <h2>From audio to video in 3 steps</h2>
                            <p>Simple workflow, professional results.</p>
                        </div>
                        <div className="steps-grid">
                            {steps.map((step, index) => (
                                <article key={step.title} className="step-card">
                                    <div className="step-header">
                                        <span className="step-index">0{index + 1}</span>
                                        <span className="step-icon">{step.icon}</span>
                                    </div>
                                    <div>
                                        <h3>{step.title}</h3>
                                        <p>{step.description}</p>
                                    </div>
                                    {index < steps.length - 1 && <div className="step-connector"></div>}
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Features Grid */}
                <section className="landing-section" id="features">
                    <div className="container">
                        <div className="section-header section-header-center">
                            <span className="section-eyebrow">Why HukFlow</span>
                            <h2>Everything you need to go from track to video</h2>
                            <p>Stay in control with tools built for fast iteration and polished output.</p>
                        </div>
                        <div className="feature-grid">
                            {features.map((feature) => (
                                <article key={feature.title} className="feature-card">
                                    <span className="feature-card-icon">{feature.icon}</span>
                                    <h3>{feature.title}</h3>
                                    <p>{feature.description}</p>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Pricing */}
                <section className="landing-section section-pricing" id="pricing">
                    <div className="container">
                        <div className="pricing-card">
                            <div className="pricing-content">
                                <span className="pricing-badge">Flexible pricing</span>
                                <h2>Start free, scale as you grow</h2>
                                <p>Begin with free credits, then upgrade when you're ready to ship more videos.</p>
                            </div>
                            <Link className="btn btn-primary btn-lg" to="/pricing">
                                View plans
                                <span className="btn-arrow">→</span>
                            </Link>
                        </div>
                    </div>
                </section>

                {/* FAQ */}
                <section className="landing-section" id="faq">
                    <div className="container">
                        <div className="section-header section-header-center">
                            <span className="section-eyebrow">FAQ</span>
                            <h2>Frequently asked questions</h2>
                            <p>Quick answers to get you started.</p>
                        </div>
                        <div className="faq-list">
                            {faqs.map((faq, index) => (
                                <div key={faq.question} className={`faq-item ${activeFaq === index ? 'open' : ''}`}>
                                    <button
                                        className="faq-question"
                                        type="button"
                                        aria-expanded={activeFaq === index}
                                        aria-controls={`faq-panel-${index}`}
                                        onClick={() => setActiveFaq(activeFaq === index ? -1 : index)}
                                    >
                                        <span>{faq.question}</span>
                                        <span className="faq-icon" aria-hidden="true">
                                            {activeFaq === index ? '−' : '+'}
                                        </span>
                                    </button>
                                    <div
                                        id={`faq-panel-${index}`}
                                        className={`faq-answer ${activeFaq === index ? 'open' : ''}`}
                                        role="region"
                                    >
                                        <p>{faq.answer}</p>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                {/* CTA */}
                <section className="landing-cta">
                    <div className="container">
                        <div className="cta-inner">
                            <div className="cta-content">
                                <h2>Ready to make your music visible?</h2>
                                <p>Start free, explore the workflow, and publish your first video today.</p>
                            </div>
                            <div className="cta-actions">
                                <Link className="btn btn-primary btn-lg btn-glow" to="/auth">
                                    Start creating
                                    <span className="btn-arrow">→</span>
                                </Link>
                                <Link className="btn btn-glass" to="/studio">Open studio</Link>
                            </div>
                        </div>
                    </div>
                </section>
            </main>

            <LandingFooter />
        </div>
    )
}

export default LandingPage
