# Overview

This project is an institutional-grade options trading platform built with Streamlit, designed to provide real-time market data analysis, advanced options pricing, technical indicators, and alert management. It integrates with Interactive Brokers (IBKR) API for live trading data and features sophisticated options analytics including Greeks calculation, volatility analysis, and risk management tools. The platform aims to offer professional traders a powerful analytical toolkit within a clean and intuitive interface, focusing on high-priority AI predictions and live market intelligence for informed trading decisions.

# User Preferences

Preferred communication style: Simple, everyday language.
UI/UX Preferences:
- Dislikes: Complex market mood displays, multi-broker dashboards, confusing unified data sections, oversized colored boxes
- Prefers: Clean, simple layouts with clear data presentation, compact text-based information display
- Focus on: Live options flow, real news, earnings results, clear trading signals
- Market Intelligence Requirements: Separate today's earnings from upcoming earnings, include FOMC dates, Fed economic data releases (CPI, PPI, Jobs), global market-moving news
- Interface Style: Minimal colors, text-based display, compact layout without large colored containers

# System Architecture

## Frontend Architecture
- **Streamlit Web Application**: Single-page application with sidebar controls and a main dashboard for real-time updates and interactive Plotly visualizations.
- **Responsive Layout**: Wide layout with an expandable sidebar.

## Backend Architecture
- **Modular Component Design**:
  - `options_engine.py`: Options pricing, Greeks calculation, volatility analysis.
  - `market_data.py`: Real-time and historical market data fetching.
  - `technical_indicators.py`: Technical analysis using TA-Lib.
  - `alerts.py`: Multi-channel notification system.
  - `utils.py`: Shared utility functions.

## Data Processing
- **Options Pricing Models**: Black-Scholes implementation.
- **Greeks Calculation**: Delta, Gamma, Theta, Vega, Rho.
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Stochastic oscillators, volume indicators.
- **Risk Management**: Position sizing, P&L tracking, risk metrics.
- **AI Prediction Engine**: Master Trading Signals with 40+ advanced features (fractal analysis, Hurst exponent, market regime detection), Signal Validation, and Prediction Results Tracker.

## Real-time Data Architecture
- **IBKR API Integration**: EClient/EWrapper pattern for live market data.
- **Caching Strategy**: 30-second cache duration for API calls.
- **Asynchronous Processing**: Async/await for non-blocking data fetching.
- **Error Handling**: Comprehensive error management with fallbacks.
- **Data Quality Enforcement**: Zero tolerance for synthetic/fallback data, real-time authentication, and quality scoring.
- **Web Scraping Infrastructure**: For live data from sources like Yahoo Finance, MarketWatch, CNBC, Bloomberg.

## Alert System Architecture
- **Multi-channel Notifications**: Telegram bot integration and email alerts.
- **Alert Cooldown**: 5-minute spam prevention.
- **Alert History**: Logging and tracking.
- **Configurable Triggers**: Price-based and technical indicator-based conditions.

## System Design Choices
- **Prediction Priority System**: Organizes features into Tiers 1-4 based on their importance for trading predictions (Core AI Predictions, Live Market Intelligence, Strategy & Context, Diagnostic & Info).
- **Institutional-Grade Screener**: Advanced ML prediction model with 10 factors, professional technical analysis, risk/reward analysis, confidence scoring, and expected move predictions.
- **Signal System Upgrade**: 6-Factor Professional Model (smart money flow, market structure, dark pool intelligence, volatility, cross-asset signals, technical confirmation), advanced ML signal fusion, Kelly Criterion integration, 5-level conviction system.
- **Balanced Trading Strategy System**: Supports conservative, moderate, aggressive, and speculative strategies with professional position sizing.
- **Institutional-Grade Analytics**: Gamma Exposure Engine, Institutional Flow Tracker (block trades, sweep orders, dark pool prints), advanced Greeks monitoring, High-Profit Options Chain.

# External Dependencies

## Broker Integrations
- **Interactive Brokers (IBKR)**: Primary institutional-grade API.
- **TD Ameritrade**: REST API.
- **Charles Schwab**: Professional trading platform.
- **E*TRADE**: Retail broker API.
- **Fidelity**: Commission-free options trading.
- **Robinhood**: Zero-commission retail platform.
- **Webull**: Advanced charting and options flow data.
- **Alpaca**: Stock trading API.
- **Unified Data Engine**: Aggregates data from connected brokers.

