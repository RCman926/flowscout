# Overview

This is a comprehensive options trading platform built with Streamlit that provides real-time market data analysis, options pricing, technical indicators, and alert management. The platform integrates with Interactive Brokers (IBKR) API for live trading data and implements advanced options analytics including Greeks calculation, volatility analysis, and risk management tools. The system is designed for professional traders who need sophisticated analysis capabilities with a clean, intuitive interface.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Streamlit Web Application**: Single-page application with sidebar controls and main dashboard
- **Real-time Updates**: Session state management for persistent data across user interactions
- **Interactive Visualizations**: Plotly integration for dynamic charts and graphs
- **Responsive Layout**: Wide layout configuration with expandable sidebar for trading controls

## Backend Architecture
- **Modular Component Design**: Separation of concerns across multiple specialized modules
  - `options_engine.py`: Options pricing, Greeks calculation, and volatility analysis
  - `market_data.py`: Real-time and historical market data fetching
  - `technical_indicators.py`: Technical analysis calculations using TA-Lib
  - `alerts.py`: Multi-channel notification system
  - `utils.py`: Shared utility functions for formatting and calculations

## Data Processing
- **Options Pricing Models**: Black-Scholes implementation for theoretical pricing
- **Greeks Calculation**: Delta, Gamma, Theta, Vega, and Rho calculations
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Stochastic oscillators, and volume indicators
- **Risk Management**: Position sizing, P&L tracking, and risk metrics

## Real-time Data Architecture
- **IBKR API Integration**: EClient/EWrapper pattern for live market data
- **Caching Strategy**: 30-second cache duration for API calls to reduce latency
- **Asynchronous Processing**: Async/await pattern for non-blocking data fetching
- **Error Handling**: Comprehensive error management with fallback mechanisms

## Alert System Architecture
- **Multi-channel Notifications**: Telegram bot integration and email alerts
- **Alert Cooldown**: Spam prevention with 5-minute cooldown periods
- **Alert History**: Logging and tracking of all sent notifications
- **Configurable Triggers**: Price-based and technical indicator-based alert conditions

# External Dependencies

## Financial Data APIs
- **Interactive Brokers API (IBKR)**: Primary source for real-time options and stock data
- **Yahoo Finance (yfinance)**: Backup data source for historical price information
- **Connection Requirements**: Local TWS/IB Gateway running on localhost:7497

## Technical Analysis Libraries
- **TA-Lib**: Advanced technical indicator calculations
- **SciPy**: Statistical functions for options pricing and analysis
- **NumPy/Pandas**: Core data manipulation and numerical computing

## Visualization and UI
- **Streamlit**: Web application framework with auto-refresh capabilities
- **Plotly**: Interactive charting and visualization library

## Communication Services
- **Telegram Bot API**: Real-time alert delivery via Telegram
- **SMTP Email**: Email-based alert system with Gmail integration
- **Required Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: Bot authentication token
  - `SMTP_SERVER`, `SMTP_PORT`: Email server configuration
  - `SENDER_EMAIL`, `SENDER_PASSWORD`: Email credentials

## Social Trading Platform
- **Community Data Management**: JSON-based storage for community insights and social trading data
- **Signal Validation System**: Real-time tracking and validation of trading signals
- **Leaderboard System**: Performance ranking and trader verification
- **Copy Trading Integration**: Automated trader following and performance tracking

## Machine Learning (Planned)
- **TensorFlow/Keras**: Neural network models for price prediction
- **Scikit-learn**: Random Forest and preprocessing utilities
- **TextBlob**: Sentiment analysis for market news integration

## Development and Deployment
- **Python 3.8+**: Core runtime environment
- **asyncio**: Asynchronous programming support
- **Environment Variables**: Configuration management for API keys and credentials

# Recent Updates (August 2025)

## Institutional-Grade Analytics Implementation
- **Gamma Exposure Engine**: Live GEX levels showing dealer positioning and gamma flip points for support/resistance identification
- **Institutional Flow Tracker**: Real-time detection of block trades (>100 contracts), sweep orders, and dark pool prints with sentiment analysis
- **Advanced Greeks Monitoring**: Portfolio-level Delta, Gamma, Theta, Vega analysis with risk assessment and time decay tracking
- **High-Profit Options Chain**: Comprehensive strike ladder with 0DTE, weekly, and monthly expirations showing 200%-2000% profit potential
- **Enhanced Position Sizing**: Account-based risk management with Conservative (300% gains), Aggressive (800% gains), and 0DTE YOLO (2000% gains) strategies
- **Professional Trading Decision Center**: Aggressive profit targets with 1:15 to 1:50 risk/reward ratios and exact entry/exit levels
- **MSN Money Integration**: Real-time market-moving news with direct options impact analysis
- **Financial Calendar Enhancement**: Real earnings dates with countdown timers and economic events affecting options volatility

## Architecture Enhancements
- **Real-Time Data Infrastructure**: Advanced caching and error handling for institutional-grade data feeds
- **Modular Analytics Engines**: Separated gamma exposure, flow tracking, and Greeks calculation into specialized modules
- **Beautiful UI Implementation**: Clean, professional interface with color-coded alerts and institutional-grade visualizations