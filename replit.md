# Overview

This project is an institutional-grade options trading platform built with Streamlit. Its purpose is to provide professional traders with real-time market data analysis, advanced options pricing, technical indicators, and alert management, integrated with the Interactive Brokers (IBKR) API. The platform focuses on delivering high-priority AI predictions and live market intelligence to facilitate informed trading decisions, offering a powerful analytical toolkit within a clean and intuitive interface.

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
- **Modular Component Design**: Core functionalities are separated into modules for options pricing (`options_engine.py`), market data (`market_data.py`), technical indicators (`technical_indicators.py`), alerts (`alerts.py`), and utility functions (`utils.py`).

## Data Processing
- **Options Pricing Models**: Black-Scholes implementation for options pricing and Greeks calculation (Delta, Gamma, Theta, Vega, Rho).
- **Technical Analysis**: Utilizes TA-Lib for indicators like RSI, MACD, Bollinger Bands, Stochastic oscillators, and volume indicators.
- **Risk Management**: Includes position sizing, P&L tracking, and risk metrics.
- **AI Prediction Engine**: Features Master Trading Signals with over 40 advanced features, Signal Validation, and a Prediction Results Tracker.

## Real-time Data Architecture
- **IBKR API Integration**: Primary institutional-grade data source using EClient/EWrapper for live market data with 3-second timeout and automatic Yahoo Finance fallback.
- **Professional Refresh Rates**: Institutional-grade update intervals - Prices: 3s (real-time), Options Flow: 5s (professional), Technical Indicators: 10s, Gamma Exposure: 30s, News: 60s.
- **Intelligent Caching Strategy**: Data-type specific cache durations (3s for prices, 5s for flow, 10s for technical) with Last-Known-Good (LKG) fallback system.
- **Asynchronous Processing**: Employs async/await for non-blocking data fetching with differential refresh coordination.
- **Data Source Priority**: IBKR TWS (98% quality) → Yahoo Finance (90% quality) → Last-Known-Good Cache (70-85% quality) → Statistical Model (50-75% quality).
- **Data Quality Enforcement**: Strict error handling, multi-tier fallbacks, real-time authentication, and quality scoring to prevent synthetic/fallback data.
- **Web Scraping Infrastructure**: Gathers live data from sources like Yahoo Finance, MarketWatch, CNBC, and Bloomberg.

## Alert System Architecture
- **Multi-channel Notifications**: Supports Telegram bot integration and email alerts.
- **Alert Cooldown**: A 5-minute spam prevention mechanism.
- **Alert History**: Logs and tracks all alerts.
- **Configurable Triggers**: Alerts can be set based on price and technical indicator conditions.

## System Design Choices
- **Prediction Priority System**: Features are categorized into Tiers 1-4 based on their importance for trading predictions (Core AI Predictions, Live Market Intelligence, Strategy & Context, Diagnostic & Info).
- **Institutional-Grade Screener**: Incorporates an advanced ML prediction model with 10 factors, professional technical analysis, risk/reward analysis, confidence scoring, and expected move predictions. Includes a pre-squeeze early warning system with 5-stage classification and an early warning score.
- **Signal System Upgrade**: Features a 6-Factor Professional Model (smart money flow, market structure, dark pool intelligence, volatility, cross-asset signals, technical confirmation), advanced ML signal fusion, Kelly Criterion integration, and a 5-level conviction system.
- **Balanced Trading Strategy System**: Supports conservative, moderate, aggressive, and speculative strategies with professional position sizing.
- **Institutional-Grade Analytics**: Includes a Gamma Exposure Engine, Institutional Flow Tracker (block trades, sweep orders, dark pool prints), advanced Greeks monitoring, and High-Profit Options Chain.
- **Earnings Playbook Enhancement**: Offers comprehensive features like Win Rate Analytics, Expected Return Calculator, Risk/Reward Ratio, HOT PLAYS Dashboard, Position Size Recommendations, and an Alert System.
- **Institutional-Grade Intelligence**: Integrates 8 advanced data sources for professional squeeze detection, including real short interest data, options flow, borrow rate tracking, dark pool detection, float rotation analysis, historical win rate back-testing, catalyst integration, and social sentiment scoring.
- **Smart Screener Filtering**: Prioritizes PRE-SQUEEZE opportunities based on short interest, borrow difficulty, and early warning scores, with new sorting priority by squeeze stage.
- **Extended Hours Tracking**: Provides real-time pre-market and after-hours price tracking, including overnight move detection (crash/pump).

# External Dependencies

## Broker Integrations
- **Interactive Brokers (IBKR)**: Primary institutional-grade API.

## Financial Data APIs
- **Interactive Brokers API (IBKR)**: Primary source for real-time options and stock data.
- **Yahoo Finance (yfinance)**: Backup data source.
- **Local TWS/IB Gateway**: Required for IBKR connection.

## Technical Analysis Libraries
- **TA-Lib**: Advanced technical indicator calculations.
- **SciPy**: Statistical functions.
- **NumPy/Pandas**: Data manipulation and numerical computing.

## Visualization and UI
- **Streamlit**: Web application framework.
- **Plotly**: Interactive charting and visualization library.

## Communication Services
- **Telegram Bot API**: For real-time alerts.
- **SMTP Email**: For email-based alerts.

## Social Trading Platform (Components integrated for community data)
- **JSON-based Storage**: For community insights.
- **Signal Validation System**: Tracking and validation of trading signals.
- **Leaderboard System**: Performance ranking.
- **Copy Trading Integration**: Automated trader following.

## Development Environment
- **Python 3.8+**
- **asyncio**: Asynchronous programming support.
- **Environment Variables**: For API keys and credentials.