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