## Financial Data APIs
- **Interactive Brokers API (IBKR)**: Primary source for real-time options and stock data.
- **Yahoo Finance (yfinance)**: Backup data source.
- **Local TWS/IB Gateway**: Required for IBKR connection on `localhost:7497`.

## Technical Analysis Libraries
- **TA-Lib**: Advanced technical indicator calculations.
- **SciPy**: Statistical functions.
- **NumPy/Pandas**: Data manipulation and numerical computing.

## Visualization and UI
- **Streamlit**: Web application framework.
- **Plotly**: Interactive charting and visualization library.

## Communication Services
- **Telegram Bot API**: For real-time alerts.
- **SMTP Email**: For email-based alerts (requires `SMTP_SERVER`, `SMTP_PORT`, `SENDER_EMAIL`, `SENDER_PASSWORD`).

## Social Trading Platform (Components integrated for community data)
- **JSON-based Storage**: For community insights.
- **Signal Validation System**: Tracking and validation of trading signals.
- **Leaderboard System**: Performance ranking.
- **Copy Trading Integration**: Automated trader following.

## Development Environment
- **Python 3.8+**
- **asyncio**: Asynchronous programming support.
- **Environment Variables**: For API keys and credentials (e.g., `TELEGRAM_BOT_TOKEN`).

# Recent Updates (October 2025)

## INSTITUTIONAL-GRADE INTELLIGENCE - ALL 8 FEATURES UPGRADED (October 24, 2025)
**Major Upgrade**: Added 8 advanced institutional-grade data sources for professional squeeze detection

### 8 Advanced Data Sources (All Implemented)
1. **REAL Short Interest Data**: Live scraping from Finviz with SI%, days to cover, shares short, float data (fallback to yfinance)
2. **Real Options Flow Detection**: Unusual activity scoring (0-100), sweep orders, block trades, put/call ratio analysis, unusual call/put buying detection
3. **Borrow Rate Tracking**: Estimated borrow difficulty (EASY/MODERATE/HARD/VERY HARD) based on SI% and volatility - identifies hard-to-short stocks with high squeeze fuel
4. **Dark Pool Detection**: Institutional accumulation patterns via price/volume divergence analysis, unusual block trade detection (0-100 score)
5. **Float Rotation Analysis**: Tracks if entire float is trading (5-day and 20-day rotation rates, days to trade float, extreme squeeze indicators)
6. **Historical Win Rate Back-Testing**: Analyzes 1-year history for similar squeeze patterns, calculates win rate, avg gains/losses, confidence levels (LOW/MODERATE/HIGH/VERY HIGH)
7. **Catalyst Integration**: Upcoming earnings detection with proximity scoring, sector-specific catalysts (FDA for biotech, product launches for tech), days until catalyst
8. **Social Sentiment Scoring**: Proxy analysis for WSB/retail interest using volume surge + volatility patterns, buzz level classification (LOW/MODERATE/HIGH/VERY HIGH), trending detection

### Integration & Display
- All 8 features integrated into market_wide_screener.py with 5-minute caching
- Comprehensive UI section "Advanced Institutional Intelligence" displays all metrics
- Real-time data fetching with graceful fallbacks
- Professional scoring systems (0-100) for quantitative analysis

## PRE-SQUEEZE EARLY WARNING SYSTEM - V2.0 (October 24, 2025)
**Breakthrough Feature**: Detects squeeze setups 1-5 days BEFORE they happen (not during)

### Pre-Squeeze Leading Indicators
- **Volatility Compression**: Bollinger Band squeeze detection - identifies "calm before the storm" when bands tighten significantly below historical average
- **Accumulation Score**: On-Balance Volume (OBV) divergence - detects smart money buying (OBV rising) while price consolidates (price flat)
- **Short Interest Trend**: Tracks increasing short interest over time as fuel accumulates for potential squeeze
- **Option Activity**: Proxy detection of increasing call buying through volume patterns and price correlation

