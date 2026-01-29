import { useEffect, useState } from 'react'
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
        description: 'Upload a track and let HukFlow map beats and energy to visual scenes.'
    },
    {
        title: 'Scene-by-scene control',
        description: 'Adjust, reorder, and fine-tune every generated moment in one timeline.'
    },
    {
        title: 'Visual consistency tools',
        description: 'Keep a cohesive look across your video with style and motion settings.'
    },
    {
        title: 'Fast previews',
        description: 'Iterate quickly with previews that keep you in the creative flow.'
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
        description: 'Drop in a track and let HukFlow analyze structure and tempo.'
    },
    {
        title: 'Generate and refine',
        description: 'Choose a visual direction, then tweak scenes to match your sound.'
    },
    {
        title: 'Export when ready',
        description: 'Lock in your final cut and deliver a ready-to-share video.'
    }
]

const exampleItems = [
    {
        id: 'ex-1',
        title: 'Neon Pulse',
        nickname: '@creator1', // TODO: Replace with real creator nickname.
        orientation: 'horizontal',
        gradient: 'linear-gradient(135deg, rgba(99,102,241,0.9), rgba(139,92,246,0.7))'
    },
    {
        id: 'ex-2',
        title: 'Midnight Drift',
        nickname: '@creator2', // TODO: Replace with real creator nickname.
        orientation: 'vertical',
        gradient: 'linear-gradient(135deg, rgba(14,165,233,0.9), rgba(56,189,248,0.7))'
    },
    {
        id: 'ex-3',
        title: 'Analog Bloom',
        nickname: '@creator3', // TODO: Replace with real creator nickname.
        orientation: 'horizontal',
        gradient: 'linear-gradient(135deg, rgba(244,63,94,0.9), rgba(251,113,133,0.7))'
    },
    {
        id: 'ex-4',
        title: 'Velvet Echo',
        nickname: '@creator4', // TODO: Replace with real creator nickname.
        orientation: 'vertical',
        gradient: 'linear-gradient(135deg, rgba(16,185,129,0.9), rgba(52,211,153,0.7))'
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
    }
]

function LandingPage() {
    const [activeFaq, setActiveFaq] = useState(0)

    useEffect(() => {
        document.body.classList.add('landing-body')
        return () => document.body.classList.remove('landing-body')
    }, [])

    return (
        <div className="landing-page">
            <LandingNav />

            <main className="landing-main">
                <section className="landing-hero">
                    <div className="container hero-grid">
                        <div className="hero-copy">
                            <p className="eyebrow">AI music visualizer</p>
                            <h1>HukFlow — Make music visible.</h1>
                            <p className="hero-subtitle">
                                Build striking music videos from your audio with a streamlined, creator-first workflow.
                            </p>
                            <div className="hero-actions">
                                <a className="btn btn-primary" href="/auth">Start free</a>
                                <a className="btn btn-secondary" href="#examples">See examples</a>
                            </div>
                            <p className="hero-note">Start free with included credits — no card required.</p>
                        </div>
                        <div className="hero-visual" aria-hidden="true">
                            <div className="hero-card">
                                <div className="hero-card-top">
                                    <span className="pill">New scene</span>
                                    <span className="pill muted">Preview</span>
                                </div>
                                <div className="hero-card-media">
                                    <div className="hero-wave" />
                                </div>
                                <div className="hero-card-bottom">
                                    <span>Energy peaks</span>
                                    <span className="status">Ready</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="social-proof">
                    <div className="container">
                        <div className="section-header">
                            <h2>Trusted by teams shaping new sounds</h2>
                            <p>Replace with real partner logos when available.</p>
                        </div>
                        <div className="social-proof">
                            {socialProof.map((item) => (
                                <div key={item} className="social-proof-card">
                                    {item}
                                </div>
                            ))}
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="auto-features">
                    <div className="container">
                        <div className="section-header">
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
                        <div className="auto-feature-cta">
                            <a className="btn btn-primary" href="/studio">Upload a track</a>
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="features">
                    <div className="container">
                        <div className="section-header">
                            <h2>Everything you need to go from track to video</h2>
                            <p>Stay in control with tools built for fast iteration and polished output.</p>
                        </div>
                        <div className="feature-grid">
                            {features.map((feature) => (
                                <article key={feature.title} className="feature-card">
                                    <h3>{feature.title}</h3>
                                    <p>{feature.description}</p>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="how-it-works">
                    <div className="container">
                        <div className="section-header">
                            <h2>How HukFlow works</h2>
                            <p>Three steps to go from audio to a share-ready music video.</p>
                        </div>
                        <div className="steps-grid">
                            {steps.map((step, index) => (
                                <article key={step.title} className="step-card">
                                    <span className="step-index">0{index + 1}</span>
                                    <div>
                                        <h3>{step.title}</h3>
                                        <p>{step.description}</p>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="examples">
                    <div className="container">
                        <div className="section-header">
                            <h2>Examples from the community</h2>
                            <p>Explore mixed formats in one continuous row.</p>
                        </div>
                        <div className="examples-row" role="list">
                            {exampleItems.map((example) => (
                                <article
                                    key={example.id}
                                    className={`example-card ${example.orientation}`}
                                    role="listitem"
                                >
                                    <div
                                        className="example-media"
                                        style={{ backgroundImage: example.gradient }}
                                        role="img"
                                        aria-label={`${example.title} by ${example.nickname}`}
                                    >
                                        <span className="example-tag">{example.title}</span>
                                    </div>
                                    <div className="example-meta">
                                        <span>by {example.nickname}</span>
                                        <span className="example-format">{example.orientation === 'vertical' ? 'Vertical' : 'Horizontal'}</span>
                                    </div>
                                </article>
                            ))}
                        </div>
                    </div>
                </section>

                <section className="landing-section" id="pricing">
                    <div className="container pricing-card">
                        <div>
                            <h2>Flexible plans as you grow</h2>
                            <p>Start with free credits, then scale when you are ready to ship more videos.</p>
                        </div>
                        <a className="btn btn-primary" href="/pricing">View pricing</a>
                    </div>
                </section>

                <section className="landing-section" id="faq">
                    <div className="container">
                        <div className="section-header">
                            <h2>Frequently asked questions</h2>
                            <p>Short answers to help you get started quickly.</p>
                        </div>
                        <div className="faq-list">
                            {faqs.map((faq, index) => (
                                <div key={faq.question} className="faq-item">
                                    <button
                                        className="faq-question"
                                        type="button"
                                        aria-expanded={activeFaq === index}
                                        aria-controls={`faq-panel-${index}`}
                                        onClick={() => setActiveFaq(activeFaq === index ? -1 : index)}
                                    >
                                        <span>{faq.question}</span>
                                        <span className="faq-icon" aria-hidden="true">+</span>
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

                <section className="landing-cta">
                    <div className="container cta-inner">
                        <div>
                            <h2>Ready to make your next release visual?</h2>
                            <p>Start free, explore the workflow, and share your first preview today.</p>
                        </div>
                        <div className="cta-actions">
                            <a className="btn btn-primary" href="/auth">Start free</a>
                            <a className="btn btn-secondary" href="/studio">Open studio</a>
                        </div>
                    </div>
                </section>
            </main>

            <LandingFooter />
        </div>
    )
}

export default LandingPage
