import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
function Hero({ healthy }) { return <motion.section className="hero" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}><span className="eyebrow"><Sparkles size={14} /> AI-powered decision intelligence</span><h1>See the signal <span className="gradient-text">before the market does.</span></h1><p className="hero-copy">Evaluate startup outcomes with a production-grade machine learning model. Upload a portfolio, inspect the probability, and move from intuition to evidence.</p><div className="status-pill"><span className="status-dot" /> {healthy ? 'Model online and ready to analyze' : 'Connecting to model service'}</div></motion.section> }
export default Hero
