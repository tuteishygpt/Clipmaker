function LandingFooter() {
    const year = new Date().getFullYear()

    return (
        <footer className="landing-footer">
            <div className="landing-footer-inner">
                <div className="footer-grid">
                    <div className="footer-brand">
                        <span className="brand-name">HukFlow</span>
                        <p>Turn music into cinematic visuals with a faster, creator-first workflow.</p>
                        <div className="footer-social">
                            <a
                                className="social-link"
                                href="https://x.com/hukflow"
                                aria-label="HukFlow on X"
                                target="_blank"
                                rel="noreferrer"
                            >
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M18.9 3H22l-7.1 8.1L23 21h-6.4l-5-6.1L6 21H2.9l7.6-8.7L1 3h6.6l4.6 5.6L18.9 3zm-1.1 16h1.8L7.2 5H5.3l12.5 14z" />
                                </svg>
                            </a>
                            <a
                                className="social-link"
                                href="https://www.youtube.com/@hukflow"
                                aria-label="HukFlow on YouTube"
                                target="_blank"
                                rel="noreferrer"
                            >
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M23.5 6.2a3 3 0 0 0-2.1-2.1C19.6 3.6 12 3.6 12 3.6s-7.6 0-9.4.5a3 3 0 0 0-2.1 2.1A31.3 31.3 0 0 0 0 12a31.3 31.3 0 0 0 .5 5.8 3 3 0 0 0 2.1 2.1c1.8.5 9.4.5 9.4.5s7.6 0 9.4-.5a3 3 0 0 0 2.1-2.1A31.3 31.3 0 0 0 24 12a31.3 31.3 0 0 0-.5-5.8zM9.6 15.5V8.5l6.5 3.5-6.5 3.5z" />
                                </svg>
                            </a>
                            <a className="social-link" href="mailto:hello@hukflow.ai" aria-label="Email HukFlow">
                                <svg viewBox="0 0 24 24" aria-hidden="true">
                                    <path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 4.4V18h16V8.4l-8 5-8-5zm8 2.8L20 6H4l8 5.2z" />
                                </svg>
                            </a>
                        </div>
                    </div>

                    <div>
                        <h3>Product</h3>
                        <ul>
                            <li><a href="/studio">Music Video Generator</a></li>
                            <li><a href="/studio">AI Music Generator</a></li>
                            <li><a href="/studio">AI Beat Video Generator</a></li>
                        </ul>
                    </div>

                    <div>
                        <h3>Company</h3>
                        <ul>
                            <li><a href="/pricing">Pricing</a></li>
                            <li><a href="/partners">Partners</a></li>
                            <li><a href="/contact">Contact Us</a></li>
                        </ul>
                    </div>

                    <div>
                        <h3>Legal</h3>
                        <ul>
                            <li><a href="/privacy">Privacy Policy</a></li>
                            <li><a href="/terms">Terms of Service</a></li>
                            <li><a href="/refund">Refund Policy</a></li>
                        </ul>
                    </div>
                </div>

                <div className="footer-bottom">
                    <span>© {year} HukFlow. All rights reserved.</span>
                </div>
            </div>
        </footer>
    )
}

export default LandingFooter