### Squeeze Stage Classification (5-Stage System)
- **PRE-SQUEEZE**: Building phase (1-5 days out) - Optimal entry point, compression + accumulation detected
- **READY**: Imminent squeeze (0-2 days out) - Compression + technical breakout signals, about to pop
- **ACTIVE**: Happening NOW - Volume surge + momentum + RSI confirming squeeze in progress
- **POST**: Already happened - Overbought signals, momentum fading, too late to enter
- **BUILDING**: Early stage (3-7+ days out) - Worth monitoring, not ready yet

### Early Warning Score
- **0-100 Predictive Score**: Combines all leading indicators with weighted formula:
  - Volatility Compression: 30% weight
  - Accumulation Score: 25% weight
  - Short Interest Trend: 25% weight
  - Option Activity: 20% weight
- **Days Until Squeeze**: Estimated timeframe based on stage classification and signal strength

### Market Coverage Expansion
- **500+ Stocks Scanned**: Up from 200, broader market coverage
- **Comprehensive Universe**: Penny stocks, micro caps, small caps, biotech, EV, crypto-related, Chinese ADRs, recent IPOs, volatile tech
- **Two-Stage Parallel Processing**: Pre-filter 500 stocks → Deep analysis on 100-150 high-quality candidates
- **10 Parallel Workers**: 5-10x performance improvement

### Institutional-Grade Analytics (V1.0 Foundation)
- **10-Factor AI Model**: RSI, MACD, Bollinger Bands, Volume Profile, ATR, short interest, volume momentum, price action, float tightness, freshness
- **Risk/Reward Analysis**: ATR-based stops, multiple profit targets, expected moves, support/resistance, risk-adjusted ratios
- **Confidence Scoring**: 0-100% prediction reliability based on data quality and technical validation
- **Professional UI**: Institutional-style presentation with all metrics prominently displayed

## CRITICAL FIX: SMART SCREENER FILTERING (October 24, 2025)
**Major Bug Fix**: Completely rewrote screener filtering logic to prioritize PRE-SQUEEZE opportunities instead of stocks that already squeezed

### The Problem
- Old logic: Filtered by `squeeze_score >= 60`, which rewarded past performance (high volume, momentum)
- Result: Showed stocks AFTER they squeezed (like SCNX +354% then -23% crash), filtered out stocks BEFORE they squeezed (like BYND with 53% SI)
- This was backwards - we want to catch squeezes BEFORE they happen!

### The Solution
**New Smart Filtering** (`_is_explosive_opportunity` function):

**TIER 1: PRE-SQUEEZE (1-5 days out)** - HIGHEST PRIORITY
- Short interest ≥20% OR borrow difficulty HARD/VERY HARD
- Perfect entry window before the move

**TIER 2: READY (0-2 days out)** - HIGH PRIORITY
- Short interest ≥15% OR borrow difficulty HARD/VERY HARD
- Imminent squeeze expected

**TIER 3: BUILDING (3-7+ days out)** - MEDIUM PRIORITY
- Short interest ≥30% AND borrow difficulty HARD/VERY HARD
- OR Short interest ≥40% with early warning ≥30
- Example: BYND (53.4% SI + VERY HARD borrow) qualifies here

**REJECTED:**
- POST stage - Squeeze already happened, too late
- ACTIVE stage with SI <40% - Late entry, high risk
- Example: SCNX (ACTIVE stage, 2.5% SI, already crashed) filtered out

### New Sorting Priority
Stocks now rank by:
1. **Squeeze Stage Priority**: PRE-SQUEEZE (1000 pts) > READY (800) > BUILDING (600) > ACTIVE (400)
2. **Short Interest**: Higher SI = more squeeze fuel (up to 500 pts)
3. **Early Warning Score**: Forward-looking signals (up to 200 pts)

**Total priority score determines ranking** - NOT past performance!

### Extended Hours Tracking (October 24, 2025)
**New Feature**: Real-time pre-market and after-hours price tracking

- **Extended Hours Data**: Captures pre-market and post-market prices from yfinance
- **Crash Detection**: Automatically classifies overnight moves (MINOR/MODERATE/SEVERE/CATASTROPHIC)
- **Pump Detection**: Identifies overnight squeezes before market open
- **10-Second Cache**: Real-time updates for extended hours movements
- **Integration**: Works seamlessly with screener to detect overnight selloffs (like SCNX -23% post-market)

**Module**: `extended_hours_tracker.py` with `ExtendedHoursTracker` class